"""Fingering shapes for the five remaining scales in Note Trainer.

Seven-tone scales use seven ascending three-notes-per-string (3NPS) paths.
The minor blues scale uses five classical minor-pentatonic boxes plus the
optional b5 passing tone(s) inside each box's fret span. These are different
families from the five chord-oriented CAGED positions.
"""
from __future__ import annotations
from typing import Sequence
from vguitar_scale_shapes import BOX_NAMES, BOX_SCALES, pentatonic_box

DIATONIC_OFFSETS = {
    'Мажор': ((0, 2, 4, 5, 7, 9, 11), ('1', '2', '3', '4', '5', '6', '7')),
    'Натуральный минор': ((0, 2, 3, 5, 7, 8, 10), ('1', '2', '♭3', '4', '5', '♭6', '♭7')),
    'Дорийский': ((0, 2, 3, 5, 7, 9, 10), ('1', '2', '♭3', '4', '5', '6', '♭7')),
    'Фригийский': ((0, 1, 3, 5, 7, 8, 10), ('1', '♭2', '♭3', '4', '5', '♭6', '♭7')),
}
BLUES_SCALE = 'Блюзовая'
FINGERING_SCALES = (*BOX_SCALES, BLUES_SCALE, *DIATONIC_OFFSETS)
THREE_NPS_NAMES = tuple(f'3NPS {n}' for n in range(1, 8))


def shape_names(name: str) -> tuple[str, ...]:
    if name in DIATONIC_OFFSETS:
        return THREE_NPS_NAMES
    if name in (*BOX_SCALES, BLUES_SCALE):
        return BOX_NAMES
    raise ValueError('No fingering positions for this scale')


def shape_family(name: str) -> str:
    return '3nps' if name in DIATONIC_OFFSETS else 'blues_box' if name == BLUES_SCALE else 'pentatonic_box'


def next_shape(name: str, current: int) -> int:
    return current % len(shape_names(name)) + 1


def _validate_standard_intervals(tuning: Sequence[int]) -> None:
    if len(tuning) != 6 or any(type(n) is not int for n in tuning):
        raise ValueError('Invalid tuning')
    from vguitar_scale_shapes import STANDARD_MIDI
    delta = tuning[0] - STANDARD_MIDI[0]
    if any(tuning[r] - STANDARD_MIDI[r] != delta for r in range(6)):
        raise ValueError('Точные аппликатуры требуют стандартных интервалов между струнами; для Drop/Open используй «Участок ладов» или «Весь звукоряд»')


def scale_fingering(tuning: Sequence[int], name: str, key: int, number: int):
    """One transposable canonical fingering as (row, fret, midi, degree)."""
    if name not in FINGERING_SCALES or not isinstance(key, int) or not 0 <= key < 12:
        raise ValueError('Invalid scale or key')
    if type(number) is not int or not 1 <= number <= len(shape_names(name)):
        raise ValueError('Invalid fingering number')
    _validate_standard_intervals(tuning)
    if name in BOX_SCALES:
        return pentatonic_box(tuning, name, key, number)
    if name == BLUES_SCALE:
        base = pentatonic_box(tuning, 'Минорная пентатоника', key, number)
        low = min(f for _, f, _, _ in base)
        high = max(f for _, f, _, _ in base)
        extra = []
        for row in range(5, -1, -1):
            for fret in range(low, high + 1):
                midi = tuning[row] + fret
                if (midi - key) % 12 == 6:
                    extra.append((row, fret, midi, '♭5'))
        result = sorted(base + extra, key=lambda x: (-x[0], x[1]))
        return result

    offsets, labels = DIATONIC_OFFSETS[name]
    degree_by_pc = {(key + offset) % 12: label for offset, label in zip(offsets, labels)}
    # Position 1 starts on the sixth-string tonic, then ascend through the
    # scale degrees to create seven interconnected 3NPS patterns.
    root_fret = (key - tuning[5]) % 12
    low_fret = (root_fret + offsets[number - 1]) % 12
    last_midi = None
    result = []
    for row in range(5, -1, -1):
        frets = [f for f in range(25) if (tuning[row] + f) % 12 in degree_by_pc
                 and (last_midi is None and f >= low_fret or
                      last_midi is not None and tuning[row] + f > last_midi)]
        if last_midi is None:
            if low_fret not in frets:
                raise ValueError('Invalid starting note')
            frets = frets[frets.index(low_fret):]
        frets = frets[:3]
        if len(frets) != 3:
            raise ValueError('3NPS не помещается на грифе 0–24')
        for fret in frets:
            midi = tuning[row] + fret
            result.append((row, fret, midi, degree_by_pc[midi % 12]))
        last_midi = tuning[row] + frets[-1]
    return result
