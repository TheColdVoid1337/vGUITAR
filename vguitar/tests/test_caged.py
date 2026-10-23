"""CAGED chord tone mapping and tuning regression checks."""
import unittest
from vguitar_caged import (STANDARD_MIDI, CAGED_ORDER, CAGED_OPEN_FORMS,
                           caged_shift, caged_positions, next_caged_form)


class CagedTests(unittest.TestCase):
    def test_open_shapes(self):
        for form, key in {"C":0, "A":9, "G":7, "E":4, "D":2}.items():
            positions = caged_positions(STANDARD_MIDI, key, form)
            self.assertEqual(caged_shift(STANDARD_MIDI, key, form), 0)
            self.assertEqual(len(positions), sum(v is not None for v in CAGED_OPEN_FORMS[form]))
            self.assertEqual({p[3] for p in positions}, {"1", "3", "5"})

    def test_major_chord_in_all_keys(self):
        for key in range(12):
            for form in CAGED_ORDER:
                positions = caged_positions(STANDARD_MIDI, key, form)
                self.assertTrue(all((midi-key)%12 in (0,4,7) for _,_,midi,_ in positions))
                self.assertTrue(all(0<=f<=24 for _,f,_,_ in positions))

    def test_e_shape_g_major(self):
        self.assertEqual({(r,f,d) for r,f,_,d in caged_positions(STANDARD_MIDI,7,"E")},
                         {(5,3,"1"),(4,5,"5"),(3,5,"1"),(2,4,"3"),(1,3,"5"),(0,3,"1")})

    def test_uniform_transposition_and_drop_d(self):
        self.assertEqual(caged_shift(tuple(v-2 for v in STANDARD_MIDI),7,"E"),5)
        with self.assertRaisesRegex(ValueError,"standard string intervals"):
            caged_positions((64,59,55,50,45,38),7,"E")

    def test_auto_cycles(self):
        current=None
        seen=[]
        for i in range(6):
            current=next_caged_form(current)
            seen.append(current)
        self.assertEqual(seen,["C","A","G","E","D","C"])


if __name__ == "__main__":
    unittest.main()
