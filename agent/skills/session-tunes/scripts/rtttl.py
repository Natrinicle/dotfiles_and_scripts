"""Parse Nokia RTTTL ringtone codes and render quiet PCM."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

NOTE_SEMITONE = {
    "c": 0,
    "c#": 1,
    "d": 2,
    "d#": 3,
    "e": 4,
    "f": 5,
    "f#": 6,
    "g": 7,
    "g#": 8,
    "a": 9,
    "a#": 10,
    "h": 11,  # German B
    "b": 11,
}

_NOTE_RE = re.compile(
    r"^(?P<dur>\d+)?(?P<note>p|[a-h]#?)(?P<rest>.*)$",
    re.IGNORECASE,
)
_SEMI_TO_NOTE = {
    0: "c",
    1: "c#",
    2: "d",
    3: "d#",
    4: "e",
    5: "f",
    6: "f#",
    7: "g",
    8: "g#",
    9: "a",
    10: "a#",
    11: "b",
}


@dataclass(frozen=True)
class RtttlTune:
    name: str
    bpm: int
    default_duration: int
    default_octave: int
    notes: tuple[tuple[float, float], ...]  # (freq_hz or 0, duration_s)

    @property
    def duration_s(self) -> float:
        return sum(d for _f, d in self.notes)


def parse_rtttl(text: str) -> RtttlTune:
    raw = text.strip().splitlines()
    line = next(
        (ln.strip() for ln in raw if ln.strip() and not ln.strip().startswith("#")), ""
    )
    if not line:
        raise ValueError("empty RTTTL")
    first = line.find(":")
    second = line.find(":", first + 1) if first >= 0 else -1
    if first < 0 or second < 0:
        raise ValueError(f"RTTTL needs name:defaults:notes, got {line[:80]!r}")
    name = line[:first].strip() or "untitled"
    default_blob = line[first + 1 : second].strip()
    note_blob = line[second + 1 :].strip()
    defaults = {"d": 4, "o": 5, "b": 120}
    for item in default_blob.split(","):
        item = item.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip().lower()
        if key in defaults:
            defaults[key] = int(value.strip())
    beat_s = 60.0 / max(32, min(defaults["b"], 400))
    notes: list[tuple[float, float]] = []
    for token in note_blob.split(","):
        token = token.strip().lower()
        if not token:
            continue
        m = _NOTE_RE.match(token)
        if not m:
            continue
        dur = int(m.group("dur") or defaults["d"])
        if dur not in {1, 2, 4, 8, 16, 32, 64}:
            continue
        rest = m.group("rest") or ""
        octave_s, dotted = _split_octave_dot(rest)
        if octave_s is None and rest not in {"", "."}:
            continue
        length = (4.0 / dur) * beat_s
        if dotted:
            length *= 1.5
        note = m.group("note")
        if note == "p":
            notes.append((0.0, length))
            continue
        octave = int(octave_s or defaults["o"])
        octave = max(4, min(8, octave))
        semitone = NOTE_SEMITONE.get(note)
        if semitone is None:
            raise ValueError(f"unknown note {note!r}")
        midi = 12 * (octave + 1) + semitone
        freq = 440.0 * (2.0 ** ((midi - 69) / 12.0))
        notes.append((freq, length))
    if len(notes) < 3:
        raise ValueError("RTTTL needs at least 3 notes")
    # Keep clips short so the flock can crossfade often.
    acc = 0.0
    trimmed: list[tuple[float, float]] = []
    for freq, dur in notes:
        if acc >= 14.0:
            break
        if acc + dur > 14.0:
            dur = 14.0 - acc
        trimmed.append((freq, dur))
        acc += dur
    notes = trimmed
    if acc < 0.4:
        raise ValueError("RTTTL duration must be at least 0.4s")
    return RtttlTune(
        name=name,
        bpm=defaults["b"],
        default_duration=defaults["d"],
        default_octave=defaults["o"],
        notes=tuple(notes),
    )


def render_pcm(
    tune: RtttlTune,
    *,
    sample_rate: int = 22050,
    amplitude: float = 0.04,
    wave: str = "square",
) -> bytes:
    """Render mono s16le PCM. Amplitude is a fraction of full scale (keep tiny)."""
    amp = max(0.001, min(amplitude, 0.2))
    peak = int(32767 * amp)
    fade = max(1, int(sample_rate * 0.003))
    chunks: list[int] = []
    t = 0
    for freq, dur in tune.notes:
        n = max(1, int(sample_rate * dur))
        if freq <= 0:
            chunks.extend([0] * n)
            t += n
            continue
        period = sample_rate / freq
        for i in range(n):
            phase = (t + i) / period
            if wave == "triangle":
                frac = phase % 1.0
                sample = 4.0 * abs(frac - 0.5) - 1.0
            else:
                sample = 1.0 if (phase % 1.0) < 0.5 else -1.0
            env = 1.0
            if i < fade:
                env = i / fade
            elif i > n - fade:
                env = max(0.0, (n - i) / fade)
            chunks.append(int(peak * sample * env))
        t += n
    out = bytearray()
    for s in chunks:
        if s > 32767:
            s = 32767
        elif s < -32768:
            s = -32768
        out.extend(int(s).to_bytes(2, "little", signed=True))
    return bytes(out)


def extract_rtttl_line(text: str) -> str:
    """Pull the first RTTTL line from model output."""
    for line in text.splitlines():
        line = line.strip().strip("`")
        if line.count(":") < 2:
            continue
        try:
            parse_rtttl(line)
        except ValueError:
            continue
        return line
    raise ValueError("no RTTTL line in model output")


def _split_octave_dot(rest: str) -> tuple[str | None, bool]:
    """Accept both Nokia `c6.` and the common `c.6` dotted form."""
    rest = rest.strip()
    if rest == "":
        return None, False
    if rest == ".":
        return None, True
    if rest.isdigit():
        return rest, False
    if rest.startswith(".") and rest[1:].isdigit():
        return rest[1:], True
    if rest.endswith(".") and rest[:-1].isdigit():
        return rest[:-1], True
    return None, False


def serialize_rtttl(tune: RtttlTune) -> str:
    """Rebuild a one-line RTTTL string from a parsed tune."""
    beat_s = 60.0 / max(32, min(tune.bpm, 400))
    tokens: list[str] = []
    for freq, dur in tune.notes:
        if dur <= 0:
            continue
        raw = 4.0 * beat_s / dur
        nearest = min((1, 2, 4, 8, 16, 32), key=lambda d: abs(d - raw))
        if freq <= 0:
            tokens.append(f"{nearest}p")
            continue
        midi = round(69 + 12 * math.log2(max(freq, 1.0) / 440.0))
        octave = max(4, min(8, midi // 12 - 1))
        note = _SEMI_TO_NOTE[midi % 12]
        tokens.append(f"{nearest}{note}{octave}")
    name = (tune.name or "tune").replace(":", " ").strip()[:24] or "tune"
    d = tune.default_duration if tune.default_duration in {1, 2, 4, 8, 16, 32} else 8
    o = max(4, min(8, tune.default_octave or 5))
    bpm = max(32, min(400, tune.bpm))
    return f"{name}:d={d},o={o},b={bpm}:{','.join(tokens)}"
