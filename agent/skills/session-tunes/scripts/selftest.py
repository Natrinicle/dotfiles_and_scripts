#!/usr/bin/env python3
"""Parse every seed RTTTL and render PCM. Optional --play of a tiny blip."""

from __future__ import annotations

import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from calls import fingerprints_from_nodes, fingerprints_from_source_outputs
from config import SEED_LIB
from flock import Flock
from modem import render_modem
from player import parse_pactl_sections, pulse_fade_levels
from rtttl import parse_rtttl, render_pcm, serialize_rtttl


def run() -> list[str]:
    errors: list[str] = []
    files = sorted(SEED_LIB.glob("*.rtttl"))
    if len(files) < 3:
        errors.append(f"expected seed library, found {len(files)}")
        return errors
    for path in files:
        try:
            tune = parse_rtttl(path.read_text(encoding="utf-8"))
            pcm = render_pcm(tune, sample_rate=22050, amplitude=0.006)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path.name}: {exc}")
            continue
        if len(pcm) < 22050 * 2 // 2:
            errors.append(f"{path.name}: pcm too short ({len(pcm)} bytes)")
        print(
            f"ok {path.name:24} notes={len(tune.notes):2} "
            f"{tune.duration_s:5.2f}s  pcm={len(pcm)} bytes"
        )
    dotted = parse_rtttl("Simpsons:d=4,o=5,b=160:c.6,e6,f#6,8a6,g.6,e6,c6")
    if len(dotted.notes) < 7:
        errors.append(f"dotted-before-octave parse lost notes: {len(dotted.notes)}")
    else:
        print(f"ok dotted-octave form notes={len(dotted.notes)}")
    roundtrip = parse_rtttl(serialize_rtttl(dotted))
    if abs(roundtrip.duration_s - dotted.duration_s) > 1.5:
        errors.append("serialize_rtttl duration drifted too far")
    modem = render_modem(sample_rate=22050, amplitude=0.006)
    modem_s = len(modem) / (2 * 22050)
    if modem_s < 4.0 or modem_s > 16.0:
        errors.append(f"modem duration {modem_s:.2f}s out of range")
    else:
        print(f"ok {'computer-room':24} {modem_s:5.2f}s  pcm={len(modem)} bytes")
    tmp = Path("/tmp/session-tunes-selftest-flock")
    if tmp.exists():
        for child in tmp.glob("*"):
            child.unlink()
    tmp.mkdir(parents=True, exist_ok=True)
    flock = Flock(tmp)
    cfg = {
        "thinking_sound": "both",
        "flock_max": 40,
        "busy_amplitude": 0.006,
        "sample_rate": 22050,
    }
    a = flock.breed_busy(cfg)
    b = flock.breed_busy(cfg)
    pa = flock.render(a, amplitude=0.006, sample_rate=22050)
    pb = flock.render(b, amplitude=0.006, sample_rate=22050)
    if pa == pb:
        errors.append("two busy sheep rendered identical PCM")
    else:
        print(f"ok flock unique {a.sheep_id} vs {b.sheep_id}")
    att = flock.breed_alert("attention", cfg)
    err = flock.breed_alert("error", cfg)
    if att.bpm <= 170 or err.kind != "error":
        errors.append("alert genomes not urgent enough")
    else:
        print(f"ok alert bpm={att.bpm} error scale={err.scale}")
    levels = pulse_fade_levels(10)
    if not levels or levels[-1] != 0 or levels[0] >= 65536:
        errors.append(f"pulse fade levels wrong: {levels[:3]}…{levels[-1:]}")
    else:
        print(f"ok pulse fade steps={len(levels)} end={levels[-1]}")
    cam_run = [
        {
            "type": "PipeWire:Interface:Node",
            "info": {
                "state": "running",
                "props": {
                    "media.class": "Video/Source",
                    "media.role": "Camera",
                    "node.name": "v4l2_test_cam",
                },
            },
        }
    ]
    cam_fps = fingerprints_from_nodes(cam_run)
    if "camera:v4l2_test_cam" not in cam_fps:
        errors.append(f"running camera not detected: {cam_fps}")
    else:
        print("ok running camera fingerprint")
    cam_off = [
        {
            "type": "PipeWire:Interface:Node",
            "info": {
                "state": "suspended",
                "props": {
                    "media.class": "Video/Source",
                    "media.role": "Camera",
                    "node.name": "v4l2_test_cam",
                },
            },
        }
    ]
    if fingerprints_from_nodes(cam_off):
        errors.append("suspended camera treated as a call")
    else:
        print("ok suspended camera ignored")
    chrome_mic = [
        {
            "type": "PipeWire:Interface:Node",
            "info": {
                "state": "running",
                "props": {
                    "media.class": "Stream/Input/Audio",
                    "application.process.binary": "chrome",
                    "application.name": "Chrome",
                },
            },
        }
    ]
    if fingerprints_from_nodes(chrome_mic):
        errors.append("chrome mic without camera treated as a call")
    else:
        print("ok chrome mic alone ignored")
    chrome_call = fingerprints_from_nodes(cam_run + chrome_mic)
    if "camera:v4l2_test_cam" not in chrome_call or "mic:chrome" not in chrome_call:
        errors.append(f"chrome+camera not a call: {chrome_call}")
    else:
        print("ok chrome+camera fingerprint")
    zoom_mic = [
        {
            "type": "PipeWire:Interface:Node",
            "info": {
                "state": "running",
                "props": {
                    "media.class": "Stream/Input/Audio",
                    "application.process.binary": "zoom",
                },
            },
        }
    ]
    if "mic:zoom" not in fingerprints_from_nodes(zoom_mic):
        errors.append("zoom mic not detected")
    else:
        print("ok zoom mic fingerprint")
    pactl_text = (
        "Source Output #9\n"
        "\tProperties:\n"
        '\t\tapplication.process.binary = "zoom"\n'
        '\t\tapplication.name = "Zoom"\n'
    )
    blocks = parse_pactl_sections(pactl_text, "Source Output #")
    pactl_fps = fingerprints_from_source_outputs(blocks, camera_on=False)
    if "mic:zoom" not in pactl_fps:
        errors.append(f"pactl zoom capture missed: {pactl_fps}")
    else:
        print("ok pactl zoom capture")
    return errors


def play_blip() -> None:
    from player import PcmPlayer

    path = next(SEED_LIB.glob("alert-*.rtttl"))
    tune = parse_rtttl(path.read_text(encoding="utf-8"))
    pcm = render_pcm(tune, sample_rate=22050, amplitude=0.006)
    player = PcmPlayer()
    player.play(
        pcm, sample_rate=22050, pulse_volume=32768, stream_name="selftest", loop=False
    )
    time.sleep(min(tune.duration_s + 0.2, 4.0))
    player.stop()
    print(f"played quiet blip from {path.name}")


def main() -> int:
    errors = run()
    if "--play" in sys.argv:
        try:
            play_blip()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"play: {exc}")
    if errors:
        print("FAIL", file=sys.stderr)
        for item in errors:
            print(item, file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
