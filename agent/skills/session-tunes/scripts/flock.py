"""Electric Sheep analog: evolving audio genomes, never the same clip twice."""

from __future__ import annotations

import hashlib
import json
import math
import random
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from config import FLOCK_DIR
from modem import render_modem_layer, samples_to_pcm
from rtttl import RtttlTune, parse_rtttl, render_pcm, serialize_rtttl

SCALES: dict[str, tuple[int, ...]] = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "pentatonic": (0, 2, 4, 7, 9),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "minor_pent": (0, 3, 5, 7, 10),
}
WAVES = ("square", "triangle")
RECENT_MAX = 48


@dataclass
class Sheep:
    sheep_id: str
    generation: int
    parents: list[str]
    kind: str
    root_midi: int
    scale: str
    bpm: int
    wave: str
    degrees: list[int]
    durs: list[int]
    modem_mix: float
    modem_seed: int
    handshake: bool
    rtttl_line: str = ""
    born: float = field(default_factory=time.time)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Sheep:
        return cls(
            sheep_id=str(data["sheep_id"]),
            generation=int(data.get("generation") or 0),
            parents=list(data.get("parents") or []),
            kind=str(data.get("kind") or "busy"),
            root_midi=int(data.get("root_midi") or 60),
            scale=str(data.get("scale") or "pentatonic"),
            bpm=int(data.get("bpm") or 140),
            wave=str(data.get("wave") or "square"),
            degrees=[int(x) for x in (data.get("degrees") or [0, 2, 4, 2])],
            durs=[int(x) for x in (data.get("durs") or [8, 8, 8, 8])],
            modem_mix=float(data.get("modem_mix") or 0.25),
            modem_seed=int(data.get("modem_seed") or 1),
            handshake=bool(data.get("handshake")),
            rtttl_line=str(data.get("rtttl_line") or ""),
            born=float(data.get("born") or time.time()),
        )


