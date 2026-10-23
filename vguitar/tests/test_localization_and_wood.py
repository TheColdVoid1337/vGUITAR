"""Regression coverage for bilingual presentation and wood-grain layers."""
import tkinter as tk
import unittest

from vguitar_i18n import LocalizedVar, from_display, set_language, tr
from vguitar_wood import draw_wood_grain
from vguitar_notes import FRETBOARD_THEMES


class I18nTests(unittest.TestCase):
    def tearDown(self):
        set_language("ru")

    def test_russian_is_unchanged(self):
        set_language("ru")
        self.assertEqual(tr("Натуральный минор"), "Натуральный минор")
        self.assertEqual(tr("Вопрос 3/10"), "Вопрос 3/10")

    def test_english_labels_and_generated_headers(self):
        set_language("en")
        self.assertEqual(tr("Натуральный минор"), "Natural minor")
        self.assertEqual(tr("Струны 6,5"), "Strings 6,5")
        self.assertEqual(tr("Вопрос 3/10"), "Question 3/10")
        self.assertEqual(tr("Накладка грифа"), "Fretboard wood")

    def test_option_labels_preserve_canonical_data(self):
        set_language("en")
        for original in ("Натуральный минор", "Трезвучие", "Авто",
                         "Минорная гамма", "Участок ладов", "На слух"):
            self.assertEqual(from_display(tr(original)), original)
        tcl = tk.Tcl()
        choice = LocalizedVar(master=tcl, value="Натуральный минор")
        self.assertEqual(choice.get(), "Натуральный минор")
        self.assertEqual(tcl.getvar(choice._name), "Natural minor")
        tcl.setvar(choice._name, "Triad")
        self.assertEqual(choice.get(), "Трезвучие")


class _FakeCanvas:
    def __init__(self):
        self.lines = []

    def create_line(self, *args, **kwargs):
        self.lines.append((args, kwargs))


class WoodTests(unittest.TestCase):
    def test_available_woods_and_preserved_originals(self):
        self.assertEqual(list(FRETBOARD_THEMES), ["default", "ebony", "maple", "rosewood"])
        self.assertEqual(FRETBOARD_THEMES["default"]["neck"], "#163349")
        self.assertEqual(FRETBOARD_THEMES["ebony"]["neck"], "#1b1a1c")
        self.assertTrue(FRETBOARD_THEMES["maple"]["grain"])
        self.assertTrue(FRETBOARD_THEMES["rosewood"]["grain"])

    def test_texture_is_deterministic_and_separate_layer(self):
        p = FRETBOARD_THEMES["rosewood"]
        canvas = _FakeCanvas()
        count = draw_wood_grain(canvas, "rosewood", 300, 24, 210,
                                p["neck"], p["grain"])
        self.assertGreater(count, 0)
        self.assertEqual(len(canvas.lines), count)
        self.assertTrue(all(k["tags"] == ("wood_texture",) for _, k in canvas.lines))
        again = _FakeCanvas()
        draw_wood_grain(again, "rosewood", 300, 24, 210, p["neck"], p["grain"])
        self.assertEqual(canvas.lines, again.lines)
        self.assertTrue(all(24 <= coords[i] <= 210
                            for coords, _ in canvas.lines
                            for i in range(1, len(coords), 2)))

    def test_original_has_no_wood_overlay(self):
        p = FRETBOARD_THEMES["default"]
        canvas = _FakeCanvas()
        self.assertEqual(draw_wood_grain(canvas, "default", 300, 24, 210,
                                         p["neck"], p["grain"]), 0)
        self.assertFalse(canvas.lines)


if __name__ == "__main__":
    unittest.main()
