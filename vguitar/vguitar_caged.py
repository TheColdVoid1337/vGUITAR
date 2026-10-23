"""Major-triad CAGED movable forms for vGUITAR.

Fingering is stored in string order 1 (thin) to 6 (thick).
None means a muted string; this is a chord-tone map, not a barre-fingering guide.
"""
from __future__ import annotations

STANDARD_MIDI = (64, 59, 55, 50, 45, 40)
CAGED_ORDER = ("C", "A", "G", "E", "D")
BASE_FORM_ROOTS = {"C": 0, "A": 9, "G": 7, "E": 4, "D": 2}
CAGED_OPEN_FORMS = {
    "C": (0, 1, 0, 2, 3, None),       # x32010
    "A": (0, 2, 2, 2, 0, None),       # x02220
    "G": (3, 0, 0, 0, 2, 3),          # 320003
    "E": (0, 0, 1, 2, 2, 0),          # 022100
    "D": (2, 3, 2, 0, None, None),    # xx0232
}
INTERVALS = {0: "1", 4: "3", 7: "5"}
INTERVAL_DESCRIPTIONS = {"1": "Корень", "3": "Большая терция", "5": "Квинта"}


def caged_shift(tuning: tuple[int, ...], key: int, form: str) -> int:
    """Capo-equivalent shift for a major chord; only uniform standard tunings."""
    if form not in CAGED_OPEN_FORMS or not 0 <= key <= 11:
        raise ValueError("Unknown CAGED major form or key")
    if len(tuning) != 6 or any(type(x) is not int for x in tuning):
        raise ValueError("Invalid guitar tuning")
    transposition = tuning[0] - STANDARD_MIDI[0]
    if any(tuning[i] - STANDARD_MIDI[i] != transposition for i in range(6)):
        raise ValueError("CAGED requires standard string intervals")
    return (key - BASE_FORM_ROOTS[form] - transposition) % 12


def caged_positions(tuning: tuple[int, ...], key: int, form: str) -> list[tuple[int, int, int, str]]:
    """All sounding chord tones as (string row, fret, MIDI, degree)."""
    shift = caged_shift(tuning, key, form)
    result = []
    for row, original_fret in enumerate(CAGED_OPEN_FORMS[form]):
        if original_fret is None:
            continue
        fret = original_fret + shift
        if fret > 24:
            raise ValueError("CAGED form is outside the fretboard")
        midi = tuning[row] + fret
        degree = INTERVALS.get((midi - key) % 12)
        if degree is None:
            raise ValueError("Form does not match selected major chord")
        result.append((row, fret, midi, degree))
    result.sort(key=lambda p: (int(p[3]), -p[0]))
    if not any(p[3] == "1" for p in result):
        raise ValueError("CAGED form does not contain a root")
    return result


def next_caged_form(current: str | None = None) -> str:
    """Cycle through the five shapes in C-A-G-E-D order."""
    if current not in CAGED_ORDER:
        return CAGED_ORDER[0]
    return CAGED_ORDER[(CAGED_ORDER.index(current) + 1) % len(CAGED_ORDER)]