def _assign_id(sheep: Sheep) -> Sheep:
    payload = {
        "k": sheep.kind,
        "r": sheep.root_midi,
        "s": sheep.scale,
        "b": sheep.bpm,
        "w": sheep.wave,
        "d": sheep.degrees,
        "u": sheep.durs,
        "m": round(sheep.modem_mix, 3),
        "seed": sheep.modem_seed,
        "h": sheep.handshake,
        "t": sheep.rtttl_line,
        "g": sheep.generation,
        "p": sheep.parents,
    }
    sheep.sheep_id = hashlib.sha1(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()[:12]
    return sheep


def _midi_freq(midi: int) -> float:
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def _mix_range(thinking_sound: str, kind: str) -> tuple[float, float]:
    if kind != "busy":
        return (0.0, 0.08)
    style = (thinking_sound or "peppy").lower()
    if style == "modem":
        return (0.08, 0.16)
    if style == "peppy":
        return (0.0, 0.12)
    return (0.0, 0.14)


def _modem_roll(rng: random.Random, cfg: dict[str, Any]) -> tuple[float, bool]:
    chance = float(cfg.get("modem_chance") or 0.15)
    if rng.random() > chance:
        return 0.0, False
    return rng.uniform(0.07, 0.13), True


def drift_rtttl_line(line: str, rng: random.Random) -> str:
    """Keep the song recognizable, then nudge pitch, rhythm, and BPM."""
    try:
        tune = parse_rtttl(line)
    except ValueError:
        return line
    bpm = max(80, min(240, tune.bpm + rng.randint(-18, 18)))
    notes = list(tune.notes)
    if not notes:
        return line
    flips = max(2, len(notes) // 5)
    for _ in range(flips):
        i = rng.randrange(len(notes))
        freq, dur = notes[i]
        roll = rng.random()
        if roll < 0.18:
            notes[i] = (0.0, dur)
        elif roll < 0.55 and freq > 0:
            steps = rng.choice((-3, -2, -1, 1, 2, 3, 5, -5))
            notes[i] = (freq * (2 ** (steps / 12.0)), dur)
        else:
            notes[i] = (freq, max(0.03, dur * rng.choice((0.5, 0.5, 1.5, 2.0))))
    drifted = RtttlTune(
        name=tune.name,
        bpm=bpm,
        default_duration=tune.default_duration,
        default_octave=tune.default_octave,
        notes=tuple(notes),
    )
    out = serialize_rtttl(drifted)
    try:
        parse_rtttl(out)
    except ValueError:
        return line
    return out


class Flock:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or FLOCK_DIR
        self.path = self.root / "flock.json"
        self._lock = threading.Lock()
        self.sheep: dict[str, Sheep] = {}
        self.recent: list[str] = []
        self.recent_names: list[str] = []
        self._rng = random.Random()
        self.root.mkdir(parents=True, exist_ok=True)
        self._load()
        if len(self.sheep) < 6:
            self._seed()
            self._save()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for item in data.get("sheep") or []:
            if isinstance(item, dict):
                sheep = Sheep.from_json(item)
                self.sheep[sheep.sheep_id] = sheep
        self.recent = [str(x) for x in (data.get("recent") or [])][-RECENT_MAX:]
        self.recent_names = [str(x) for x in (data.get("recent_names") or [])][
            -RECENT_MAX:
        ]

    def _save(self) -> None:
        blob = {
            "sheep": [s.to_json() for s in self.sheep.values()],
            "recent": self.recent[-RECENT_MAX:],
            "recent_names": self.recent_names[-RECENT_MAX:],
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(blob, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def save(self) -> None:
        with self._lock:
            self._save()

    def stats(self) -> dict[str, Any]:
        gens = [s.generation for s in self.sheep.values()] or [0]
        return {
            "count": len(self.sheep),
            "generation_max": max(gens),
            "recent": list(self.recent[-6:]),
            "library": self._library_count(),
        }

    def _library_count(self) -> int:
        from config import busy_library_files

        return len(busy_library_files())

    def _unused_library_files(self) -> list[Path]:
        from config import busy_library_files

        seen = set(self.recent_names)
        return [p for p in busy_library_files() if p.stem.lower() not in seen]

    def _add(self, sheep: Sheep, flock_max: int = 250) -> Sheep:
        _assign_id(sheep)
        self.sheep[sheep.sheep_id] = sheep
        extra = len(self.sheep) - flock_max
        if extra > 0:
            oldest = sorted(self.sheep.values(), key=lambda s: (s.generation, s.born))
            for victim in oldest[:extra]:
                if victim.sheep_id not in self.recent:
                    self.sheep.pop(victim.sheep_id, None)
        return sheep

    def _seed(self) -> None:
        from config import SEED_LIB, USER_LIB, busy_library_files

        for path in sorted(SEED_LIB.glob("*.rtttl")):
            name = path.stem.lower()
            kind = "busy"
            if name.startswith("alert"):
                kind = "attention"
            elif name.startswith("error"):
                kind = "error"
            try:
                sheep = self._from_rtttl(
                    path.read_text(encoding="utf-8", errors="ignore"), kind=kind
                )
            except ValueError:
                continue
            self._add(sheep)
        pool = [p for p in busy_library_files() if p.parent == USER_LIB]
        self._rng.shuffle(pool)
        for path in pool[:32]:
            try:
                self._add(
                    self._from_rtttl(
                        path.read_text(encoding="utf-8", errors="ignore"), kind="busy"
                    )
                )
            except ValueError:
                continue
        for _ in range(12):
            self._add(self._random_sheep("busy", thinking_sound="peppy"))
        self._save()

    def _from_rtttl(self, text: str, *, kind: str = "busy") -> Sheep:
        tune = parse_rtttl(text)
        line = text.strip().splitlines()
        rtttl_line = next(
            (
                ln.strip()
                for ln in line
                if ln.strip() and not ln.strip().startswith("#")
            ),
            "",
        )
        degrees: list[int] = []
        durs: list[int] = []
        beat_s = 60.0 / max(32, tune.bpm)
        for freq, dur in tune.notes:
            if dur <= 0:
                continue
            raw = 4.0 * beat_s / dur
            nearest = min((1, 2, 4, 8, 16, 32), key=lambda d: abs(d - raw))
            durs.append(nearest)
            if freq <= 0:
                degrees.append(-1)
                continue
            midi = round(69 + 12 * math.log2(freq / 440.0))
            degrees.append(max(-1, midi - 60))
        return Sheep(
            sheep_id="",
            generation=0,
            parents=[],
            kind=kind,
            root_midi=60,
            scale="pentatonic",
            bpm=tune.bpm,
            wave="triangle",
            degrees=degrees[:32] or [0, 2, 4, 2],
            durs=durs[:32] or [8, 8, 8, 8],
            modem_mix=0.0,
            modem_seed=self._rng.randint(1, 2**30),
            handshake=False,
            rtttl_line=rtttl_line,
        )

    def ingest_rtttl(
        self, text: str, *, kind: str = "busy", save: bool = True
    ) -> Sheep:
        sheep = self._from_rtttl(text, kind=kind)
        with self._lock:
            sheep = self._add(sheep)
            if save:
                self._save()
        return sheep

    def _random_sheep(self, kind: str, thinking_sound: str = "both") -> Sheep:
        rng = self._rng
        lo, hi = _mix_range(thinking_sound, kind)
        n = rng.randint(18, 32) if kind == "busy" else rng.randint(6, 12)
        if kind == "error":
            scale = rng.choice(("dorian", "minor_pent"))
            root = rng.randint(62, 74)
            bpm = rng.randint(152, 196)
            degrees = list(range(n - 1, -1, -1))
            durs = [rng.choice((8, 16, 16)) for _ in range(n)]
            handshake = False
        elif kind == "attention":
            scale = "pentatonic"
            root = rng.randint(72, 84)
            bpm = rng.randint(188, 236)
            degrees = [rng.choice((0, 1, 2, 4, 5, -1)) for _ in range(n)]
            durs = [rng.choice((16, 16, 32)) for _ in range(n)]
            handshake = False
        else:
            scale = rng.choice(tuple(SCALES))
            root = rng.randint(55, 69)
            bpm = rng.randint(118, 176)
            degrees = [rng.choice(range(-1, 12)) for _ in range(n)]
            durs = [rng.choice((4, 8, 8, 8, 16)) for _ in range(n)]
            handshake = False
        return _assign_id(
            Sheep(
                sheep_id="",
                generation=0,
                parents=[],
                kind=kind,
                root_midi=root,
                scale=scale,
                bpm=bpm,
                wave="triangle" if kind == "busy" else rng.choice(WAVES),
                degrees=degrees,
                durs=durs,
                modem_mix=rng.uniform(lo, hi) if kind != "busy" else 0.0,
                modem_seed=rng.randint(1, 2**30),
                handshake=handshake,
            )
        )

    def _mutate(
        self, parent: Sheep, *, kind: str | None = None, thinking_sound: str = "both"
    ) -> Sheep:
        rng = self._rng
        kind = kind or parent.kind
        lo, hi = _mix_range(thinking_sound, kind)
        degrees = list(parent.degrees)
        durs = list(parent.durs)
        n = min(len(degrees), len(durs))
        degrees, durs = degrees[:n], durs[:n]
        flips = max(3, n // 4)
        for _ in range(flips):
            i = rng.randrange(n)
            if kind == "error":
                degrees[i] = max(-1, degrees[i] + rng.choice((-2, -1, 0, 1)))
                durs[i] = rng.choice((8, 16, 16))
            elif kind == "attention":
                degrees[i] = rng.choice((0, 1, 2, 4, 5, 7, -1))
                durs[i] = rng.choice((16, 16, 32))
            else:
                degrees[i] = rng.choice(range(-1, 14))
                durs[i] = rng.choice((4, 8, 8, 16))
        mix = min(hi, max(lo, parent.modem_mix + rng.uniform(-0.12, 0.12)))
        bpm = parent.bpm + rng.randint(-18, 18)
        bpm = max(96, min(240, bpm))
        root = parent.root_midi + rng.choice((-2, 0, 0, 2, 5, -5))
        if kind == "attention":
            root = max(70, min(88, root))
            bpm = max(180, bpm)
        elif kind == "error":
            root = max(57, min(76, root))
        else:
            root = max(50, min(76, root))
        scale = parent.scale
        if rng.random() < 0.25:
            scale = rng.choice(tuple(SCALES))
        return _assign_id(
            Sheep(
                sheep_id="",
                generation=parent.generation + 1,
                parents=[parent.sheep_id],
                kind=kind,
                root_midi=root,
                scale=scale,
                bpm=bpm,
                wave="triangle"
                if kind == "busy"
                else (rng.choice(WAVES) if rng.random() < 0.2 else parent.wave),
                degrees=degrees,
                durs=durs,
                modem_mix=mix if kind != "busy" else 0.0,
                modem_seed=rng.randint(1, 2**30),
                handshake=False,
                rtttl_line=(
                    drift_rtttl_line(parent.rtttl_line, rng)
                    if kind == "busy" and parent.rtttl_line
                    else ""
                ),
            )
        )

    def _crossover(self, a: Sheep, b: Sheep, thinking_sound: str) -> Sheep:
        rng = self._rng
        cut = max(2, min(len(a.degrees), len(b.degrees)) // 2)
        degrees = a.degrees[:cut] + b.degrees[cut:]
        durs = b.durs[:cut] + a.durs[cut:]
        n = min(len(degrees), len(durs))
        parent = a if rng.random() < 0.5 else b
        child = self._mutate(parent, kind="busy", thinking_sound=thinking_sound)
        child.degrees = degrees[:n]
        child.durs = durs[:n]
        child.parents = [a.sheep_id, b.sheep_id]
        child.generation = max(a.generation, b.generation) + 1
        child.scale = a.scale if rng.random() < 0.5 else b.scale
        child.root_midi = a.root_midi if rng.random() < 0.5 else b.root_midi
        return _assign_id(child)

    def _pick_parent(self) -> Sheep:
        pool = [s for s in self.sheep.values() if s.kind == "busy"] or list(
            self.sheep.values()
        )
        fresh = [s for s in pool if s.sheep_id not in self.recent]
        choices = fresh or pool
        return self._rng.choice(choices)

    def breed_busy(self, cfg: dict[str, Any], *, save: bool = True) -> Sheep:
        thinking = str(cfg.get("thinking_sound") or "peppy")
        flock_max = int(cfg.get("flock_max") or 250)
        with self._lock:
            unused_files = self._unused_library_files()
            unused_sheep = [
                s
                for s in self.sheep.values()
                if s.kind == "busy" and s.rtttl_line and s.sheep_id not in self.recent
            ]
            pick = self._rng.random()
            used_name = ""
            sheep: Sheep | None = None
            if unused_files and pick < 0.62:
                path = self._rng.choice(unused_files)
                try:
                    sheep = self._from_rtttl(
                        path.read_text(encoding="utf-8", errors="ignore"), kind="busy"
                    )
                except ValueError:
                    sheep = None
                else:
                    used_name = path.stem.lower()
                    if self._rng.random() < 0.45:
                        sheep.rtttl_line = drift_rtttl_line(sheep.rtttl_line, self._rng)
                        sheep.generation = 1
                    mix, handshake = _modem_roll(self._rng, cfg)
                    sheep.modem_mix = mix
                    sheep.handshake = handshake
                    sheep.modem_seed = self._rng.randint(1, 2**30)
                    _assign_id(sheep)
            if sheep is None and unused_sheep and pick < 0.78:
                chosen = self._rng.choice(unused_sheep)
                sheep = Sheep.from_json(chosen.to_json())
                if sheep.rtttl_line and self._rng.random() < 0.45:
                    sheep.rtttl_line = drift_rtttl_line(sheep.rtttl_line, self._rng)
                    sheep.generation = chosen.generation + 1
                mix, handshake = _modem_roll(self._rng, cfg)
                sheep.modem_mix = mix
                sheep.handshake = handshake
                sheep.modem_seed = self._rng.randint(1, 2**30)
                sheep.parents = [chosen.sheep_id]
                _assign_id(sheep)
            if sheep is None and len(self.sheep) < 2:
                sheep = self._random_sheep("busy", thinking)
            if sheep is None:
                a = self._pick_parent()
                b = self._pick_parent()
                if a.sheep_id == b.sheep_id or self._rng.random() < 0.55:
                    sheep = self._mutate(a, kind="busy", thinking_sound=thinking)
                else:
                    sheep = self._crossover(a, b, thinking)
                mix, handshake = _modem_roll(self._rng, cfg)
                sheep.modem_mix = mix
                sheep.handshake = handshake
            if sheep is None:
                sheep = self._random_sheep("busy", thinking)
            while sheep.sheep_id in self.recent:
                sheep.modem_seed = self._rng.randint(1, 2**30)
                _assign_id(sheep)
            self._add(sheep, flock_max=flock_max)
            self.recent.append(sheep.sheep_id)
            self.recent = self.recent[-RECENT_MAX:]
            if used_name:
                self.recent_names.append(used_name)
                self.recent_names = self.recent_names[-RECENT_MAX:]
            if save:
                self._save()
            return sheep

    def breed_alert(self, kind: str, cfg: dict[str, Any]) -> Sheep:
        thinking = str(cfg.get("thinking_sound") or "both")
        with self._lock:
            parents = [s for s in self.sheep.values() if s.kind == kind] or list(
                self.sheep.values()
            )
            if parents and self._rng.random() < 0.7:
                sheep = self._mutate(
                    self._rng.choice(parents), kind=kind, thinking_sound=thinking
                )
            else:
                sheep = self._random_sheep(kind, thinking)
            sheep.modem_seed = self._rng.randint(1, 2**30)
            _assign_id(sheep)
            self._add(sheep, flock_max=int(cfg.get("flock_max") or 250))
            self._save()
            return sheep

    def render(
        self,
        sheep: Sheep,
        *,
        amplitude: float,
        sample_rate: int,
        modem_amplitude: float = 0.0051,
        wave: str | None = None,
    ) -> bytes:
        use_wave = wave or sheep.wave or "triangle"
        if sheep.rtttl_line:
            try:
                tune = parse_rtttl(sheep.rtttl_line)
                melody = render_pcm(
                    tune,
                    sample_rate=sample_rate,
                    amplitude=amplitude,
                    wave=use_wave,
                )
            except ValueError:
                melody = self._render_degrees(sheep, amplitude, sample_rate)
        else:
            melody = self._render_degrees(sheep, amplitude, sample_rate)
        if sheep.modem_mix <= 0.04:
            return melody
        n_samples = len(melody) // 2
        duration_s = n_samples / float(sample_rate)
        layer = render_modem_layer(
            duration_s,
            sample_rate=sample_rate,
            amplitude=modem_amplitude,
            seed=sheep.modem_seed,
            handshake=sheep.handshake and sheep.kind == "busy",
        )
        return _mix_pcm(melody, samples_to_pcm(layer))

    def _render_degrees(
        self, sheep: Sheep, amplitude: float, sample_rate: int
    ) -> bytes:
        scale = SCALES.get(sheep.scale, SCALES["pentatonic"])
        beat_s = 60.0 / max(32, min(sheep.bpm, 280))
        notes: list[tuple[float, float]] = []
        for deg, dur in zip(sheep.degrees, sheep.durs, strict=False):
            token = dur if dur in {1, 2, 4, 8, 16, 32, 64} else 8
            length = (4.0 / token) * beat_s
            if deg < 0:
                notes.append((0.0, length))
                continue
            octave, idx = divmod(deg, len(scale))
            midi = sheep.root_midi + scale[idx] + 12 * octave
            midi = max(40, min(100, midi))
            notes.append((_midi_freq(midi), length))
        if len(notes) < 3:
            notes = [(440.0, 0.2), (660.0, 0.2), (550.0, 0.2)]
        total = sum(d for _f, d in notes)
        if total < 0.5:
            notes.append((0.0, 0.5 - total))
        if sheep.kind == "busy" and total > 14.0:
            acc = 0.0
            trimmed: list[tuple[float, float]] = []
            for freq, dur in notes:
                if acc >= 12.0:
                    break
                trimmed.append((freq, dur))
                acc += dur
            notes = trimmed
        if sheep.kind in {"attention", "error"} and total > 3.2:
            acc = 0.0
            trimmed = []
            for freq, dur in notes:
                if acc >= 2.8:
                    break
                trimmed.append((freq, dur))
                acc += dur
            notes = trimmed
        tune = RtttlTune(
            name=sheep.sheep_id,
            bpm=sheep.bpm,
            default_duration=8,
            default_octave=5,
            notes=tuple(notes),
        )
        return render_pcm(
            tune, sample_rate=sample_rate, amplitude=amplitude, wave=sheep.wave
        )


def _mix_pcm(a: bytes, b: bytes) -> bytes:
    import array

    sa = array.array("h")
    sb = array.array("h")
    sa.frombytes(a)
    sb.frombytes(b)
    n = min(len(sa), len(sb))
    out = array.array("h")
    for i in range(n):
        v = sa[i] + sb[i]
        if v > 32767:
            v = 32767
        elif v < -32768:
            v = -32768
        out.append(v)
    if len(sa) > n:
        out.extend(sa[n:])
    return out.tobytes()


_FLOCK: Flock | None = None
_FLOCK_LOCK = threading.Lock()


def get_flock() -> Flock:
    global _FLOCK
    with _FLOCK_LOCK:
        if _FLOCK is None:
            _FLOCK = Flock()
        return _FLOCK
