"""70s computer-room analog beeps (TechMoan 38:36 / Hollywood library).

Not Bell 103. The outro sting is the same analog-synth computer SFX used in
1970s–80s TV/film computer rooms: a longer boop, then repeating doots.
Measured on MCivbXqfqfs 38:36 and the matching library clip: 1650 → 1890 →
2025 Hz holds, then gated ~1495 / ~2740 Hz pulses.
"""

from __future__ import annotations

import math
import random
import struct

BOOP_HZ = (1650.0, 1890.0, 2025.0)
DOOT_LOW = 1495.0
DOOT_HIGH = 2740.0
HARMONIC = 0.35


def samples_to_pcm(samples: list[float]) -> bytes:
    return b"".join(
        struct.pack("<h", max(-32767, min(32767, int(x * 32767)))) for x in samples
    )


def _pcm_bytes(samples: list[float]) -> bytes:
    return samples_to_pcm(samples)


def _osc(phase: float, harmonic: float = HARMONIC) -> float:
    return (math.sin(phase) + harmonic * math.sin(2.0 * phase)) / (1.0 + harmonic)


def _silence(duration_s: float, sample_rate: int) -> list[float]:
    return [0.0] * max(1, int(sample_rate * duration_s))


def _beep(
    freq: float,
    duration_s: float,
    sample_rate: int,
    amplitude: float,
    rng: random.Random,
    *,
    fade_in_s: float = 0.006,
    fade_out_s: float = 0.018,
    vibrato_hz: float = 0.0,
    trem_hz: float = 0.0,
    drop_hz: float = 0.0,
) -> list[float]:
    """One analog beep: harmonic-rich sine, optional vibrato/tremolo/pitch drop."""
    n = max(1, int(sample_rate * duration_s))
    fade_in = max(1, int(sample_rate * fade_in_s))
    fade_out = max(1, int(sample_rate * fade_out_s))
    two_pi = 2.0 * math.pi
    f0 = freq + rng.uniform(-10.0, 10.0)
    phase = rng.uniform(0.0, two_pi)
    samples: list[float] = []
    for i in range(n):
        t = i / sample_rate
        env = 1.0
        if i < fade_in:
            env = i / fade_in
        elif i > n - fade_out:
            env = max(0.0, (n - i) / fade_out)
        if trem_hz > 0.0:
            env *= 0.72 + 0.28 * math.sin(two_pi * trem_hz * t)
        inst = f0 + drop_hz * (t / max(duration_s, 1e-6))
        if vibrato_hz > 0.0:
            inst += 7.0 * math.sin(two_pi * vibrato_hz * t)
        step = two_pi * inst / sample_rate
        samples.append(_osc(phase) * amplitude * env)
        phase += step
        if phase > two_pi:
            phase -= two_pi * math.floor(phase / two_pi)
    return samples


def _boop_phrase(sample_rate: int, amplitude: float, rng: random.Random) -> list[float]:
    """Rising 1650 → 1890 → 2025 Hz holds from the TechMoan sting."""
    chunks: list[float] = []
    for i, hz in enumerate(BOOP_HZ):
        dur = rng.uniform(0.22, 0.38) if i == 0 else rng.uniform(0.18, 0.32)
        amp = amplitude * (0.92 if i == 0 else 0.82)
        chunks.extend(
            _beep(
                hz,
                dur,
                sample_rate,
                amp,
                rng,
                fade_in_s=0.010,
                fade_out_s=0.022,
                vibrato_hz=rng.uniform(4.5, 6.5),
                drop_hz=rng.uniform(-18.0, -4.0),
            )
        )
        chunks.extend(_silence(rng.uniform(0.04, 0.09), sample_rate))
    return chunks


def _doot_train(
    duration_s: float,
    sample_rate: int,
    amplitude: float,
    rng: random.Random,
) -> list[float]:
    """Boop-doot-doot… 1495 / 2740 Hz gated pulses (~8 Hz)."""
    target = max(1, int(sample_rate * duration_s))
    chunks: list[float] = []
    low_first = rng.random() < 0.55
    n = 0
    trem = rng.uniform(6.5, 8.5)
    while len(chunks) < target:
        high = (n % 2 == 0) ^ low_first
        hz = DOOT_HIGH if high else DOOT_LOW
        on_s = rng.uniform(0.065, 0.095)
        gap_s = rng.uniform(0.035, 0.070)
        amp = amplitude * (0.88 if high else 0.78)
        chunks.extend(
            _beep(
                hz,
                on_s,
                sample_rate,
                amp,
                rng,
                fade_in_s=0.004,
                fade_out_s=0.012,
                trem_hz=trem,
                drop_hz=rng.uniform(-12.0, 0.0),
            )
        )
        chunks.extend(_silence(gap_s, sample_rate))
        n += 1
    return chunks[:target]


def _sweep(
    duration_s: float,
    sample_rate: int,
    amplitude: float,
    rng: random.Random,
) -> list[float]:
    """Short analog whoop, Hollywood computer-room seasoning."""
    n = max(1, int(sample_rate * duration_s))
    f0 = rng.uniform(700.0, 1100.0)
    f1 = rng.uniform(1800.0, 2600.0)
    if rng.random() < 0.45:
        f0, f1 = f1, f0
    two_pi = 2.0 * math.pi
    phase = 0.0
    fade = max(1, int(sample_rate * 0.02))
    samples: list[float] = []
    for i in range(n):
        t = i / max(n - 1, 1)
        env = 1.0
        if i < fade:
            env = i / fade
        elif i > n - fade:
            env = max(0.0, (n - i) / fade)
        freq = f0 + (f1 - f0) * t
        samples.append(_osc(phase, 0.22) * amplitude * 0.55 * env)
        phase += two_pi * freq / sample_rate
        if phase > two_pi:
            phase -= two_pi * math.floor(phase / two_pi)
    return samples


def render_modem_layer(
    duration_s: float,
    *,
    sample_rate: int = 22050,
    amplitude: float = 0.0051,
    seed: int = 103,
    handshake: bool = True,
) -> list[float]:
    """Analog computer-room layer of exact length. New seed => new rhythm."""
    sr = sample_rate
    amp = max(0.0005, min(amplitude, 0.08))
    target = max(int(sr * 2.0), int(sr * duration_s))
    rng = random.Random(seed)
    chunks: list[float] = []

    if handshake:
        chunks.extend(_boop_phrase(sr, amp, rng))

    while len(chunks) < target:
        remain_s = (target - len(chunks)) / sr
        if remain_s < 0.10:
            chunks.extend(_silence(remain_s, sr))
            break
        pick = rng.random()
        if pick < 0.12 and remain_s > 0.35:
            chunks.extend(_sweep(min(remain_s, rng.uniform(0.28, 0.55)), sr, amp, rng))
        elif pick < 0.22 and remain_s > 1.1:
            chunks.extend(_boop_phrase(sr, amp * 0.9, rng))
        else:
            span = min(remain_s, rng.uniform(1.6, 3.4))
            chunks.extend(_doot_train(span, sr, amp, rng))

    if len(chunks) < target:
        chunks.extend([0.0] * (target - len(chunks)))
    return chunks[:target]


def render_modem(
    *,
    sample_rate: int = 22050,
    amplitude: float = 0.0051,
    seed: int = 103,
) -> bytes:
    """One-shot computer-room clip (tests). Prefer render_modem_layer."""
    samples = render_modem_layer(
        7.5, sample_rate=sample_rate, amplitude=amplitude, seed=seed, handshake=True
    )
    return _pcm_bytes(samples)
