"""1960s Bell 103 acoustic-coupler modem tones (handshake + 300-baud FSK)."""

from __future__ import annotations

import math
from collections.abc import Iterable

# Bell 103 (1962): originate 1070/1270, answer 2025/2225, 300 baud.
ORIGINATE_SPACE = 1070.0
ORIGINATE_MARK = 1270.0
ANSWER_SPACE = 2025.0
ANSWER_MARK = 2225.0
BAUD = 300.0


def _clamp_amp(amplitude: float) -> float:
    return max(0.0005, min(float(amplitude), 0.2))


def samples_to_pcm(samples: list[float]) -> bytes:
    return _pcm_bytes(samples)


def _pcm_bytes(samples: list[float]) -> bytes:
    out = bytearray()
    for x in samples:
        s = int(32767 * x)
        if s > 32767:
            s = 32767
        elif s < -32768:
            s = -32768
        out.extend(s.to_bytes(2, "little", signed=True))
    return bytes(out)


def _tone(
    freq: float,
    duration_s: float,
    sample_rate: int,
    amplitude: float,
    *,
    phase: float = 0.0,
) -> tuple[list[float], float]:
    n = max(1, int(sample_rate * duration_s))
    fade = max(1, int(sample_rate * 0.004))
    two_pi = 2.0 * math.pi
    step = two_pi * freq / sample_rate
    samples: list[float] = []
    for i in range(n):
        env = 1.0
        if i < fade:
            env = i / fade
        elif i > n - fade:
            env = max(0.0, (n - i) / fade)
        samples.append(math.sin(phase) * amplitude * env)
        phase += step
        if phase > two_pi:
            phase -= two_pi * math.floor(phase / two_pi)
    return samples, phase


def _silence(duration_s: float, sample_rate: int) -> list[float]:
    return [0.0] * max(1, int(sample_rate * duration_s))


def _fsk(
    bits: Iterable[int],
    mark_hz: float,
    space_hz: float,
    sample_rate: int,
    amplitude: float,
    *,
    phase: float = 0.0,
) -> tuple[list[float], float]:
    bit_n = max(1, int(sample_rate / BAUD))
    fade = max(1, int(sample_rate * 0.003))
    two_pi = 2.0 * math.pi
    bits_list = list(bits)
    total = bit_n * len(bits_list)
    samples: list[float] = []
    t = 0
    for bit in bits_list:
        freq = mark_hz if bit else space_hz
        step = two_pi * freq / sample_rate
        for _ in range(bit_n):
            env = 1.0
            if t < fade:
                env = t / fade
            elif t > total - fade:
                env = max(0.0, (total - t) / fade)
            samples.append(math.sin(phase) * amplitude * env)
            phase += step
            if phase > two_pi:
                phase -= two_pi * math.floor(phase / two_pi)
            t += 1
    return samples, phase


def _mix(a: list[float], b: list[float]) -> list[float]:
    n = max(len(a), len(b))
    out = [0.0] * n
    for i, x in enumerate(a):
        out[i] += x
    for i, x in enumerate(b):
        out[i] += x
    return out


def _pattern(n_bits: int, seed: int) -> list[int]:
    # Deterministic scramble so a looped clip does not become a steady tone.
    bits: list[int] = []
    state = seed & 0xFFFF
    for _ in range(n_bits):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        bits.append((state >> 16) & 1)
    return bits


def render_modem_layer(
    duration_s: float,
    *,
    sample_rate: int = 22050,
    amplitude: float = 0.006,
    seed: int = 103,
    handshake: bool = True,
) -> list[float]:
    """Unique Bell 103 layer of exact length. New seed => new FSK bits."""
    amp = _clamp_amp(amplitude)
    sr = sample_rate
    target = max(1, int(sr * max(0.4, duration_s)))
    chunks: list[float] = []
    if handshake:
        chunks.extend(_silence(0.08 + (seed % 7) * 0.02, sr))
        tone, _ = _tone(ORIGINATE_MARK, 0.12 + (seed % 5) * 0.03, sr, amp * 0.65)
        chunks.extend(tone)
        chunks.extend(_silence(0.06, sr))
        answer, _ = _tone(ANSWER_MARK, 0.35 + (seed % 9) * 0.04, sr, amp)
        chunks.extend(answer)
        lock_a, _ = _tone(ANSWER_MARK, 0.28, sr, amp * 0.5)
        lock_o, _ = _tone(ORIGINATE_MARK, 0.28, sr, amp * 0.45)
        chunks.extend(_mix(lock_a, lock_o))
    remain_s = max(0.5, (target - len(chunks)) / sr)
    ans_bits = _pattern(max(8, int(BAUD * remain_s * 0.7)), seed)
    orig_bits = _pattern(max(8, int(BAUD * remain_s * 0.7)), seed ^ 0xA5A5)
    ans_fsk, _ = _fsk(ans_bits, ANSWER_MARK, ANSWER_SPACE, sr, amp * 0.7)
    orig_fsk, _ = _fsk(orig_bits, ORIGINATE_MARK, ORIGINATE_SPACE, sr, amp * 0.62)
    if (seed >> 3) & 1:
        chunks.extend(ans_fsk[: int(sr * min(1.2, remain_s / 3))])
    overlap = min(len(ans_fsk), len(orig_fsk), max(1, target - len(chunks)))
    chunks.extend(_mix(ans_fsk[:overlap], orig_fsk[:overlap]))
    if len(chunks) < target:
        extra, _ = _fsk(
            _pattern(max(8, int(BAUD * (target - len(chunks)) / sr)), seed ^ 0x1111),
            ANSWER_MARK if seed & 1 else ORIGINATE_MARK,
            ANSWER_SPACE if seed & 1 else ORIGINATE_SPACE,
            sr,
            amp * 0.55,
        )
        chunks.extend(extra)
    if len(chunks) < target:
        chunks.extend([0.0] * (target - len(chunks)))
    return chunks[:target]


def render_modem(
    *,
    sample_rate: int = 22050,
    amplitude: float = 0.006,
    seed: int = 103,
) -> bytes:
    """One-shot Bell 103 clip (tests / fallback). Prefer render_modem_layer."""
    samples = render_modem_layer(
        8.0, sample_rate=sample_rate, amplitude=amplitude, seed=seed, handshake=True
    )
    return _pcm_bytes(samples)
