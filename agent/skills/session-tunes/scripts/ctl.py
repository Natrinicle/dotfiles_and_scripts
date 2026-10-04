#!/usr/bin/env python3
"""session-tunes CLI: install, status, mute, test, generate-now."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from config import CONFIG_PATH, MUTE_PATH, SKILL_DIR, load_config, muted, set_muted
from flock import get_flock
from generate import mint_rtttl
from modem import render_modem
from player import PcmPlayer
from state import STATE_PATH, aggregate, load_state
from watcher import fallback_busy


def cmd_install(*, enable: bool) -> int:
    unit_src = SKILL_DIR / "share" / "session-tunes.service"
    unit_dest = Path.home() / ".config/systemd/user/session-tunes.service"
    if not unit_src.is_file():
        print(f"missing unit: {unit_src}", file=sys.stderr)
        return 1
    unit_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(unit_src, unit_dest)
    load_config()
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    if enable:
        result = subprocess.run(
            ["systemctl", "--user", "enable", "--now", "session-tunes.service"],
            check=False,
        )
        if result.returncode != 0:
            print(
                "unit copied; enable later with session-tunes install --enable",
                file=sys.stderr,
            )
            return result.returncode
        print(f"enabled {unit_dest}")
        return 0
    print(f"installed {unit_dest}")
    print("enable with: session-tunes install --enable")
    return 0


def cmd_status() -> int:
    cfg = load_config()
    data = load_state()
    print(f"enabled: {cfg.get('enabled', True)}")
    print(f"muted: {muted()} ({MUTE_PATH})")
    print(f"aggregate: {aggregate(data)}")
    print(f"fallback_busy: {fallback_busy(float(cfg['activity_window_s']))}")
    print(f"config: {CONFIG_PATH}")
    print(f"state: {STATE_PATH}")
    print(
        f"busy_amplitude: {cfg['busy_amplitude']}  "
        f"modem_amplitude: {cfg.get('modem_amplitude')}  "
        f"alert_amplitude: {cfg['alert_amplitude']}  "
        f"error_amplitude: {cfg.get('error_amplitude', 0.018)}"
    )
    print(
        f"thinking_sound: {cfg.get('thinking_sound', 'peppy')}  "
        f"wave: {cfg.get('wave')}  "
        f"generate_interval_s: {cfg.get('generate_interval_s')}"
    )
    print(f"flock: {get_flock().stats()}")
    sessions = data.get("sessions") or {}
    if not sessions:
        print("sessions: (none)")
        return 0
    print("sessions:")
    print(json.dumps(sessions, indent=2, sort_keys=True))
    return 0


def cmd_test(kind: str) -> int:
    cfg = load_config()
    sr = int(cfg["sample_rate"])
    vol = int(cfg["pulse_volume"])
    flock = get_flock()
    if kind == "modem":
        amp = float(cfg.get("modem_amplitude") or 0.0068)
        pcm = render_modem(
            sample_rate=sr,
            amplitude=amp,
            seed=int(time.time()) & 0x7FFFFFFF,
        )
        dur = len(pcm) / (2 * sr)
        label = f"bell103-modem ({dur:.1f}s, amp={amp})"
    else:
        if kind == "busy":
            sheep = flock.breed_busy(cfg)
            amp = float(cfg["busy_amplitude"])
        else:
            sheep = flock.breed_alert(kind, cfg)
            amp = float(
                cfg["error_amplitude"] if kind == "error" else cfg["alert_amplitude"]
            )
        pcm = flock.render(
            sheep,
            amplitude=amp,
            sample_rate=sr,
            modem_amplitude=float(cfg.get("modem_amplitude") or 0.0068),
            wave=str(cfg.get("wave") or "triangle"),
        )
        dur = len(pcm) / (2 * sr)
        title = ""
        if sheep.rtttl_line and ":" in sheep.rtttl_line:
            title = sheep.rtttl_line.split(":", 1)[0]
        mix = f" modem={sheep.modem_mix:.2f}" if sheep.modem_mix > 0.04 else ""
        label = (
            f"sheep {sheep.sheep_id} gen={sheep.generation} "
            f"{title} ({dur:.1f}s, amp={amp}{mix})"
        )
    player = PcmPlayer()
    print(f"playing {label}")
    player.play(
        pcm,
        sample_rate=sr,
        pulse_volume=vol,
        stream_name=f"test-{kind}",
        loop=False,
    )
    time.sleep(min(dur + 0.3, 10.0))
    player.stop()
    return 0


def cmd_generate(kind: str) -> int:
    cfg = load_config()
    flock = get_flock()
    if kind == "busy":
        sheep = flock.breed_busy(cfg)
    else:
        sheep = flock.breed_alert(kind, cfg)
    print(f"bred {sheep.sheep_id} gen={sheep.generation}")
    try:
        path = mint_rtttl(kind)
        flock.ingest_rtttl(path.read_text(encoding="utf-8"), kind=kind)
        print(path)
    except Exception as exc:  # noqa: BLE001
        print(f"ollama mint skipped: {exc}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="session-tunes")
    sub = parser.add_subparsers(dest="cmd", required=True)
    inst = sub.add_parser("install")
    inst.add_argument(
        "--enable",
        action="store_true",
        help="enable and start the user unit",
    )
    sub.add_parser("status")
    sub.add_parser("mute")
    sub.add_parser("unmute")
    t = sub.add_parser("test")
    t.add_argument(
        "kind",
        nargs="?",
        default="busy",
        choices=("busy", "alert", "error", "modem"),
    )
    g = sub.add_parser("generate-now")
    g.add_argument(
        "kind", nargs="?", default="busy", choices=("busy", "alert", "error")
    )
    args = parser.parse_args()
    if args.cmd == "install":
        return cmd_install(enable=args.enable)
    if args.cmd == "status":
        return cmd_status()
    if args.cmd == "mute":
        set_muted(True)
        print("muted")
        return 0
    if args.cmd == "unmute":
        set_muted(False)
        print("unmuted")
        return 0
    if args.cmd == "test":
        return cmd_test(args.kind)
    if args.cmd == "generate-now":
        return cmd_generate(args.kind)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
