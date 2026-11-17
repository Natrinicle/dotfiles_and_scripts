#!/usr/bin/env python3
"""Start an agent-only display, optionally capture it, always tear it down.

Labs live under /tmp/ephemeral-display/<id>/. Stop kills only processes whose
cmdline contains that lab path or the recorded pgid, and never host
plasmashell / kwin_wayland.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STATE_ROOT = Path(os.environ.get("EPHEMERAL_DISPLAY_DIR", "/tmp/ephemeral-display"))
SHOT_DIR = Path(os.environ.get("SCREENSHOT_WINDOW_DIR", "/tmp/agent-screenshots"))
WEBTOP_IMAGE = os.environ.get(
    "EPHEMERAL_DISPLAY_WEBTOP_IMAGE", "lscr.io/linuxserver/webtop:ubuntu-kde"
)
KINDS = (
    "plasmawindowed",
    "qml",
    "nested-kwin",
    "chrome",
    "chrome-shot",
    "webtop",
    "app",
)
PROTECTED_COMM = {"plasmashell", "kwin_wayland"}
FORBIDDEN_FLAGS = ("--replace", "--drm", "--fullscreen")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _which(names: list[str]) -> Path | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def _run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, text=True, **kwargs)


def _proc_cmd(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\x00", b" ").decode("utf-8", "replace").strip()


def _proc_comm(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/comm").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _proc_uid(pid: int) -> int | None:
    try:
        for line in (
            Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines()
        ):
            if line.startswith("Uid:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


def _proc_cwd(pid: int) -> str:
    try:
        return os.readlink(f"/proc/{pid}/cwd")
    except OSError:
        return ""


def _proc_ppid(pid: int) -> int:
    try:
        for line in (
            Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines()
        ):
            if line.startswith("PPid:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return 0
    return 0


def live_protected_pids() -> set[int]:
    """Host compositor/shell only. Nested kwin/plasmashell in a lab is not protected."""
    protected: set[int] = set()
    uid = os.getuid()
    display = os.environ.get("WAYLAND_DISPLAY", "wayland-0")
    state_root = str(STATE_ROOT)
    proc_root = Path("/proc")
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if _proc_uid(pid) != uid:
            continue
        comm = _proc_comm(pid)
        if comm not in PROTECTED_COMM:
            continue
        cmd = _proc_cmd(pid)
        cwd = _proc_cwd(pid)
        if state_root in cmd or state_root in cwd:
            continue
        if "ephemeral-display" in cmd or "--socket=ed-" in cmd or "--virtual" in cmd:
            continue
        if comm == "kwin_wayland":
            if (
                "--wayland-fd" in cmd
                or f"--socket {display}" in cmd
                or f"--socket={display}" in cmd
            ):
                protected.add(pid)
            continue
        parent_cmd = _proc_cmd(_proc_ppid(pid))
        if (
            state_root in parent_cmd
            or "--socket=ed-" in parent_cmd
            or "ephemeral-display" in parent_cmd
        ):
            continue
        protected.add(pid)
    return protected


def _refuse_host_takeover(parts: list[str]) -> None:
    """Nested labs must not take over the host compositor or shell."""
    for part in parts:
        base = part.split("=", 1)[0]
        if base in FORBIDDEN_FLAGS or part in FORBIDDEN_FLAGS:
            raise SystemExit(f"refusing {part} (would take over the host session)")
    joined = " ".join(parts)
    if "kquitapp" in joined and "plasmashell" in joined:
        raise SystemExit("refusing kquitapp plasmashell (would kill the host session)")


def _start_session_bus(lab: Path) -> tuple[int, str]:
    """Private session bus so nested plasmashell cannot claim the host name."""
    daemon = _which(["dbus-daemon"])
    if daemon is None:
        raise SystemExit("dbus-daemon not on PATH")
    sock = lab / "bus"
    address = f"unix:path={sock}"
    log = (lab / "dbus.log").open("ab")
    proc = subprocess.Popen(
        [
            str(daemon),
            "--session",
            "--nofork",
            "--nopidfile",
            f"--address={address}",
        ],
        start_new_session=True,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    deadline = time.time() + 5
    while time.time() < deadline:
        if sock.exists():
            return proc.pid, address
        if proc.poll() is not None:
            raise SystemExit("dbus-daemon exited before the socket was ready")
        time.sleep(0.05)
    proc.kill()
    raise SystemExit("dbus-daemon socket not ready")


def _new_id() -> str:
    return f"{_now()}-{secrets.token_hex(3)}"


def _lab_dir(lab_id: str) -> Path:
    return STATE_ROOT / lab_id


def _state_path(lab_id: str) -> Path:
    return _lab_dir(lab_id) / "state.json"


def load_state(lab_id: str) -> dict[str, Any]:
    path = _state_path(lab_id)
    if not path.is_file():
        raise SystemExit(f"no lab: {lab_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"bad state: {path}")
    return data


def save_state(state: dict[str, Any]) -> None:
    path = _state_path(str(state["id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def list_labs() -> list[dict[str, Any]]:
    if not STATE_ROOT.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for child in sorted(STATE_ROOT.iterdir()):
        st = child / "state.json"
        if st.is_file():
            try:
                data = json.loads(st.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                rows.append(data)
    return rows


def chromium_bin() -> Path:
    found = _which(
        ["chromium", "google-chrome-stable", "google-chrome", "chromium-browser"]
    )
    if found is None:
        raise SystemExit("chromium not on PATH")
    return found


def screenshot_window_bin() -> Path | None:
    found = _which(["screenshot-window"])
    return Path(found) if found else None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    except OSError:
        return False
    for line in status.splitlines():
        if line.startswith("State:"):
            # Zombies still accept kill(pid, 0); they are not a running lab.
            return not line.split()[1].startswith("Z")
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _kill_pid(pid: int, protected: set[int]) -> None:
    if pid <= 0 or pid in protected or not _pid_alive(pid):
        return
    if pid in {os.getpid(), os.getpgid(0)}:
        return
    if pid in live_protected_pids():
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return


def _kill_pgid(pgid: int, protected: set[int], sig: int = signal.SIGTERM) -> None:
    if pgid <= 0 or pgid in protected:
        return
    if pgid in {os.getpid(), os.getpgid(0)}:
        return
    try:
        os.killpg(pgid, sig)
    except OSError:
        try:
            os.kill(pgid, sig)
        except OSError:
            return


def _wait_dead(pids: list[int], timeout: float) -> None:
    deadline = time.time() + timeout
    pending = {pid for pid in pids if pid > 0}
    while pending and time.time() < deadline:
        pending = {pid for pid in pending if _pid_alive(pid)}
        if pending:
            time.sleep(0.05)


def _lab_pids(lab_id: str) -> list[int]:
    needles = (
        f"/tmp/ephemeral-display/{lab_id}",
        f"ephemeral-display-{lab_id}",
        f"--socket=ed-{lab_id}",
        f"ed-{lab_id}",
    )
    hits: list[int] = []
    uid = os.getuid()
    protected = live_protected_pids()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid in protected or _proc_uid(pid) != uid:
            continue
        cmd = _proc_cmd(pid)
        cwd = _proc_cwd(pid)
        if any(n in cmd or n in cwd for n in needles):
            hits.append(pid)
    return hits


def stop_lab(lab_id: str, *, forget: bool = True) -> dict[str, Any]:
    protected = live_protected_pids()
    state: dict[str, Any] = {}
    path = _state_path(lab_id)
    if path.is_file():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {"id": lab_id}
    container = state.get("container")
    if container:
        _run(["docker", "rm", "-f", str(container)], capture_output=True)
    pgids: list[int] = []
    for raw in list(state.get("pgids") or []):
        pgids.append(int(raw))
    pgid = int(state.get("pgid") or 0)
    if pgid:
        pgids.append(pgid)
    recorded = [int(pid) for pid in list(state.get("pids") or []) if int(pid) > 0]
    me = {os.getpid(), os.getpgid(0)}
    for group in dict.fromkeys(pgids):
        if group and group not in protected and group not in me:
            _kill_pgid(int(group), protected)
    for pid in recorded:
        _kill_pid(int(pid), protected)
    _wait_dead(recorded, timeout=2.0)
    leftovers = set(_lab_pids(lab_id)) | {pid for pid in recorded if _pid_alive(pid)}
    for pid in leftovers:
        if pid in me or pid in live_protected_pids():
            continue
        _kill_pid(pid, protected)
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            if pid not in me:
                os.killpg(pid, signal.SIGKILL)
        except OSError:
            pass
    _wait_dead(list(leftovers | set(recorded)), timeout=1.0)
    still = set(_lab_pids(lab_id)) | {pid for pid in recorded if _pid_alive(pid)}
    for pid in still:
        if pid in live_protected_pids() or pid in me:
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    chrome_dir = _lab_dir(lab_id) / "chrome"
    if chrome_dir.is_dir():
        shutil.rmtree(chrome_dir, ignore_errors=True)
    if forget:
        shutil.rmtree(_lab_dir(lab_id), ignore_errors=True)
    return {"id": lab_id, "stopped": True, "protected_untouched": sorted(protected)}


def gc(*, stale_min: float | None, all_labs: bool) -> list[str]:
    stopped: list[str] = []
    now = time.time()
    for state in list_labs():
        lab_id = str(state.get("id") or "")
        if not lab_id:
            continue
        created = state.get("created_unix")
        age_ok = False
        if stale_min is not None and isinstance(created, (int, float)):
            age_ok = (now - float(created)) >= stale_min * 60
        alive = False
        for pid in list(state.get("pids") or []):
            if _pid_alive(int(pid)):
                alive = True
                break
        if state.get("container"):
            inspect = _run(
                [
                    "docker",
                    "inspect",
                    "-f",
                    "{{.State.Running}}",
                    str(state["container"]),
                ],
                capture_output=True,
            )
            if inspect.returncode == 0 and inspect.stdout.strip() == "true":
                alive = True
        if all_labs or age_ok or not alive:
            stop_lab(lab_id)
            stopped.append(lab_id)
    if STATE_ROOT.is_dir():
        for child in STATE_ROOT.iterdir():
            if child.is_dir() and not (child / "state.json").is_file():
                shutil.rmtree(child, ignore_errors=True)
    return stopped


def _popen(
    cmd: list[str], lab: Path, extra_env: dict[str, str] | None = None
) -> subprocess.Popen[str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    log = (lab / "lab.log").open("ab")
    return subprocess.Popen(
        cmd,
        cwd=str(lab),
        env=env,
        start_new_session=True,
        stdout=log,
        stderr=subprocess.STDOUT,
    )


def _wait_http(url: str, timeout: float) -> None:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                if 200 <= resp.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = str(exc)
        time.sleep(0.2)
    raise SystemExit(f"timeout waiting for {url}: {last}")


def _http_json(url: str) -> Any:
    with urllib.request.urlopen(url, timeout=3) as resp:
        return json.loads(resp.read().decode("utf-8"))


class _Cdp:
    """Minimal CDP client (RFC 6455 text frames, client masked)."""

    def __init__(self, ws_url: str) -> None:
        parsed = urllib.parse.urlparse(ws_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        self._sock = socket.create_connection((host, port), timeout=10)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        self._sock.sendall(req.encode("ascii"))
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise RuntimeError("CDP websocket handshake closed")
            buf += chunk
        header, rest = buf.split(b"\r\n\r\n", 1)
        status = header.split(b"\r\n", 1)[0]
        if b"101" not in status:
            raise RuntimeError(f"CDP handshake failed: {status!r}")
        expect = base64.b64encode(
            hashlib.sha1(
                (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()
            ).digest()
        )
        if expect not in header:
            raise RuntimeError("CDP websocket accept mismatch")
        self._buf = rest
        self._next_id = 1

    def close(self) -> None:
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._sock.close()

    def _send_frame(self, payload: bytes) -> None:
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        header = bytearray()
        header.append(0x81)
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header.extend(n.to_bytes(2, "big"))
        else:
            header.append(0x80 | 127)
            header.extend(n.to_bytes(8, "big"))
        header.extend(mask)
        self._sock.sendall(header + masked)

    def _recv_frame(self) -> bytes:
        def need(n: int) -> bytes:
            while len(self._buf) < n:
                chunk = self._sock.recv(4096)
                if not chunk:
                    raise RuntimeError("CDP socket closed")
                self._buf += chunk
            data, self._buf = self._buf[:n], self._buf[n:]
            return data

        b0, b1 = need(2)
        opcode = b0 & 0x0F
        masked = b1 & 0x80
        length = b1 & 0x7F
        if length == 126:
            length = int.from_bytes(need(2), "big")
        elif length == 127:
            length = int.from_bytes(need(8), "big")
        mask = need(4) if masked else b""
        payload = need(length)
        if masked:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        if opcode == 0x8:
            raise RuntimeError("CDP websocket close")
        if opcode == 0x1:
            return payload
        if opcode == 0x2:
            return payload
        return payload

    def call(
        self, method: str, params: dict[str, Any] | None = None, timeout: float = 20
    ) -> Any:
        msg_id = self._next_id
        self._next_id += 1
        self._send_frame(
            json.dumps(
                {"id": msg_id, "method": method, "params": params or {}}
            ).encode()
        )
        deadline = time.time() + timeout
        self._sock.settimeout(max(1.0, timeout))
        while time.time() < deadline:
            raw = self._recv_frame()
            data = json.loads(raw.decode("utf-8"))
            if data.get("id") == msg_id:
                if "error" in data:
                    raise RuntimeError(f"CDP {method}: {data['error']}")
                return data.get("result")
        raise TimeoutError(f"CDP {method} timed out")


def _chrome_user_data(lab: Path) -> Path:
    path = lab / "chrome"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _chrome_base_args(user_data: Path) -> list[str]:
    return [
        str(chromium_bin()),
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-sync",
        "--password-store=basic",
        "--disable-dev-shm-usage",
        "--hide-scrollbars",
        f"--user-data-dir={user_data}",
        "--window-size=1280,720",
    ]


def start_chrome_shot(url: str, output: Path, lab: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    user_data = _chrome_user_data(lab)
    cmd = [
        *_chrome_base_args(user_data),
        "--virtual-time-budget=8000",
        "--timeout=20000",
        "--ignore-certificate-errors",
        f"--screenshot={output}",
        url,
    ]
    try:
        proc = _run(cmd, capture_output=True, timeout=40)
    except subprocess.TimeoutExpired as exc:
        raise SystemExit("chromium screenshot timed out") from exc
    if proc.returncode != 0 and not output.is_file():
        sys.stderr.write(proc.stderr or proc.stdout or "")
        raise SystemExit(f"chromium screenshot failed ({proc.returncode})")
    if not output.is_file():
        raise SystemExit(f"chromium wrote no PNG: {output}")
    return output


def start_chrome(url: str, lab: Path, lab_id: str) -> dict[str, Any]:
    port = _free_port()
    user_data = _chrome_user_data(lab)
    cmd = [
        *_chrome_base_args(user_data),
        "--remote-debugging-address=127.0.0.1",
        f"--remote-debugging-port={port}",
        "--ignore-certificate-errors",
        url,
    ]
    proc = _popen(cmd, lab)
    state = {
        "id": lab_id,
        "kind": "chrome",
        "pgid": proc.pid,
        "pids": [proc.pid],
        "port": port,
        "url": url,
        "title": "headless chromium",
        "created": _now(),
        "created_unix": time.time(),
        "cmd": cmd,
    }
    save_state(state)
    try:
        _wait_http(f"http://127.0.0.1:{port}/json/version", timeout=20)
    except SystemExit:
        stop_lab(lab_id)
        raise
    return state


def capture_chrome(state: dict[str, Any], output: Path) -> Path:
    port = int(state["port"])
    pages = _http_json(f"http://127.0.0.1:{port}/json/list")
    ws = None
    if isinstance(pages, list):
        for page in pages:
            if page.get("type") == "page" and page.get("webSocketDebuggerUrl"):
                ws = page["webSocketDebuggerUrl"]
                break
    if not ws:
        version = _http_json(f"http://127.0.0.1:{port}/json/version")
        ws = version.get("webSocketDebuggerUrl")
    if not ws:
        raise SystemExit("no CDP websocket for chromium lab")
    client = _Cdp(str(ws))
    try:
        try:
            client.call("Page.enable")
        except RuntimeError:
            pass
        result = client.call("Page.captureScreenshot", {"format": "png"})
    finally:
        client.close()
    png = base64.b64decode(result["data"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(png)
    return output


def start_plasmawindowed(
    applet: str, lab: Path, lab_id: str, extra: list[str]
) -> dict[str, Any]:
    binary = _which(["plasmawindowed"])
    if binary is None:
        raise SystemExit("plasmawindowed not on PATH")
    cmd = [str(binary), applet, *extra]
    proc = _popen(cmd, lab)
    state = {
        "id": lab_id,
        "kind": "plasmawindowed",
        "pgid": proc.pid,
        "pids": [proc.pid],
        "applet": applet,
        "title": applet.rsplit(".", 1)[-1],
        "created": _now(),
        "created_unix": time.time(),
        "cmd": cmd,
        "capture_all": True,
    }
    save_state(state)
    return state


def start_qml(
    qml_file: Path, lab: Path, lab_id: str, extra: list[str]
) -> dict[str, Any]:
    binary = _which(["qml", "qml6"])
    if binary is None:
        raise SystemExit("qml not on PATH")
    if not qml_file.is_file():
        raise SystemExit(f"missing QML: {qml_file}")
    cmd = [str(binary), str(qml_file), *extra]
    proc = _popen(cmd, lab)
    state = {
        "id": lab_id,
        "kind": "qml",
        "pgid": proc.pid,
        "pids": [proc.pid],
        "file": str(qml_file),
        "title": qml_file.stem,
        "created": _now(),
        "created_unix": time.time(),
        "cmd": cmd,
    }
    save_state(state)
    return state


def start_nested_kwin(
    lab: Path,
    lab_id: str,
    width: int,
    height: int,
    inner: list[str],
    *,
    virtual: bool,
) -> dict[str, Any]:
    binary = _which(["kwin_wayland"])
    if binary is None:
        raise SystemExit("kwin_wayland not on PATH")
    _refuse_host_takeover(inner)
    parent_display = os.environ.get("WAYLAND_DISPLAY", "")
    socket_name = f"ed-{lab_id}"
    dbus_pid, bus_address = _start_session_bus(lab)
    cmd = [
        str(binary),
        f"--socket={socket_name}",
        "--xwayland",
        "--no-global-shortcuts",
        "--no-lockscreen",
        "--no-kactivities",
        f"--width={width}",
        f"--height={height}",
    ]
    if virtual:
        cmd.append("--virtual")
    elif parent_display:
        cmd.append(f"--wayland-display={parent_display}")
    if inner:
        cmd.extend(inner)
    _refuse_host_takeover(cmd)
    try:
        proc = _popen(cmd, lab, extra_env={"DBUS_SESSION_BUS_ADDRESS": bus_address})
    except BaseException:
        _kill_pid(dbus_pid, set())
        try:
            os.killpg(dbus_pid, signal.SIGTERM)
        except OSError:
            pass
        raise
    state = {
        "id": lab_id,
        "kind": "nested-kwin",
        "pgid": proc.pid,
        "pgids": [proc.pid, dbus_pid],
        "pids": [proc.pid, dbus_pid],
        "socket": socket_name,
        "dbus": bus_address,
        "title": "kwin_wayland",
        "created": _now(),
        "created_unix": time.time(),
        "cmd": cmd,
        "width": width,
        "height": height,
        "virtual": virtual,
    }
    save_state(state)
    return state


def start_app(
    argv: list[str], lab: Path, lab_id: str, title: str | None
) -> dict[str, Any]:
    if not argv:
        raise SystemExit("app needs --exec")
    _refuse_host_takeover(argv)
    binary = Path(argv[0])
    if not binary.is_file():
        found = _which([argv[0]])
        if found is None:
            raise SystemExit(f"not on PATH: {argv[0]}")
        argv = [str(found), *argv[1:]]
    proc = _popen(argv, lab)
    state = {
        "id": lab_id,
        "kind": "app",
        "pgid": proc.pid,
        "pids": [proc.pid],
        "title": title or Path(argv[0]).name,
        "created": _now(),
        "created_unix": time.time(),
        "cmd": argv,
        "capture_all": True,
    }
    save_state(state)
    return state


def _docker_image_present(image: str) -> bool:
    insp = _run(["docker", "image", "inspect", image], capture_output=True)
    return insp.returncode == 0


def start_webtop(
    lab: Path,
    lab_id: str,
    *,
    pull: bool,
    share: Path | None,
    image: str,
) -> dict[str, Any]:
    if _which(["docker"]) is None:
        raise SystemExit("docker not on PATH")
    if not _docker_image_present(image):
        if not pull:
            raise SystemExit(
                f"missing image {image}. Pass --pull after the user names a pull."
            )
        pulled = _run(["docker", "pull", image], capture_output=True)
        if pulled.returncode != 0:
            sys.stderr.write(pulled.stderr)
            raise SystemExit("docker pull failed")
    name = f"ephemeral-display-{lab_id}"
    cmd = [
        "docker",
        "run",
        "-d",
        "--rm",
        "--name",
        name,
        "--shm-size=1gb",
        "-p",
        "127.0.0.1::3001",
        "-e",
        f"PUID={os.getuid()}",
        "-e",
        f"PGID={os.getgid()}",
    ]
    dri = Path("/dev/dri")
    if dri.is_dir():
        cmd.extend(["--device", "/dev/dri"])
    if share is not None:
        cmd.extend(["-v", f"{share.resolve()}:/config/lab:ro"])
    cmd.append(image)
    proc = _run(cmd, capture_output=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit("docker run failed")
    cid = proc.stdout.strip()
    port_out = _run(["docker", "port", name, "3001/tcp"], capture_output=True)
    host_port = ""
    if port_out.returncode == 0:
        # 127.0.0.1:NNNN
        line = port_out.stdout.strip().splitlines()[0]
        host_port = line.rsplit(":", 1)[-1].strip()
    url = f"https://127.0.0.1:{host_port}/" if host_port else ""
    state = {
        "id": lab_id,
        "kind": "webtop",
        "pgid": 0,
        "pids": [],
        "container": name,
        "cid": cid,
        "port": host_port,
        "url": url,
        "title": "webtop",
        "created": _now(),
        "created_unix": time.time(),
        "cmd": cmd,
        "image": image,
    }
    save_state(state)
    if url:
        try:
            _wait_http(url.replace("https://", "http://"), timeout=5)
        except SystemExit:
            pass
    return state


def wait_window(title: str, timeout: float, *, include_all: bool) -> dict[str, Any]:
    helper = screenshot_window_bin()
    if helper is None:
        raise SystemExit("screenshot-window not on PATH")
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        cmd = [str(helper), "list", "--json"]
        if include_all:
            cmd.append("--all")
        listed = _run(cmd, capture_output=True)
        if listed.returncode != 0:
            last = listed.stderr.strip()
            time.sleep(0.3)
            continue
        try:
            rows = json.loads(listed.stdout)
        except json.JSONDecodeError:
            last = "invalid list json"
            time.sleep(0.3)
            continue
        needle = title.casefold()
        hits = [
            r
            for r in rows
            if needle in str(r.get("caption") or "").casefold()
            or needle in str(r.get("resourceClass") or "").casefold()
        ]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            last = f"ambiguous title {title!r}: {len(hits)} windows"
        else:
            last = f"no window matching {title!r}"
        time.sleep(0.3)
    raise SystemExit(f"window wait failed: {last}")


def capture_window(
    state: dict[str, Any], output: Path | None, title: str | None
) -> Path:
    helper = screenshot_window_bin()
    if helper is None:
        raise SystemExit("screenshot-window not on PATH")
    needle = title or str(state.get("title") or "")
    if not needle:
        raise SystemExit("capture needs --title")
    include_all = bool(
        state.get("capture_all") or state.get("kind") == "plasmawindowed"
    )
    row = wait_window(needle, timeout=20, include_all=include_all)
    uuid = str(row.get("uuid") or "")
    cmd = [str(helper), "capture", "--uuid", uuid]
    if output is not None:
        cmd.extend(["--output", str(output)])
    shot = _run(cmd, capture_output=True)
    if shot.returncode != 0:
        sys.stderr.write(shot.stderr)
        raise SystemExit(f"screenshot-window failed ({shot.returncode})")
    path = Path(shot.stdout.strip())
    if not path.is_file():
        raise SystemExit("screenshot-window printed no file")
    return path


def default_png(lab_id: str, kind: str) -> Path:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    return SHOT_DIR / f"ephemeral-{kind}-{lab_id}.png"


def _exec_argv(args: argparse.Namespace) -> list[str]:
    extra = list(args.extra or [])
    if args.exec:
        return shlex.split(str(args.exec)) + extra
    return extra


def start_kind(args: argparse.Namespace) -> dict[str, Any]:
    if not getattr(args, "no_gc", False):
        gc(stale_min=args.stale_min, all_labs=False)
    lab_id = _new_id()
    lab = _lab_dir(lab_id)
    lab.mkdir(parents=True, exist_ok=True)
    extra = list(args.extra or [])
    kind = args.kind
    state: dict[str, Any] | None = None
    try:
        if kind == "plasmawindowed":
            if not args.applet:
                raise SystemExit("plasmawindowed needs --applet")
            state = start_plasmawindowed(args.applet, lab, lab_id, extra)
            if args.title:
                state["title"] = args.title
                save_state(state)
            return state
        if kind == "qml":
            if not args.file:
                raise SystemExit("qml needs --file")
            state = start_qml(Path(args.file).expanduser(), lab, lab_id, extra)
            if args.title:
                state["title"] = args.title
                save_state(state)
            return state
        if kind == "nested-kwin":
            inner = _exec_argv(args)
            state = start_nested_kwin(
                lab,
                lab_id,
                args.width,
                args.height,
                inner,
                virtual=bool(args.virtual),
            )
            if args.title:
                state["title"] = args.title
                save_state(state)
            return state
        if kind == "app":
            argv = _exec_argv(args)
            state = start_app(argv, lab, lab_id, args.title)
            return state
        if kind == "chrome":
            if not args.url:
                raise SystemExit("chrome needs --url")
            return start_chrome(args.url, lab, lab_id)
        if kind == "chrome-shot":
            if not args.url:
                raise SystemExit("chrome-shot needs --url")
            dest = (
                Path(args.output).expanduser()
                if args.output
                else default_png(lab_id, "chrome-shot")
            )
            png = start_chrome_shot(args.url, dest, lab)
            shutil.rmtree(lab, ignore_errors=True)
            return {
                "id": lab_id,
                "kind": "chrome-shot",
                "stopped": True,
                "png": str(png),
                "url": args.url,
            }
        if kind == "webtop":
            share = Path(args.share).expanduser() if args.share else None
            return start_webtop(
                lab,
                lab_id,
                pull=args.pull,
                share=share,
                image=args.image or WEBTOP_IMAGE,
            )
        raise SystemExit(f"unknown kind {kind}")
    except BaseException:
        if state and state.get("id"):
            stop_lab(str(state["id"]))
        else:
            shutil.rmtree(lab, ignore_errors=True)
        raise


def capture_state(state: dict[str, Any], args: argparse.Namespace) -> Path:
    kind = str(state.get("kind"))
    dest = (
        Path(args.output).expanduser()
        if args.output
        else default_png(str(state["id"]), kind)
    )
    if kind == "chrome":
        return capture_chrome(state, dest)
    if kind == "chrome-shot":
        raise SystemExit("chrome-shot already captured during start")
    if kind == "webtop":
        url = str(state.get("url") or "")
        if not url:
            raise SystemExit("webtop has no mapped URL yet")
        lab = _lab_dir(str(state["id"]))
        return start_chrome_shot(url, dest, lab)
    return capture_window(state, dest, args.title or state.get("title"))


def cmd_start(args: argparse.Namespace) -> int:
    state = start_kind(args)
    print(json.dumps(state, indent=2))
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    if args.all:
        ids = [str(s.get("id")) for s in list_labs() if s.get("id")]
    elif args.id:
        ids = [args.id]
    else:
        raise SystemExit("stop needs ID or --all")
    out = [stop_lab(lab_id) for lab_id in ids]
    print(json.dumps(out, indent=2))
    return 0


def cmd_gc(args: argparse.Namespace) -> int:
    stopped = gc(stale_min=None if args.all else args.stale_min, all_labs=args.all)
    print(json.dumps({"stopped": stopped}, indent=2))
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    print(json.dumps(list_labs(), indent=2))
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    state = load_state(args.id)
    path = capture_state(state, args)
    print(path)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    state: dict[str, Any] | None = None
    rc = 0
    png: Path | None = None
    try:
        state = start_kind(args)
        if state.get("kind") == "chrome-shot":
            print(state["png"])
            return 0
        if args.capture or args.output:
            time.sleep(0.4)
            png = capture_state(state, args)
            print(png)
        if args.command:
            env = os.environ.copy()
            env["EPHEMERAL_DISPLAY_ID"] = str(state["id"])
            env["EPHEMERAL_DISPLAY_KIND"] = str(state.get("kind"))
            if state.get("url"):
                env["EPHEMERAL_DISPLAY_URL"] = str(state["url"])
            ran = subprocess.run(args.command, check=False, env=env)
            rc = int(ran.returncode)
            if png is None:
                print(json.dumps({"id": state["id"], "command_exit": rc}))
        if png is None and not args.command:
            print(json.dumps(state, indent=2))
        return rc
    finally:
        if state and state.get("kind") != "chrome-shot" and state.get("id"):
            stop_lab(str(state["id"]))


def cmd_doctor(_args: argparse.Namespace) -> int:
    rows = {
        "kwin_wayland": str(_which(["kwin_wayland"]) or ""),
        "plasmawindowed": str(_which(["plasmawindowed"]) or ""),
        "qml": str(_which(["qml", "qml6"]) or ""),
        "chromium": str(
            _which(["chromium", "google-chrome-stable", "google-chrome"]) or ""
        ),
        "docker": str(_which(["docker"]) or ""),
        "screenshot-window": str(screenshot_window_bin() or ""),
        "state_root": str(STATE_ROOT),
        "shot_dir": str(SHOT_DIR),
        "protected_pids": sorted(live_protected_pids()),
    }
    print(json.dumps(rows, indent=2))
    return 0


def cmd_self_test(_args: argparse.Namespace) -> int:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    protected = live_protected_pids()
    sleeper = subprocess.Popen(
        ["sleep", "30"],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    lab_id = f"selftest-{secrets.token_hex(3)}"
    lab = _lab_dir(lab_id)
    lab.mkdir(parents=True, exist_ok=True)
    marker = lab / "marker"
    marker.write_text("1\n", encoding="utf-8")
    save_state(
        {
            "id": lab_id,
            "kind": "app",
            "pgid": sleeper.pid,
            "pids": [sleeper.pid],
            "created": _now(),
            "created_unix": time.time(),
            "cmd": ["sleep", "30", f"/tmp/ephemeral-display/{lab_id}"],
        }
    )
    before = set(protected)
    stop_lab(lab_id)
    try:
        sleeper.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass
    if _pid_alive(sleeper.pid):
        try:
            os.kill(sleeper.pid, signal.SIGKILL)
        except OSError:
            pass
        raise SystemExit("self-test: sleeper still alive after stop")
    after = live_protected_pids()
    if not before <= after:
        raise SystemExit(
            f"self-test: protected pids changed unexpectedly {before - after}"
        )
    if _lab_dir(lab_id).exists():
        raise SystemExit("self-test: lab dir remains")
    dest = SHOT_DIR / f"ephemeral-selftest-{_now()}.png"
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    html = "data:text/html,<html><body style='background:#123456'><h1>ephemeral</h1></body></html>"
    chrome_lab = _lab_dir(f"selftest-chrome-{secrets.token_hex(2)}")
    chrome_lab.mkdir(parents=True, exist_ok=True)
    try:
        png = start_chrome_shot(html, dest, chrome_lab)
    finally:
        shutil.rmtree(chrome_lab, ignore_errors=True)
    if not png.is_file() or png.stat().st_size < 32:
        raise SystemExit("self-test: chrome-shot produced no PNG")
    png.unlink()
    leftovers = [
        pid
        for pid in _lab_pids("selftest")
        if "chromium" in _proc_cmd(pid).casefold() or "chrome" in _proc_comm(pid)
    ]
    if leftovers:
        raise SystemExit(f"self-test: chromium leftover pids {leftovers}")
    print("self-test ok")
    return 0


def _add_kind_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("kind", choices=KINDS)
    p.add_argument("--applet", help="plasmawindowed applet id")
    p.add_argument("--file", help="QML file")
    p.add_argument("--url", help="URL for chrome / chrome-shot / webtop capture")
    p.add_argument("--title", help="window caption substring for wait/capture")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument(
        "--exec",
        help="inner command for nested-kwin / app (quoted; split with shlex)",
    )
    p.add_argument(
        "--virtual", action="store_true", help="nested-kwin virtual framebuffer"
    )
    p.add_argument(
        "--extra",
        action="append",
        default=None,
        help="extra arg for nested-kwin / app (repeatable)",
    )
    p.add_argument(
        "--share", help="host path to mount read-only into webtop /config/lab"
    )
    p.add_argument("--pull", action="store_true", help="docker pull webtop image")
    p.add_argument("--image", help="webtop image ref")
    p.add_argument("--output", "-o", help="PNG path")
    p.add_argument(
        "--stale-min", type=float, default=30.0, help="gc labs older than N minutes"
    )
    p.add_argument("--no-gc", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ephemeral-display",
        description="Agent-only display labs with guaranteed teardown.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    start_p = sub.add_parser(
        "start", help="start a lab and print JSON (caller must stop)"
    )
    _add_kind_flags(start_p)
    start_p.set_defaults(func=cmd_start)

    run_p = sub.add_parser("run", help="start, optional capture/command, always stop")
    _add_kind_flags(run_p)
    run_p.add_argument("--capture", action="store_true")
    run_p.set_defaults(func=cmd_run, command=None)

    cap = sub.add_parser("capture", help="screenshot a running lab")
    cap.add_argument("id")
    cap.add_argument("--title")
    cap.add_argument("-o", "--output")
    cap.set_defaults(func=cmd_capture)

    stop_p = sub.add_parser("stop", help="tear down one lab or all")
    stop_p.add_argument("id", nargs="?")
    stop_p.add_argument("--all", action="store_true")
    stop_p.set_defaults(func=cmd_stop)

    gc_p = sub.add_parser("gc", help="stop stale or dead labs")
    gc_p.add_argument("--all", action="store_true")
    gc_p.add_argument("--stale-min", type=float, default=30.0)
    gc_p.set_defaults(func=cmd_gc)

    st = sub.add_parser("status", help="list labs as JSON")
    st.set_defaults(func=cmd_status)

    doc = sub.add_parser("doctor", help="print binary and compositor probes")
    doc.set_defaults(func=cmd_doctor)

    test_p = sub.add_parser(
        "self-test", help="kill a fake lab and chrome-shot a data URL"
    )
    test_p.set_defaults(func=cmd_self_test)
    return p


def main() -> int:
    argv = sys.argv[1:]
    run_command: list[str] | None = None
    if argv and argv[0] == "run" and "--" in argv:
        idx = argv.index("--")
        run_command = argv[idx + 1 :]
        argv = argv[:idx]
    args = build_parser().parse_args(argv)
    if run_command is not None:
        args.command = run_command
    elif not hasattr(args, "command"):
        args.command = None
    return int(args.func(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130) from None
