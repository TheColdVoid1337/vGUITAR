"""Seeded, non-repeating-looking wood grain, behind strings, markers and frets.

Randomness is generated from a saved 32-bit seed, so resizing or switching
modes never shuffles the user's chosen grain. Reroll changes the seed only.
"""
from __future__ import annotations

import math
import random


def _blend(foreground: str, background: str, opacity: float) -> str:
    fg = tuple(int(foreground[i:i+2], 16) for i in (1, 3, 5))
    bg = tuple(int(background[i:i+2], 16) for i in (1, 3, 5))
    mixed = [round(opacity * f + (1 - opacity) * b) for f, b in zip(fg, bg)]
    return "#" + "".join(f"{n:02x}" for n in mixed)


def draw_wood_grain(canvas, theme: str, width: float, top: float, bottom: float,
                    base: str, grain: str, *, seed: int = 0) -> int:
    """Draw individually jittered grain strands as a separate Canvas layer.

    Reproducible for (theme, seed, size); visually independent bands and knots
    replace the former uniformly periodic full-width sine lines.
    """
    if theme == "default" or bottom <= top or width <= 0 or not grain:
        return 0
    theme_seed = {"ebony": 201, "maple": 307, "rosewood": 419}.get(theme, 23)
    rng = random.Random((int(seed) & 0xffffffff) ^ (theme_seed * 982451653))
    span = bottom - top
    width = float(width)
    drawn = 0
    density = {"maple": .61, "rosewood": 1.1, "ebony": .75}.get(theme, 1.0)
    strands = max(12, min(270, int((span / 2.3 + width / 22.0) * density)))
    for index in range(strands):
        # Irregular start positions and lengths, rather than parallel bands.
        y0 = rng.uniform(top + 2, bottom - 2)
        x0 = rng.uniform(0, width)
        length = min(width - x0, rng.uniform(18, max(25, min(240, width * .35))))
        if length < 3:
            continue
        wave = rng.uniform(.1, 2.3) if theme == "maple" else rng.uniform(.3, 3.9)
        slope = rng.uniform(-.014, .014)
        phase = rng.uniform(0, math.tau)
        frequency = rng.uniform(24.0, 140.0)
        steps = max(2, min(18, int(length / 15)))
        points = []
        for step in range(steps + 1):
            x = x0 + length * step / steps
            d = x - x0
            y = y0 + slope * d + math.sin(d / frequency + phase) * wave
            # Tiny independent kinks prevent overly regular, sine-shaped veins.
            y += rng.uniform(-.32, .32)
            points.extend((min(width, max(0, x)), max(top + 1, min(bottom - 1, y))))
        opacity = (.09 if theme == "maple" else .13 if theme == "ebony" else .16)
        opacity += rng.uniform(-.04, .09)
        color = _blend(grain, base, min(.28, max(.045, opacity)))
        canvas.create_line(*points, fill=color,
                           width=2 if index % 17 == 0 else 1,
                           smooth=True, tags=("wood_texture",))
        drawn += 1

    # Occasional subtle oval-shaped waviness, built from curved line fragments.
    # Still only primitive canvas strokes, no image files or huge textures.
    if width >= 70 and span >= 55:
        for _ in range(2 if theme == "maple" else 3):
            cx = rng.uniform(26, max(27, width - 24))
            cy = rng.uniform(top + 18, bottom - 18)
            rx = rng.uniform(13, 37)
            ry = rng.uniform(2.3, 4.6)
            points = []
            for i in range(13):
                theta = math.tau * i / 12
                x = min(width, max(0, cx + rx * math.cos(theta)))
                y = max(top + 1, min(bottom - 1, cy + ry * math.sin(theta)))
                points.extend((x, y))
            shade = _blend(grain, base, .13 if theme == "maple" else .18)
            canvas.create_line(*points, fill=shade, width=1,
                               smooth=True, tags=("wood_texture",))
            drawn += 1
    return drawn
