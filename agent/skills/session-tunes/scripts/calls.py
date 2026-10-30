"""Detect live video calls from PipeWire camera/RTC nodes and Pulse capture."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from player import parse_pactl_sections

CALL_ROLES = frozenset({"phone", "communication"})
BROWSER_BINS = frozenset(
    {
        "brave",
        "chrome",
        "chrome-wrapper",
        "chromium",
        "firefox",
        "firefox-esr",
        "google-chrome",
        "google-chrome-stable",
        "microsoft-edge",
        "msedge",
        "opera",
        "vivaldi-bin",
    }
)
MEETING_NEEDLES = (
    "ciscocollabhost",
    "discord",
    "element",
    "signal-desktop",
    "skype",
    "slack",
    "teams",
    "telegram-desktop",
    "webex",
    "zoom",
)
IGNORE_BINS = frozenset(
    {"pacat", "paplay", "pipewire", "pulseaudio", "session-tunes", "wireplumber"}
)


def _norm_bin(raw: str) -> str:
    return Path(raw.strip().strip('"')).name.lower()


def _is_meeting(binary: str) -> bool:
    if not binary or binary in IGNORE_BINS:
        return False
    return any(needle in binary for needle in MEETING_NEEDLES)


def fingerprints_from_nodes(objs: list[Any]) -> set[str]:
    """Map pw-dump Node objects to call fingerprints (no tab titles)."""
    camera_on = False
    fps: set[str] = set()
    parsed: list[tuple[str, str, str, str, str]] = []
    for obj in objs:
        if not isinstance(obj, dict):
            continue
        typ = str(obj.get("type") or "")
        if typ and typ != "PipeWire:Interface:Node":
            continue
        info = obj.get("info") or {}
        if not isinstance(info, dict):
            continue
        props = info.get("props") or {}
        if not isinstance(props, dict):
            continue
        state = str(info.get("state") or "").lower()
        media_class = str(props.get("media.class") or "")
        role = str(props.get("media.role") or "").lower()
        node_name = str(props.get("node.name") or "node")
        binary = _norm_bin(
            str(
                props.get("application.process.binary")
                or props.get("application.name")
                or ""
            )
        )
        parsed.append((state, media_class, role, node_name, binary))
        if media_class == "Video/Source" and role == "camera" and state == "running":
            fps.add(f"camera:{node_name}")
            camera_on = True
        if media_class == "Stream/Input/Video" and state in {"running", "idle"}:
            fps.add(f"video-in:{binary or node_name}")
            camera_on = True
    for state, media_class, role, node_name, binary in parsed:
        if binary in IGNORE_BINS:
            continue
        if role in CALL_ROLES and "Input" in media_class and state == "running":
            fps.add(f"role:{role}:{binary or node_name}")
        if media_class != "Stream/Input/Audio" or state != "running":
            continue
        if (
            _is_meeting(binary)
            or binary in BROWSER_BINS
            and (camera_on or role in CALL_ROLES)
        ):
            fps.add(f"mic:{binary}")
    return fps


def fingerprints_from_source_outputs(
    blocks: list[dict[str, str]], *, camera_on: bool
) -> set[str]:
    fps: set[str] = set()
    for block in blocks:
        binary = _norm_bin(
            block.get("application.process.binary")
            or block.get("application.name")
            or ""
        )
        if binary in IGNORE_BINS:
            continue
        role = (block.get("media.role") or "").lower()
        if role in CALL_ROLES:
            fps.add(f"role:{role}:{binary or 'mic'}")
        elif (
            _is_meeting(binary)
            or binary in BROWSER_BINS
            and (camera_on or role in CALL_ROLES)
        ):
            fps.add(f"mic:{binary}")
    return fps


def _pw_nodes() -> list[Any]:
    try:
        result = subprocess.run(
            ["pw-dump", "Node"],
            capture_output=True,
            timeout=1,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0 or not result.stdout:
        return []
    try:
        data = json.loads(result.stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _pactl_source_outputs() -> list[dict[str, str]]:
    try:
        result = subprocess.run(
            ["pactl", "list", "source-outputs"],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return parse_pactl_sections(result.stdout or "", "Source Output #")


def call_fingerprints() -> set[str]:
    """Stable ids for an active video call / camera capture. Empty if none."""
    nodes = _pw_nodes()
    fps = fingerprints_from_nodes(nodes)
    camera_on = any(item.startswith(("camera:", "video-in:")) for item in fps)
    fps |= fingerprints_from_source_outputs(
        _pactl_source_outputs(), camera_on=camera_on
    )
    return fps
