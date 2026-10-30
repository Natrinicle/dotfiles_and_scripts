"""Play s16le PCM through PulseAudio/PipeWire at a capped volume."""

from __future__ import annotations

import array
import os
import subprocess
import threading
import time
from collections.abc import Callable
from typing import IO

CHUNK_SAMPLES = 2048
BUSY_VOICE = "busy"
STING_VOICE = "sting"


def _paplay_cmd(
    sample_rate: int, pulse_volume: int, stream_name: str, voice: str
) -> list[str]:
    vol = max(0, min(int(pulse_volume), 65536))
    app_id = f"session-tunes.{voice}"
    return [
        "paplay",
        "--raw",
        f"--rate={sample_rate}",
        "--format=s16le",
        "--channels=1",
        f"--volume={vol}",
        "--client-name=session-tunes",
        f"--stream-name={stream_name}",
        "--property=media.role=abstract",
        "--property=media.name=session-tunes",
        f"--property=application.id={app_id}",
    ]


def _crossfade(tail: array.array, head: array.array, n: int) -> array.array:
    n = min(n, len(tail), len(head))
    if n <= 0:
        return array.array("h")
    out = array.array("h")
    for i in range(n):
        t = i / n
        v = int(tail[len(tail) - n + i] * (1.0 - t) + head[i] * t)
        if v > 32767:
            v = 32767
        elif v < -32768:
            v = -32768
        out.append(v)
    return out


def pulse_fade_levels(steps: int) -> list[int]:
    """Integer Pulse volumes from just below full down to 0."""
    steps = max(1, int(steps))
    return [int(65536 * (1.0 - (i + 1) / steps)) for i in range(steps)]


def parse_pactl_sections(text: str, header_prefix: str) -> list[dict[str, str]]:
    """Parse `pactl list` blocks into dicts of property key → value."""
    blocks: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith(header_prefix):
            if current:
                blocks.append(current)
            current = {"index": line.split("#", 1)[-1].strip()}
            continue
        if current is None or "=" not in line:
            continue
        key, _, value = line.strip().partition("=")
        current[key.strip()] = value.strip().strip('"')
    if current:
        blocks.append(current)
    return blocks


