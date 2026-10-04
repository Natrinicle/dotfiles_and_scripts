"""Play s16le PCM through PulseAudio/PipeWire at a capped volume."""

from __future__ import annotations

import array
import os
import subprocess
import threading
from collections.abc import Callable
from typing import IO


def _paplay_cmd(sample_rate: int, pulse_volume: int, stream_name: str) -> list[str]:
    vol = max(0, min(int(pulse_volume), 65536))
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


class PcmPlayer:
    """Feed PCM to paplay. loop=True repeats one buffer; play_evolving crossfades."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen[bytes] | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def running(self) -> bool:
        proc = self._proc
        return proc is not None and proc.poll() is None

    def stop(self) -> None:
        self._stop.set()
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        if proc.stdin:
            try:
                proc.stdin.close()
            except OSError:
                pass
        proc.terminate()
        try:
            proc.wait(timeout=1.5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=1)

    def play(
        self,
        pcm: bytes,
        *,
        sample_rate: int,
        pulse_volume: int,
        stream_name: str,
        loop: bool,
    ) -> None:
        self.stop()
        if not pcm:
            return
        self._stop.clear()
        env = os.environ.copy()
        env["PULSE_PROP_media.role"] = "abstract"
        env["PULSE_PROP_application.name"] = "session-tunes"
        proc = subprocess.Popen(
            _paplay_cmd(sample_rate, pulse_volume, stream_name),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        self._proc = proc

        def _feed(stdin: IO[bytes]) -> None:
            try:
                if loop:
                    while not self._stop.is_set() and proc.poll() is None:
                        stdin.write(pcm)
                        stdin.flush()
                else:
                    stdin.write(pcm)
                    stdin.flush()
            except (BrokenPipeError, OSError):
                return
            finally:
                try:
                    stdin.close()
                except OSError:
                    pass

        assert proc.stdin is not None
        self._thread = threading.Thread(target=_feed, args=(proc.stdin,), daemon=True)
        self._thread.start()

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
        self._stop.clear()
        env = os.environ.copy()
        env["PULSE_PROP_media.role"] = "abstract"
        env["PULSE_PROP_application.name"] = "session-tunes"
        proc = subprocess.Popen(
            _paplay_cmd(sample_rate, pulse_volume, stream_name),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        self._proc = proc
        fade_n = max(1, int(sample_rate * max(0.15, fade_s)))

        def _feed(stdin: IO[bytes]) -> None:
            try:
                current = array.array("h")
                first = next_pcm()
                if not first:
                    return
                current.frombytes(first)
                body_end = max(0, len(current) - fade_n)
                stdin.write(current[:body_end].tobytes())
                stdin.flush()
                while not self._stop.is_set() and proc.poll() is None:
                    nxt_bytes = next_pcm()
                    if not nxt_bytes:
                        break
                    nxt = array.array("h")
                    nxt.frombytes(nxt_bytes)
                    mixed = _crossfade(current, nxt, fade_n)
                    stdin.write(mixed.tobytes())
                    rest_end = max(0, len(nxt) - fade_n)
                    if rest_end > fade_n:
                        stdin.write(nxt[fade_n:rest_end].tobytes())
                    stdin.flush()
                    current = nxt
            except (BrokenPipeError, OSError):
                return
            finally:
                try:
                    stdin.close()
                except OSError:
                    pass

        assert proc.stdin is not None
        self._thread = threading.Thread(target=_feed, args=(proc.stdin,), daemon=True)
        self._thread.start()
