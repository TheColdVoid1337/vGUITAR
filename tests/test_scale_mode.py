"""Full scale-box coverage, auto-position defaults, and true fret geometry."""
import random
import unittest
from vguitar_notes import (SCALES, STANDARD_MIDI, TUNINGS, NOTE_EN,
                           OPEN_WIDTH, SCALE_POSITION_SPAN, FRET_RATIO,
                           board_base_width, board_width, fret_center, fret_from_x,
                           fret_width, fret_start, scale_positions, auto_scale_position,
                           NoteTrainer)


class PhysicalGeometry(unittest.TestCase):
    def test_open_area_and_true_fret_spacing(self):
        self.assertGreater(OPEN_WIDTH, 40)
        self.assertLess(OPEN_WIDTH, 66)
        self.assertAlmostEqual(fret_start(1,100), OPEN_WIDTH)
        self.assertAlmostEqual(fret_width(2,100)/fret_width(1,100), FRET_RATIO)
        self.assertGreater(fret_width(1,100), fret_width(24,100))

    def test_all_click_targets(self):
        for frets in (1, 7, 12, 24):
            w=board_base_width(480,frets)
            self.assertGreaterEqual(fret_width(frets,w),29-.001)
            for fret in range(frets+1):
                self.assertEqual(fret_from_x(fret_center(fret,w),w),fret)
            self.assertAlmostEqual(board_width(frets,w),fret_start(frets+1,w))


class ScaleMath(unittest.TestCase):
    def test_complete_box_every_string_all_keys_all_positions(self):
        for name in SCALES:
            for key in range(12):
                expected=set(n%12 for n in SCALES[name][0])
                for start in range(21):
                    items=scale_positions(STANDARD_MIDI,name,key,start)
                    allowed={((key+offset)%12) for offset in expected}
                    actual={midi%12 for _,_,midi,_ in items}
                    self.assertEqual(actual,allowed)
                    coordinates={(row,fret) for row,fret,_,_ in items}
                    expected_coords={(row,fret) for row in range(6) for fret in range(start,start+5)
                                     if (STANDARD_MIDI[row]+fret)%12 in allowed}
                    self.assertEqual(coordinates,expected_coords)
                    self.assertGreater(len(items),len(SCALES[name][0]))
                    self.assertEqual([r for r,_,_,_ in items],sorted([r for r,_,_,_ in items],reverse=True))
                    for row,fret,midi,degree in items:
                        self.assertTrue(start<=fret<start+5)
                        self.assertEqual(STANDARD_MIDI[row]+fret,midi)
                        self.assertIn(degree,SCALES[name][1])

    def test_pentatonic_requires_every_position_not_only_five_degrees(self):
        notes=scale_positions(STANDARD_MIDI,'Минорная пентатоника',4,0)
        self.assertGreater(len(notes),6)
        self.assertEqual(len({(r,f) for r,f,_,_ in notes}),len(notes))
        self.assertEqual({NOTE_EN[midi%12] for _,_,midi,_ in notes}, {'E','G','A','B','D'})
        self.assertEqual(notes[0][:2],(5,0))

    def test_auto_chooses_real_positions_and_avoids_repeat(self):
        chooser=random.Random(17)
        for name in SCALES:
            for key in range(12):
                first=auto_scale_position(STANDARD_MIDI,name,key,rng=chooser)
                second=auto_scale_position(STANDARD_MIDI,name,key,previous=first,rng=chooser)
                self.assertTrue(0<=first<=20)
                self.assertNotEqual(first,second)
                self.assertTrue(scale_positions(STANDARD_MIDI,name,key,first))

    def test_tunings_and_edge_limits(self):
        for tuning in TUNINGS.values():
            for name in SCALES:
                for key in (0,4,9):
                    pos=auto_scale_position(tuning,name,key,rng=random.Random(7))
                    self.assertTrue(scale_positions(tuning,name,key,pos))
        for start in (-1,21,24):
            with self.assertRaises(ValueError):
                scale_positions(STANDARD_MIDI,'Мажор',0,start)


if __name__=='__main__': unittest.main()
