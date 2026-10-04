#!/usr/bin/env python3
"""Poll session state and play evolving flock audio while busy, unique stings on alert."""

from __future__ import annotations

import os
import signal
import sys
import threading
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from config import load_config, muted
from flock import get_flock
from generate import mint_rtttl
from player import PcmPlayer
from state import CACHE_DIR, aggregate
from watcher import fallback_busy

PID_PATH = CACHE_DIR / "daemon.pid"
STAMP_PATH = CACHE_DIR / "last-generate"


class SessionTunes:
    def __init__(self) -> None:
        self.player = PcmPlayer()
        self.flock = get_flock()
        self.mode = "idle"
        self.busy_started = 0.0
        self.alert_hold_until = 0.0
        self.last_sting_at = 0.0
        self.last_sting_kind = ""
        self.last_sheep = ""
        self._cfg: dict = {}
        self._stop = threading.Event()

    def stop_audio(self) -> None:
        self.player.stop()
        self.mode = "idle"

    def _next_busy_pcm(self) -> bytes:
        cfg = load_config()
        self._cfg = cfg
        sheep = self.flock.breed_busy(cfg, save=False)
        self.last_sheep = sheep.sheep_id
        return self.flock.render(
            sheep,
            amplitude=float(cfg["busy_amplitude"]),
            sample_rate=int(cfg["sample_rate"]),
            modem_amplitude=float(cfg.get("modem_amplitude") or 0.0068),
            wave=str(cfg.get("wave") or "triangle"),
        )

    def start_busy(self, cfg: dict) -> None:
        self._cfg = cfg
        self.player.play_evolving(
            self._next_busy_pcm,
            sample_rate=int(cfg["sample_rate"]),
            pulse_volume=int(cfg["pulse_volume"]),
            stream_name="flock",
            fade_s=float(cfg.get("fade_s") or 0.9),
        )
        self.mode = "busy"
        self.busy_started = time.time()

    def play_sting(self, kind: str, cfg: dict) -> None:
        now = time.time()
        if kind == self.last_sting_kind and now - self.last_sting_at < float(
            cfg["sting_debounce_s"]
        ):
            self.mode = kind
            self.alert_hold_until = max(
                self.alert_hold_until, now + float(cfg["attention_hold_s"])
            )
            return
        sheep = self.flock.breed_alert(kind, cfg)
        amp = float(
            cfg["error_amplitude"] if kind == "error" else cfg["alert_amplitude"]
        )
        pcm = self.flock.render(
            sheep, amplitude=amp, sample_rate=int(cfg["sample_rate"])
        )
        self.player.play(
            pcm,
            sample_rate=int(cfg["sample_rate"]),
            pulse_volume=int(cfg["pulse_volume"]),
            stream_name=kind,
            loop=False,
        )
        self.last_sheep = sheep.sheep_id
        self.mode = kind
        self.last_sting_at = now
        self.last_sting_kind = kind
        self.alert_hold_until = now + float(cfg["attention_hold_s"])

    def desired(self, cfg: dict) -> str:
        agg = aggregate()
        fb = fallback_busy(float(cfg["activity_window_s"]))
        if agg in {"attention", "error"}:
            want = agg
        elif agg == "busy" or fb:
            want = "busy"
        else:
            want = "idle"
        now = time.time()
        if (
            self.mode in {"attention", "error"}
            and now < self.alert_hold_until
            and want == "busy"
        ):
            return self.mode
        return want

    def tick(self, cfg: dict) -> None:
        if not cfg.get("enabled", True) or muted():
            if self.mode != "idle":
                self.stop_audio()
            return
        want = self.desired(cfg)
        if want != self.mode:
            if want == "idle":
                self.stop_audio()
            elif want == "busy":
                self.start_busy(cfg)
            else:
                self.play_sting(want, cfg)


def _write_pid() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(os.getpid()) + "\n", encoding="utf-8")


def _maybe_generate(cfg: dict) -> None:
    interval = float(cfg.get("generate_interval_s") or 900)
    now = time.time()
    last = 0.0
    if STAMP_PATH.exists():
        try:
            last = float(STAMP_PATH.read_text(encoding="utf-8").strip() or 0)
        except ValueError:
            last = 0.0
    if last and now - last < interval:
        return
    flock = get_flock()
    batch = int(cfg.get("evolve_batch") or 10)
    for _ in range(batch):
        flock.breed_busy(cfg, save=False)
    flock.save()
    try:
        path = mint_rtttl("busy")
        flock.ingest_rtttl(path.read_text(encoding="utf-8"), kind="busy")
    except Exception as exc:  # noqa: BLE001 — Ollama mint is extra blood
        print(f"session-tunes ollama mint skipped: {exc}", flush=True)
    STAMP_PATH.parent.mkdir(parents=True, exist_ok=True)
    STAMP_PATH.write_text(str(now), encoding="utf-8")


def main() -> int:
    app = SessionTunes()

    def _shutdown(_signum: int, _frame: object) -> None:
        app._stop.set()
        app.stop_audio()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    _write_pid()
    print("session-tunes daemon started", flush=True)
    gen_at = time.time()
    while not app._stop.is_set():
        cfg = load_config()
        try:
            app.tick(cfg)
        except Exception as exc:  # noqa: BLE001 — keep the loop alive
            print(f"session-tunes tick error: {exc}", flush=True)
            app.stop_audio()
        if time.time() - gen_at >= 60:
            gen_at = time.time()
            threading.Thread(target=_maybe_generate, args=(cfg,), daemon=True).start()
        app._stop.wait(float(cfg.get("poll_interval_s") or 0.5))
    if PID_PATH.exists():
        PID_PATH.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
