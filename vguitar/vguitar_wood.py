"""Deterministic low-contrast wood grain, drawn below strings and frets."""
from __future__ import annotations

import math
import random


def _blend(foreground: str, background: str, opacity: float) -> str:
    fg = tuple(int(foreground[i:i+2], 16) for i in (1, 3, 5))
    bg = tuple(int(background[i:i+2], 16) for i in (1, 3, 5))
    mixed = [round(opacity * f + (1 - opacity) * b) for f, b in zip(fg, bg)]
    return "#" + "".join(f"{n:02x}" for n in mixed)


def draw_wood_grain(canvas, theme: str, width: float, top: float, bottom: float,
                    base: str, grain: str) -> int:
    """Add a separately tagged texture layer; virtual original stays flat."""
    if theme == "default" or bottom <= top or width <= 0 or not grain:
        return 0
    rng = random.Random({"ebony": 201, "maple": 307, "rosewood": 419}.get(theme, 23))
    span = bottom - top
    count = max(8, int(span / 7.0))
    drawn = 0
    for index in range(count):
        y = top + span * (index + .5) / count + rng.uniform(-2, 2)
        phase = rng.uniform(0, 2 * math.pi)
        amplitude = rng.uniform(.7, 1.6 if theme == "maple" else 2.6)
        points = []
        segments = max(2, int(width / 25))
        for step in range(segments + 1):
            x = width * step / segments
            curve = math.sin(x / 95.0 + phase) * amplitude
            curve += math.sin(x / 28.0 + phase * 1.7) * amplitude * .22
            points.extend((x, max(top + 1, min(bottom - 1, y + curve))))
        blend = .16 if theme == "maple" else .22 if theme == "rosewood" else .14
        color = _blend(grain, base, blend + rng.uniform(-.04, .04))
        canvas.create_line(*points, fill=color, width=1 if index % 5 else 2,
                           smooth=True, tags=("wood_texture",))
        drawn += 1
    return drawn
