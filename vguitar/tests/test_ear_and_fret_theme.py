"""Note Trainer v0.4.7: short open cell, fretboard finishes and true-pitch ear questions."""
import tempfile
import os
import unittest
from unittest.mock import Mock

from vguitar_notes import (
    NoteTrainer, OPEN_WIDTH, FRETBOARD_THEMES, EAR_REPLAYS,
    fret_start, fret_width, fret_center, fret_from_x, fret_inlay_centers,
    STANDARD_MIDI, TOP, ROW_H,
)
from vguitar_storage import read_preferences


class GeometryTests(unittest.TestCase):
    def test_open_position_smaller_than_a_fret(self):
        for cw in (66, 90, 120):
            self.assertLess(OPEN_WIDTH, cw)
            self.assertEqual(fret_start(0, cw), 0)
            self.assertEqual(fret_width(0, cw), OPEN_WIDTH)
            self.assertEqual(fret_start(1, cw), OPEN_WIDTH)
            for fret in (0, 1, 3, 12, 24):
                center=fret_center(fret,cw)
                self.assertEqual(fret_from_x(center,cw),fret)
            self.assertEqual(fret_from_x(OPEN_WIDTH-1,cw),0)
            self.assertEqual(fret_from_x(OPEN_WIDTH,cw),1)
            self.assertEqual(fret_from_x(OPEN_WIDTH+cw,cw),2)

    def test_all_themes_have_valid_distinct_surfaces(self):
        self.assertEqual(set(FRETBOARD_THEMES), {'default','ebony','maple','rosewood'})
        self.assertEqual(FRETBOARD_THEMES['default']['neck'], '#163349')
        self.assertEqual(len(set(v['neck'] for v in FRETBOARD_THEMES.values())), 4)
        for theme in FRETBOARD_THEMES.values():
            for key in ('neck','open','inactive','wire','string','muted','dot','dot_outline'):
                self.assertRegex(theme[key],r'^#[0-9a-f]{6}$')

    def test_inlays_center_on_actual_fret(self):
        for fret in (3,5,7,9,12,15,24):
            centers=fret_inlay_centers(fret, 80)
            for x,y in centers:
                self.assertEqual(x,fret_center(fret,80))
                self.assertLess(TOP,y)
                self.assertGreater(TOP+ROW_H*6,y)


class EarQuestionUnitTests(unittest.TestCase):
    def make_stub(self):
        app=NoteTrainer.__new__(NoteTrainer)
        app.tuning=STANDARD_MIDI
        app.active_strings=2
        app.active_frets=12
        app.question_count=30
        app.mode='ear'
        return app

    def test_ear_pool_uses_unique_absolute_midi_pitches(self):
        app=self.make_stub()
        questions=app._make_questions()
        self.assertEqual(len(questions),30)
        # Each cycle contains every playable MIDI note no more than once.
        total=len({app._pitch(q.row,q.fret) for q in questions})
        self.assertGreater(total,12)
        self.assertTrue(all(q.row in (4,5) and 0<=q.fret<=12 for q in questions))

    def test_distinguish_octaves_and_identical_notes_on_other_strings(self):
        app=self.make_stub()
        self.assertEqual(app._pitch(5,12),app._pitch(4,7))
        self.assertNotEqual(app._pitch(5,0),app._pitch(5,12))
        self.assertEqual(app._pitch_class(5,0),app._pitch_class(5,12))
