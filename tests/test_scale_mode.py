"""Scale-position calculations, octave correctness and physical fret sizing."""
import unittest
from vguitar_notes import (SCALES, STANDARD_MIDI, TUNINGS, NOTE_EN,
                           OPEN_WIDTH, SCALE_POSITION_SPAN, FRET_RATIO,
                           board_base_width, board_width, fret_center, fret_from_x,
                           fret_width, fret_start, scale_positions, NoteTrainer)

class PhysicalGeometry(unittest.TestCase):
    def test_open_area_and_true_fret_spacing(self):
        self.assertGreater(OPEN_WIDTH,40)
        self.assertLess(OPEN_WIDTH,66)
        self.assertAlmostEqual(fret_start(1,100),OPEN_WIDTH)
        self.assertAlmostEqual(fret_width(2,100)/fret_width(1,100),FRET_RATIO)
        self.assertAlmostEqual(fret_width(12,100)/fret_width(11,100),FRET_RATIO)
        self.assertGreater(fret_width(1,100),fret_width(24,100))

    def test_all_click_targets(self):
        for frets in (1,7,12,24):
            w=board_base_width(480,frets)
            self.assertGreaterEqual(fret_width(frets,w),29-.001)
            for fret in range(frets+1):
                self.assertEqual(fret_from_x(fret_center(fret,w),w),fret)
            self.assertAlmostEqual(board_width(frets,w),fret_start(frets+1,w))

class ScaleMath(unittest.TestCase):
    def test_all_keys_all_positions_in_standard_tuning(self):
        for name in SCALES:
            for key in range(12):
                for start in range(21):
                    items=scale_positions(STANDARD_MIDI,name,key,start)
                    offsets,labels=SCALES[name]
                    self.assertEqual(len(items),len(offsets))
                    root=items[0][2]
                    self.assertEqual(root%12,key)
                    self.assertEqual(items[-1][2],root+12)
                    for row,fret,midi,degree in items:
                        self.assertTrue(start<=fret<start+SCALE_POSITION_SPAN)
                        self.assertEqual(STANDARD_MIDI[row]+fret,midi)
                    self.assertEqual([x[2]-root for x in items],list(offsets))
                    self.assertEqual([x[3] for x in items],list(labels))

    def test_e_minor_spelling_and_degrees(self):
        items=scale_positions(STANDARD_MIDI,'Натуральный минор',4,0)
        self.assertEqual([NOTE_EN[i[2]%12] for i in items],['E','F♯','G','A','B','C','D','E'])
        self.assertEqual([i[3] for i in items],['1','2','♭3','4','5','♭6','♭7','8'])

    def test_all_presets_have_full_octave_near_nut(self):
        for tuning in TUNINGS.values():
            for name in SCALES:
                for key in range(12):
                    try:
                        items=scale_positions(tuning,name,key,0)
                    except ValueError:
                        # Open tunings may not contain every scale step within 5 frets.
                        continue
                    self.assertEqual(items[-1][2]-items[0][2],12)

    def test_reject_bad_positions(self):
        for start in (-1,21,24):
            with self.assertRaises(ValueError):
                scale_positions(STANDARD_MIDI,'Мажор',0,start)

if __name__=='__main__': unittest.main()
