"""Visual guitar hardware, grain seeds and backward-compatible settings."""
import math
import unittest

from vguitar_visual import (
    STRING_SETS, STRING_MATERIALS, NUT_THICKNESSES_MM, NUT_MATERIALS,
    FRET_CROWNS_MM, FRET_MATERIALS, VISUAL_DEFAULTS, clean_visual_settings,
    string_widths, nut_width_px, fret_width_px, material_label,
)
from vguitar_wood import draw_wood_grain
from vguitar_notes import FRETBOARD_THEMES, blend_hex


class _Canvas:
    def __init__(self):
        self.lines = []

    def create_line(self, *xy, **options):
        self.lines.append((xy, options))


class HardwareTests(unittest.TestCase):
    def test_electric_guitar_gauges_ordered(self):
        self.assertIn("9–42", STRING_SETS)
        self.assertIn("10–46", STRING_SETS)
        self.assertIn("11–48", STRING_SETS)
        self.assertIn("12–56", STRING_SETS)
        for gauges in STRING_SETS.values():
            self.assertEqual(len(gauges), 6)
            self.assertEqual(tuple(sorted(gauges)), gauges)
            self.assertTrue(all(8 <= gauge <= 56 for gauge in gauges))

    def test_visual_string_strokes_change_with_gauge(self):
        light = string_widths("8–38")
        heavy = string_widths("12–56")
        self.assertEqual(len(light), 6)
        self.assertTrue(all(x < y for x, y in zip(light, heavy)))
        self.assertEqual(list(light), sorted(light))
        self.assertTrue(all(1 <= v <= 4.8 for v in heavy))

    def test_material_colors_are_distinct_valid_hexes(self):
        for materials in (STRING_MATERIALS, NUT_MATERIALS, FRET_MATERIALS):
            colors = [item[2] for item in materials.values()]
            self.assertEqual(len(set(colors)), len(colors))
            for color in colors:
                self.assertRegex(color, r"^#[0-9a-f]{6}$")
        self.assertEqual(material_label(NUT_MATERIALS, "bone", "en"), "Bone")
        self.assertEqual(material_label(NUT_MATERIALS, "bone", "ru"), "Кость")

    def test_realistic_hardware_dimensions_and_pixel_limits(self):
        self.assertEqual(NUT_THICKNESSES_MM[0], 3.0)
        self.assertEqual(NUT_THICKNESSES_MM[-1], 6.0)
        self.assertAlmostEqual(FRET_CROWNS_MM[0], 2.03)
        self.assertAlmostEqual(FRET_CROWNS_MM[-1], 2.99)
        self.assertTrue(all(nut_width_px(a) < nut_width_px(b)
                            for a, b in zip(NUT_THICKNESSES_MM, NUT_THICKNESSES_MM[1:])))
        self.assertTrue(all(fret_width_px(a) < fret_width_px(b)
                            for a, b in zip(FRET_CROWNS_MM, FRET_CROWNS_MM[1:])))

    def test_saved_hardware_settings_are_clean_and_backward_compatible(self):
        self.assertEqual(clean_visual_settings(None), VISUAL_DEFAULTS)
        self.assertEqual(clean_visual_settings({"nut_mm": float("nan")}), VISUAL_DEFAULTS)
        self.assertEqual(clean_visual_settings({"string_set": "bad"})["string_set"], "10–46")
        self.assertEqual(clean_visual_settings({"inlay_radius": 999})["inlay_radius"], 7.5)
        self.assertEqual(clean_visual_settings({"inlay_radius": -100})["inlay_radius"], 2.5)
        self.assertEqual(clean_visual_settings({"nut_mm": 6, "fret_mm": 2.99,
                                                "string_material": "cobalt"}),
                         {**VISUAL_DEFAULTS, "nut_mm": 6.0, "fret_mm": 2.99,
                          "string_material": "cobalt"})

    def test_ebony_inactive_contrast_with_unchanged_active_wood(self):
        ebony = FRETBOARD_THEMES["ebony"]
        self.assertEqual(ebony["neck"], "#1b1a1c")
        overlay = blend_hex(ebony["neck"], ebony["inactive"], .4)
        base_rgb = [int(ebony["neck"][i:i+2], 16) for i in (1, 3, 5)]
        overlay_rgb = [int(overlay[i:i+2], 16) for i in (1, 3, 5)]
        self.assertGreater(sum(overlay_rgb) - sum(base_rgb), 45)


class GrainTests(unittest.TestCase):
    def test_stable_seed_and_different_rerolls(self):
        palette = FRETBOARD_THEMES["rosewood"]
        a, b, c = _Canvas(), _Canvas(), _Canvas()
        size = (360, 24, 210, palette["neck"], palette["grain"])
        self.assertGreater(draw_wood_grain(a, "rosewood", *size, seed=101), 10)
        self.assertGreater(draw_wood_grain(b, "rosewood", *size, seed=202), 10)
        draw_wood_grain(c, "rosewood", *size, seed=101)
        self.assertNotEqual(a.lines, b.lines)
        self.assertEqual(a.lines, c.lines)
        self.assertTrue(all(options.get("tags") == ("wood_texture",)
                            for _, options in a.lines))

    def test_original_virtual_surface_never_has_texture(self):
        original = FRETBOARD_THEMES["default"]
        canvas = _Canvas()
        self.assertEqual(draw_wood_grain(canvas, "default", 100, 24, 210,
                                         original["neck"], original["grain"],
                                         seed=15), 0)
        self.assertFalse(canvas.lines)


if __name__ == "__main__":
    unittest.main()
