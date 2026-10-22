"""Canonical guitar box coordinates, frets, degrees, and key/tuning transfer."""
import unittest
from vguitar_scale_shapes import BOX_SCALES, BOX_NAMES, pentatonic_box, next_box
from vguitar_notes import STANDARD_MIDI, TUNINGS, SCALES


class PentatonicShapeTests(unittest.TestCase):
    def test_a_minor_box_one_matches_reference(self):
        box = pentatonic_box(STANDARD_MIDI, 'Минорная пентатоника', 9, 1)
        expected = {
            (5,5), (5,8), (4,5), (4,7), (3,5), (3,7),
            (2,5), (2,7), (1,5), (1,8), (0,5), (0,8),
        }
        self.assertEqual({(r,f) for r,f,_,_ in box}, expected)
        self.assertNotIn((2,9), expected, 'E on G9 belongs to scale but not to Box 1')
        self.assertEqual({(r,f) for r,f,_,d in box if d=='1'}, {(5,5),(3,7),(0,5)})

    def test_every_box_has_six_strings_two_notes_each_all_keys(self):
        for scale in BOX_SCALES:
            expected_pc = set(SCALES[scale][0])
            for key in range(12):
                for box in range(1,6):
                    notes=pentatonic_box(STANDARD_MIDI,scale,key,box)
                    self.assertEqual(len(notes),12,(scale,key,box))
                    self.assertEqual([r for r,_,_,_ in notes], [r for r in range(5,-1,-1) for _ in range(2)])
                    self.assertEqual(len({(r,f) for r,f,_,_ in notes}),12)
                    self.assertTrue(all(0<=f<=24 and STANDARD_MIDI[r]+f==m for r,f,m,_ in notes))
                    self.assertEqual({m%12 for _,_,m,_ in notes}, {(key+v)%12 for v in expected_pc})
                    self.assertEqual(set(d for _,_,_,d in notes), set(SCALES[scale][1][:-1]))

    def test_all_five_distinct_and_adjacent_boxes_share_border_notes(self):
        for scale in BOX_SCALES:
            for key in range(12):
                coords=[{(r,f%12) for r,f,m,d in pentatonic_box(STANDARD_MIDI,scale,key,box)} for box in range(1,6)]
                self.assertEqual(len({frozenset(s) for s in coords}),5)
                for i in range(4):
                    self.assertGreaterEqual(len(coords[i]&coords[i+1]),2)

    def test_transposing_all_strings_preserves_box_geometry(self):
        for scale in BOX_SCALES:
            for key in (0,2,9):
                for name in ('E♭ Standard (E♭ A♭ D♭ G♭ B♭ E♭)', 'D Standard (D G C F A D)'):
                    tuning=TUNINGS[name]
                    shift=tuning[5]-STANDARD_MIDI[5]
                    for box in range(1,6):
                        a=pentatonic_box(STANDARD_MIDI,scale,key,box)
                        b=pentatonic_box(tuning,scale,(key+shift)%12,box)
                        self.assertEqual([(r,f) for r,f,_,_ in a],[(r,f) for r,f,_,_ in b])

    def test_drop_tunings_rejected_only_for_classic_boxes(self):
        for name in ('Drop D (D A D G B E)', 'Drop C (C G C F A D)', 'Open G (D G D G B D)'):
            with self.assertRaisesRegex(ValueError,'интервал'):
                pentatonic_box(TUNINGS[name], 'Минорная пентатоника',9,1)
        with self.assertRaisesRegex(ValueError,'пентатоники'):
            pentatonic_box(STANDARD_MIDI,'Мажор',2,1)

    def test_cycles_five_boxes(self):
        box=1
        for expect in (2,3,4,5,1):
            box=next_box(box)
            self.assertEqual(box,expect)

if __name__=='__main__': unittest.main()
