"""Tests for note mapping and question generation (no GUI display required)."""
import unittest
from unittest.mock import patch
from vguitar_notes import NOTE_EN, STRINGS, Question, NoteTrainer, name_at, STANDARD_MIDI


class FretboardTests(unittest.TestCase):
    def test_tuning_order_is_high_to_low(self):
        self.assertEqual([row[1] for row in STRINGS], ['e','B','G','D','A','E'])

    def test_open_string_notes(self):
        self.assertEqual([name_at(i, 0) for i in range(6)], ['E','B','G','D','A','E'])

    def test_low_e_natural_notes(self):
        self.assertEqual([name_at(5, fret) for fret in (0,1,3,5,7,8,10,12)],
                         ['E','F','G','A','B','C','D','E'])

    def test_a_string_natural_notes(self):
        self.assertEqual([name_at(4, fret) for fret in (0,2,3,5,7,8,10,12)],
                         ['A','B','C','D','E','F','G','A'])

    def test_octave_at_12th_fret(self):
        for i in range(6):
            self.assertEqual(name_at(i,0),name_at(i,12))
            self.assertEqual(name_at(i,12),name_at(i,24))

    def test_pitch_class_is_consistent(self):
        for row in range(6):
            for fret in range(25):
                self.assertEqual(NOTE_EN[Question(row,fret).pitch],name_at(row,fret))

    def test_active_strings_low_first(self):
        stub=NoteTrainer.__new__(NoteTrainer)
        stub.active_strings=2
        self.assertEqual([i for i in range(6) if stub._active(i)],[4,5])

    def test_quiz_exact_length_and_range(self):
        stub=NoteTrainer.__new__(NoteTrainer)
        stub.active_strings=2
        stub.active_frets=5
        stub.question_count=45
        stub.mode='name'
        qs=stub._make_questions()
        self.assertEqual(len(qs),45)
        self.assertTrue(all(q.row in (4,5) and 0<=q.fret<=5 for q in qs))

    def test_find_avoids_duplicate_pitch_in_batch(self):
        stub=NoteTrainer.__new__(NoteTrainer)
        stub.active_strings=1
        stub.active_frets=24
        stub.question_count=12
        stub.mode='find'
        stub.tuning=STANDARD_MIDI
        qs=stub._make_questions()
        self.assertEqual(len({(q.row,q.pitch) for q in qs}),12)

    def test_blank_open_string_supported(self):
        self.assertEqual(Question(5,0).pitch,4)
        self.assertEqual(Question(4,0).pitch,9)

if __name__=='__main__': unittest.main()
