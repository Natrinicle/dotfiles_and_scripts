"""Paths and user config for session-tunes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import tomllib

SKILL_DIR = Path(__file__).resolve().parent.parent
SEED_LIB = SKILL_DIR / "library"
USER_LIB = Path.home() / ".local" / "share" / "session-tunes" / "library"
FLOCK_DIR = Path.home() / ".local" / "share" / "session-tunes" / "flock"
CONFIG_DIR = Path.home() / ".config" / "session-tunes"
CONFIG_PATH = CONFIG_DIR / "config.toml"
MUTE_PATH = CONFIG_DIR / "mute"
EXAMPLE_CONFIG = SKILL_DIR / "share" / "config.toml"

DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "sample_rate": 22050,
    "busy_amplitude": 0.0045,
    "modem_amplitude": 0.0051,
    "alert_amplitude": 0.0106,
    "error_amplitude": 0.0138,
    "pulse_volume": 65536,
    "fade_s": 0.9,
    "flock_max": 250,
    "modem_chance": 0.15,
    "evolve_batch": 10,
    "poll_interval_s": 0.5,
    "generate_interval_s": 900,
    "activity_window_s": 8.0,
    "attention_hold_s": 12.0,
    "busy_rotate_s": 180.0,
    "sting_debounce_s": 20.0,
    "ollama_url": "http://127.0.0.1:11434",
    "ollama_model": "gemma4",
    "wave": "triangle",
    "thinking_sound": "peppy",
}


def muted() -> bool:
    return MUTE_PATH.exists()


def set_muted(value: bool) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if value:
        MUTE_PATH.write_text("1\n", encoding="utf-8")
    elif MUTE_PATH.exists():
        MUTE_PATH.unlink()


def load_config() -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    if not CONFIG_PATH.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if EXAMPLE_CONFIG.exists():
            CONFIG_PATH.write_text(
                EXAMPLE_CONFIG.read_text(encoding="utf-8"), encoding="utf-8"
            )
        else:
            CONFIG_PATH.write_text(_dumps(DEFAULTS), encoding="utf-8")
    try:
        parsed = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return cfg
    if isinstance(parsed, dict):
        for key, value in parsed.items():
            if key in cfg:
                cfg[key] = value
    return cfg


def _dumps(data: dict[str, Any]) -> str:
    lines = [
        "# Quiet RTTTL / 70s computer-room analog beeps while Grok/Claude work.",
        "# PCM amplitude is the volume control. Keep this tiny.",
        "",
    ]
    for key, value in data.items():
        if isinstance(value, bool):
            lines.append(f"{key} = {str(value).lower()}")
        elif isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        else:
            lines.append(f"{key} = {value}")
    return "\n".join(lines) + "\n"


def library_files() -> list[Path]:
    files: list[Path] = []
    for root in (SEED_LIB, USER_LIB):
        if not root.exists():
            continue
        files.extend(sorted(root.glob("*.rtttl")))
    return files


def busy_library_files() -> list[Path]:
    out: list[Path] = []
    for path in library_files():
        name = path.stem.lower()
        if name.startswith(("alert", "error")):
            continue
        out.append(path)
    return out


def files_for_kind(kind: str) -> list[Path]:
    kind = kind.lower()
    prefixes = {
        "busy": ("busy-",),
        "alert": ("alert-", "need"),
        "error": ("error-", "fail"),
    }[kind]
    out: list[Path] = []
    for path in library_files():
        name = path.stem.lower()
        if any(name.startswith(p) or p in name for p in prefixes):
            out.append(path)
    return out
