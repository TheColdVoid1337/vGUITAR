"""Pure visual configuration for the six-string electric-guitar fretboard.

Physical millimetre/inch references influence only canvas appearance; the
note grid, fret geometry, tuning and MIDI audio are intentionally unchanged.
"""
from __future__ import annotations

import math

# Gauge numbers are thousandths of an inch, high E to low E.
# Common six-string Slinky-family combinations.
STRING_SETS = {
    "8–38": (8, 11, 14, 22, 30, 38),
    "9–42": (9, 11, 16, 24, 32, 42),
    "9–46": (9, 11, 16, 26, 36, 46),
    "10–46": (10, 13, 17, 26, 36, 46),
    "10–52": (10, 13, 17, 32, 42, 52),
    "11–48": (11, 14, 18, 28, 38, 48),
    "12–56": (12, 16, 24, 32, 44, 56),
}
STRING_MATERIALS = {
    "nickel": ("Никелированная сталь", "Nickel-plated steel", "#c0c6cb"),
    "pure_nickel": ("Чистый никель", "Pure nickel", "#b1aca0"),
    "stainless": ("Нержавеющая сталь", "Stainless steel", "#dce3e9"),
    "cobalt": ("Кобальтовый сплав", "Cobalt alloy", "#899fae"),
}
NUT_THICKNESSES_MM = (3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0)
NUT_MATERIALS = {
    "plastic": ("Пластик", "Plastic", "#d5dfe8"),
    "bone": ("Кость", "Bone", "#efe6cf"),
    "tusq": ("TUSQ", "TUSQ", "#f1eee6"),
    "graphite": ("Графит", "Graphite", "#47484c"),
    "brass": ("Латунь", "Brass", "#cba355"),
    "copper": ("Медь (редкий вариант)", "Copper (uncommon)", "#b97857"),
}
# Realistic fret crown widths, not tang widths, in millimetres (Jescar).
FRET_CROWNS_MM = (2.03, 2.28, 2.41, 2.54, 2.79, 2.99)
FRET_MATERIALS = {
    "nickel_silver": ("Нейзильбер", "Nickel silver", "#b7babd"),
    "stainless": ("Нержавеющая сталь", "Stainless steel", "#dce5ed"),
    "evo_gold": ("EVO Gold", "EVO Gold", "#d2ad61"),
}
VISUAL_DEFAULTS = {
    "string_set": "10–46",
    "string_material": "nickel",
    "nut_mm": 4.0,
    "nut_material": "plastic",
    "fret_mm": 2.54,
    "fret_material": "nickel_silver",
    "inlay_radius": 4.5,
}


def clean_visual_settings(value: object) -> dict:
    """Load older preferences safely; reject bad saved IDs and dimensions."""
    source = value if isinstance(value, dict) else {}
    result = dict(VISUAL_DEFAULTS)
    for name, choices in (
        ("string_set", STRING_SETS),
        ("string_material", STRING_MATERIALS),
        ("nut_material", NUT_MATERIALS),
        ("fret_material", FRET_MATERIALS),
    ):
        if isinstance(source.get(name), str) and source[name] in choices:
            result[name] = source[name]
    for name, allowed in (("nut_mm", NUT_THICKNESSES_MM),
                          ("fret_mm", FRET_CROWNS_MM)):
        raw = source.get(name)
        if isinstance(raw, (float, int)) and not isinstance(raw, bool) and math.isfinite(raw):
            choice = min(allowed, key=lambda v: abs(v - raw))
            if abs(choice - raw) < 0.011:
                result[name] = choice
    raw = source.get("inlay_radius")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool) and math.isfinite(raw):
        result["inlay_radius"] = max(2.5, min(7.5, round(float(raw) * 2) / 2))
    return result


def string_widths(gauge_set: str) -> tuple[float, ...]:
    """Readable screen-space six-string strokes, monotonic in real gauge."""
    gauges = STRING_SETS.get(gauge_set, STRING_SETS["10–46"])
    return tuple(round(max(1.0, min(4.8, .83 + .056 * gauge)), 2)
                 for gauge in gauges)


def nut_width_px(thickness_mm: float) -> float:
    """Visual millimetres to pixels: 3–6 mm becomes 4–8 px, no fret shift."""
    return max(4.0, min(8.0, float(thickness_mm) * (4.0 / 3.0)))


def fret_width_px(crown_mm: float) -> float:
    """Fret crown options 2.03–2.99 mm become distinct canvas widths."""
    return round(max(2.0, min(4.8, 2 + (float(crown_mm) - 2.0) * 2.8)), 2)


def material_label(materials: dict, key: str, language: str) -> str:
    labels = materials[key]
    return labels[1 if language == "en" else 0]
