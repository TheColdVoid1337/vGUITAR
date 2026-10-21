"""Non-GUI tests for vGUITAR's note and quiz logic."""
import unittest

from vguitar_notes import NOTE_EN, STRINGS, Question, NoteTrainer, name_at


class FretboardTests(unittest.TestCase):
    def test_standard_tuning(self):
        self.assertEqual([name_at(i, 0) for i in range(6)], ["E", "B", "G", "D", "A", "E"])

    def test_low_e_natural_notes(self):
        self.assertEqual([name_at(5, n) for n in (0, 1, 3, 5, 7, 8, 10, 12)],
                         ["E", "F", "G", "A", "B", "C", "D", "E"])

    def test_a_natural_notes(self):
        self.assertEqual([name_at(4, n) for n in (0, 2, 3, 5, 7, 8, 10, 12)],
                         ["A", "B", "C", "D", "E", "F", "G", "A"])

    def test_octaves_repeat(self):
        for row in range(6):
            self.assertEqual(name_at(row, 0), name_at(row, 12))
            self.assertEqual(name_at(row, 12), name_at(row, 24))

    def test_pitch_consistency(self):
        for row in range(6):
            for fret in range(25):
                self.assertEqual(NOTE_EN[Question(row, fret).pitch], name_at(row, fret))

    def test_active_strings_start_from_bass(self):
        app = NoteTrainer.__new__(NoteTrainer)
        app.active_strings = 2
        self.assertEqual([r for r in range(6) if app._active(r)], [4, 5])

    def test_questions_within_selected_range(self):
        app = NoteTrainer.__new__(NoteTrainer)
        app.active_strings, app.active_frets, app.question_count, app.mode = 2, 5, 45, "name"
        questions = app._make_questions()
        self.assertEqual(len(questions), 45)
        self.assertTrue(all(q.row in (4, 5) and 0 <= q.fret <= 5 for q in questions))

    def test_find_questions_deduplicate_octaves(self):
        app = NoteTrainer.__new__(NoteTrainer)
        app.active_strings, app.active_frets, app.question_count, app.mode = 1, 24, 12, "find"
        questions = app._make_questions()
        self.assertEqual(len({(q.row, q.pitch) for q in questions}), 12)

    def test_open_string_positions(self):
        self.assertEqual(Question(5, 0).pitch, 4)
        self.assertEqual(Question(4, 0).pitch, 9)


if __name__ == "__main__":
    unittest.main()