def _pactl_list(kind: str) -> str:
    try:
        result = subprocess.run(
            ["pactl", "list", kind],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout or ""


def _sink_input_index(pid: int, voice: str) -> str | None:
    app_id = f"session-tunes.{voice}"
    pid_s = str(pid)
    for _ in range(8):
        blocks = parse_pactl_sections(_pactl_list("sink-inputs"), "Sink Input #")
        for block in blocks:
            if block.get("application.id") == app_id:
                return block.get("index")
        for block in blocks:
            if (
                block.get("application.process.id") == pid_s
                and block.get("application.name") == "session-tunes"
            ):
                return block.get("index")
        time.sleep(0.04)
    return None


def _ramp_sink_volume(pid: int, voice: str, fade_s: float) -> None:
    fade_s = max(0.05, float(fade_s))
    index = _sink_input_index(pid, voice)
    if index is None:
        return
    steps = max(4, int(fade_s / 0.05))
    levels = pulse_fade_levels(steps)
    dt = fade_s / steps
    for volume in levels:
        try:
            subprocess.run(
                ["pactl", "set-sink-input-volume", index, str(volume)],
                capture_output=True,
                timeout=0.5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return
        time.sleep(dt)


class _Voice:
    def __init__(self, name: str) -> None:
        self.name = name
        self.proc: subprocess.Popen[bytes] | None = None
        self.thread: threading.Thread | None = None
        self.stop = threading.Event()
        self.fade = threading.Event()
        self.lock = threading.Lock()


class PcmPlayer:
    """Feed PCM to paplay. One busy flock voice plus one sting; Pulse ramps fade."""

    def __init__(self) -> None:
        self._voices: dict[str, _Voice] = {}
        self._fade_threads: list[threading.Thread] = []
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        for voice in list(self._voices.values()):
            proc = voice.proc
            if proc is not None and proc.poll() is None:
                return True
        return False

    def stop(self, name: str | None = None) -> None:
        names = [name] if name else list(self._voices)
        for voice_name in names:
            voice = self._voices.get(voice_name)
            if voice is not None:
                self._kill_voice(voice)

    def fade_stop(
        self,
        name: str | None = None,
        *,
        fade_s: float = 0.9,
        wait: bool = False,
    ) -> None:
        names = [name] if name else list(self._voices)
        threads: list[threading.Thread] = []
        for voice_name in names:
            voice = self._voices.get(voice_name)
            if voice is None or voice.proc is None:
                continue
            voice.fade.set()
            thread = threading.Thread(
                target=self._fade_then_kill,
                args=(voice, fade_s),
                daemon=True,
            )
            thread.start()
            threads.append(thread)
            self._fade_threads.append(thread)
        if wait:
            timeout = max(0.2, float(fade_s) + 0.6)
            for thread in threads:
                thread.join(timeout=timeout)

    def fade_stop_all(self, *, fade_s: float = 0.9, wait: bool = False) -> None:
        self.fade_stop(None, fade_s=fade_s, wait=wait)

    def wait_idle(self, timeout: float) -> bool:
        deadline = time.time() + max(0.0, timeout)
        while time.time() < deadline:
            if not self.running:
                return True
            time.sleep(0.05)
        self.stop()
        return not self.running

    def play(
        self,
        pcm: bytes,
        *,
        sample_rate: int,
        pulse_volume: int,
        stream_name: str,
        loop: bool,
        voice: str = STING_VOICE,
    ) -> None:
        self.stop()
        if not pcm:
            return
        self._start_feed(
            voice,
            stream_name=stream_name,
            sample_rate=sample_rate,
            pulse_volume=pulse_volume,
            feeder=lambda stdin, proc, current: self._feed_oneshot(
                stdin, proc, current, pcm, loop
            ),
        )

    def play_evolving(
        self,
        next_pcm: Callable[[], bytes],
        *,
        sample_rate: int,
        pulse_volume: int,
        stream_name: str,
        fade_s: float = 0.9,
    ) -> None:
        self.stop()
        fade_n = max(1, int(sample_rate * max(0.15, fade_s)))
        self._start_feed(
            BUSY_VOICE,
            stream_name=stream_name,
            sample_rate=sample_rate,
            pulse_volume=pulse_volume,
            feeder=lambda stdin, proc, current: self._feed_evolving(
                stdin, proc, current, next_pcm, fade_n
            ),
        )

    def play_solo(
        self,
        pcm: bytes,
        *,
        sample_rate: int,
        pulse_volume: int,
        stream_name: str,
        fade_s: float = 0.9,
    ) -> None:
        """Start a sting while the busy flock fades out (LeadStinger solo)."""
        self.fade_stop(BUSY_VOICE, fade_s=fade_s, wait=False)
        sting = self._voices.get(STING_VOICE)
        if sting is not None:
            self.fade_stop(STING_VOICE, fade_s=min(0.15, fade_s), wait=False)
        if not pcm:
            return
        self._start_feed(
            STING_VOICE,
            stream_name=stream_name,
            sample_rate=sample_rate,
            pulse_volume=pulse_volume,
            feeder=lambda stdin, proc, current: self._feed_oneshot(
                stdin, proc, current, pcm, False
            ),
        )

    def _start_feed(
        self,
        name: str,
        *,
        stream_name: str,
        sample_rate: int,
        pulse_volume: int,
        feeder: Callable[[IO[bytes], subprocess.Popen[bytes], _Voice], None],
    ) -> None:
        existing = self._voices.get(name)
        if existing is not None:
            self._kill_voice(existing)
        voice = _Voice(name)
        voice.stop.clear()
        voice.fade.clear()
        env = os.environ.copy()
        env["PULSE_PROP_media.role"] = "abstract"
        env["PULSE_PROP_application.name"] = "session-tunes"
        env["PULSE_PROP_application.id"] = f"session-tunes.{name}"
        proc = subprocess.Popen(
            _paplay_cmd(sample_rate, pulse_volume, stream_name, name),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        voice.proc = proc
        with self._lock:
            self._voices[name] = voice

        def _run() -> None:
            stdin = proc.stdin
            if stdin is None:
                return
            try:
                feeder(stdin, proc, voice)
            except (BrokenPipeError, OSError):
                return
            finally:
                try:
                    stdin.close()
                except OSError:
                    pass

        voice.thread = threading.Thread(target=_run, daemon=True)
        voice.thread.start()

    def _feed_oneshot(
        self,
        stdin: IO[bytes],
        proc: subprocess.Popen[bytes],
        voice: _Voice,
        pcm: bytes,
        loop: bool,
    ) -> None:
        chunk = CHUNK_SAMPLES * 2
        while (
            not voice.stop.is_set() and not voice.fade.is_set() and proc.poll() is None
        ):
            data = pcm
            offset = 0
            while offset < len(data):
                if (
                    voice.stop.is_set()
                    or voice.fade.is_set()
                    or proc.poll() is not None
                ):
                    return
                stdin.write(data[offset : offset + chunk])
                stdin.flush()
                offset += chunk
            if not loop:
                return

    def _feed_evolving(
        self,
        stdin: IO[bytes],
        proc: subprocess.Popen[bytes],
        voice: _Voice,
        next_pcm: Callable[[], bytes],
        fade_n: int,
    ) -> None:
        current = array.array("h")
        first = next_pcm()
        if not first:
            return
        current.frombytes(first)
        body_end = max(0, len(current) - fade_n)
        self._write_chunks(stdin, proc, voice, current[:body_end])
        while not voice.stop.is_set() and proc.poll() is None:
            if voice.fade.is_set():
                return
            nxt_bytes = next_pcm()
            if not nxt_bytes:
                return
            nxt = array.array("h")
            nxt.frombytes(nxt_bytes)
            mixed = _crossfade(current, nxt, fade_n)
            self._write_chunks(stdin, proc, voice, mixed)
            rest_end = max(0, len(nxt) - fade_n)
            if rest_end > fade_n:
                self._write_chunks(stdin, proc, voice, nxt[fade_n:rest_end])
            current = nxt

    def _write_chunks(
        self,
        stdin: IO[bytes],
        proc: subprocess.Popen[bytes],
        voice: _Voice,
        samples: array.array,
    ) -> None:
        pos = 0
        n = len(samples)
        while pos < n:
            if voice.stop.is_set() or voice.fade.is_set() or proc.poll() is not None:
                return
            end = min(n, pos + CHUNK_SAMPLES)
            stdin.write(samples[pos:end].tobytes())
            stdin.flush()
            pos = end

    def _fade_then_kill(self, voice: _Voice, fade_s: float) -> None:
        proc = voice.proc
        pid = proc.pid if proc is not None else None
        if pid is not None and fade_s > 0:
            _ramp_sink_volume(pid, voice.name, fade_s)
        self._kill_voice(voice)

    def _kill_voice(self, voice: _Voice) -> None:
        voice.stop.set()
        voice.fade.set()
        with voice.lock:
            proc = voice.proc
            voice.proc = None
        if proc is not None:
            if proc.stdin:
                try:
                    proc.stdin.close()
                except OSError:
                    pass
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=1.5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=1)
        with self._lock:
            if self._voices.get(voice.name) is voice:
                self._voices.pop(voice.name, None)
