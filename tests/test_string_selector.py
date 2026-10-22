"""Independent string selection: run with python -m unittest tests/test_string_selector.py."""
import unittest
from vguitar_strings import normalize_selected_strings, rows_for_strings, strings_from_count


class StringSelectionTests(unittest.TestCase):
    def test_legacy_count(self):
        self.assertEqual(strings_from_count(1), (6,))
        self.assertEqual(strings_from_count(2), (6, 5))
        self.assertEqual(strings_from_count(6), (6, 5, 4, 3, 2, 1))

    def test_isolate_each_string(self):
        for s in range(1, 7):
            with self.subTest(s=s):
                self.assertEqual(normalize_selected_strings([s]), (s,))
                self.assertEqual(rows_for_strings((s,)), (s - 1,))

    def test_nonconsecutive(self):
        self.assertEqual(normalize_selected_strings([2, 6, 4, 2]), (6, 4, 2))
        self.assertEqual(rows_for_strings((6, 4, 2)), (1, 3, 5))

    def test_bad_values(self):
        for bad in (None, [], "5", [7], [5, "6"], [True], [5, 0]):
            self.assertEqual(normalize_selected_strings(bad, 2), (6, 5))
