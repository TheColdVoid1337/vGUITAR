"""Canonical two-notes-per-string pentatonic boxes, distinct from a fret range.

Coordinates are movable templates relative to the tonic on the low E string.
One box contains twelve fretted notes: two notes per guitar string.
The five interconnected shapes are numbered from the low-E-root box.
They do not apply to altered string-interval tunings (Drop D, Open G, etc.).
"""
from __future__ import annotations

from typing import Sequence

STANDARD_MIDI = (64, 59, 55, 50, 45, 40)  # high e -> low E
BOX_NAMES = tuple(f"Box {n}" for n in range(1, 6))
BOX_SCALES = ("Минорная пентатоника", "Мажорная пентатоника")

# Each shape: high e, B, G, D, A, low E. Relative fret offsets from
# the reference tonic on the low E string (fret 5 for A in standard tuning).
MINOR_BOXES = (
    ((0, 3), (0, 3), (0, 2), (0, 2), (0, 2), (0, 3)),
    ((3, 5), (3, 5), (2, 4), (2, 5), (2, 5), (3, 5)),
    ((5, 7), (5, 8), (4, 7), (5, 7), (5, 7), (5, 7)),
    ((7, 10), (8, 10), (7, 9), (7, 9), (7, 10), (7, 10)),
    ((10, 12), (10, 12), (9, 12), (9, 12), (10, 12), (10, 12)),
)
# A major-pentatonic Box 1 starts on A (6th string, fret 5), unlike the
# *relative minor* F# pentatonic Box 1, which has another root/reference.
MAJOR_BOXES = (
    ((0, 2), (0, 2), (-1, 1), (-1, 2), (-1, 2), (0, 2)),
    ((2, 4), (2, 5), (1, 4), (2, 4), (2, 4), (2, 4)),
    ((4, 7), (5, 7), (4, 6), (4, 6), (4, 7), (4, 7)),
    ((7, 9), (7, 9), (6, 9), (6, 9), (7, 9), (7, 9)),
    ((9, 12), (9, 12), (9, 11), (9, 11), (9, 11), (9, 12)),
)

# Fix the templates rather than allowing a scale membership filter to silently
# add correct pitches located OUTSIDE the selected box.


def pentatonic_box(tuning: Sequence[int], scale_name: str, key: int,
                    box: int) -> list[tuple[int, int, int, str]]:
    """Return every note in exactly one canonical guitar box.

    Results are (string_row, fret, midi_pitch, degree) ordered low E to high e.
    All notes are on frets 0..24, and preserve the selected absolute octaves.
    """
    if scale_name not in BOX_SCALES:
        raise ValueError("Аппликатуры Box 1–5 поддерживаются для мажорной и минорной пентатоники")
    if not 0 <= key < 12 or box not in range(1, 6):
        raise ValueError("Неверная тональность или номер Box")
    if len(tuning) != 6 or any(type(m) is not int for m in tuning):
        raise ValueError("Неверный гитарный строй")
    delta = tuning[0] - STANDARD_MIDI[0]
    if any(tuning[r] - STANDARD_MIDI[r] != delta for r in range(6)):
        raise ValueError("Классические пентатонические боксы требуют одинакового интервала между струнами, как в Standard")

    root_fret = (key - tuning[5]) % 12
    pattern = (MINOR_BOXES if scale_name == BOX_SCALES[0] else MAJOR_BOXES)[box - 1]
    offsets = (0, 3, 5, 7, 10) if scale_name == BOX_SCALES[0] else (0, 2, 4, 7, 9)
    labels = ("1", "♭3", "4", "5", "♭7") if scale_name == BOX_SCALES[0] else ("1", "2", "3", "5", "6")
    degrees = {(key + o) % 12: d for o, d in zip(offsets, labels)}
    if all(0 <= root_fret + off <= 24 for pair in pattern for off in pair):
        return _assemble(tuning, pattern, root_fret, degrees)

    # Move the *whole box* by one octave, not isolated notes.
    for shift in (-12, 12, -24, 24):
        if all(0 <= root_fret + off + shift <= 24 for pair in pattern for off in pair):
            return _assemble(tuning, pattern, root_fret + shift, degrees)
    raise ValueError("Box не помещается в диапазон 0–24 ладов")


def _assemble(tuning, pattern, base, degrees):
    result = []
    for row in range(5, -1, -1):
        for offset in pattern[row]:
            fret = base + offset
            midi = tuning[row] + fret
            label = degrees.get(midi % 12)
            if label is None:
                raise ValueError(f"Ошибочная аппликатура: струна {6-row}, лад {fret}")
            result.append((row, fret, midi, label))
    return result


def next_box(current: int) -> int:
    return current % 5 + 1
