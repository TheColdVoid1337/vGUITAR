import unittest
from vguitar_scale_shapes import STANDARD_MIDI, pentatonic_box
from vguitar_scale_patterns import (BLUES_SCALE, FINGERING_SCALES, DIATONIC_OFFSETS,
    shape_names, shape_family, next_shape, scale_fingering)

class ShapeTests(unittest.TestCase):
    def test_every_scale_has_applicative_shapes(self):
        self.assertEqual(len(FINGERING_SCALES),7)
        for scale in FINGERING_SCALES:
            names=shape_names(scale)
            self.assertEqual(len(names),7 if scale in DIATONIC_OFFSETS else 5)
            self.assertEqual(next_shape(scale,len(names)),1)
    def test_major_position_one_starts_on_sixth_string_root(self):
        notes=scale_fingering(STANDARD_MIDI,'Мажор',2,1)
        self.assertEqual(notes[0],(5,10,50,'1'))
        self.assertEqual(len(notes),18)
        self.assertEqual([r for r,_,_,_ in notes], [r for r in range(5,-1,-1) for _ in range(3)])
    def test_all_keys_all_shapes_cover_correct_intervals(self):
        for scale in FINGERING_SCALES:
            for key in range(12):
                shapes=[]
                for i in range(1,len(shape_names(scale))+1):
                    notes=scale_fingering(STANDARD_MIDI,scale,key,i)
                    self.assertEqual(len(notes),18 if scale in DIATONIC_OFFSETS else 12 if 'пентатоника' in scale else len(notes))
                    self.assertTrue(all(0<=f<=24 for _,f,_,_ in notes))
                    self.assertTrue(all(STANDARD_MIDI[r]+f==m for r,f,m,_ in notes))
                    self.assertEqual(len(set((r,f) for r,f,_,_ in notes)),len(notes))
                    self.assertTrue(any(deg=='1' for _,_,_,deg in notes))
                    self.assertTrue(max(f for _,f,_,_ in notes)-min(f for _,f,_,_ in notes)<=7)
                    shapes.append(frozenset((r,f%12) for r,f,_,_ in notes))
                self.assertEqual(len(set(shapes)),len(shape_names(scale)))
    def test_major_dorian_minor_phrygian_degree_set(self):
        for scale,(offsets,labels) in DIATONIC_OFFSETS.items():
            for key in range(12):
                for idx in range(1,8):
                    notes=scale_fingering(STANDARD_MIDI,scale,key,idx)
                    self.assertEqual({(m-key)%12 for _,_,m,_ in notes}, set(offsets))
                    self.assertEqual({d for _,_,_,d in notes},set(labels))
    def test_all_strings_three_notes(self):
        for scale in DIATONIC_OFFSETS:
            for key in (0,2,4,9):
                for idx in range(1,8):
                    notes=scale_fingering(STANDARD_MIDI,scale,key,idx)
                    for row in range(6):
                        self.assertEqual(len([r for r,_,_,_ in notes if r==row]),3)
                    self.assertEqual([m for _,_,m,_ in notes],sorted(m for _,_,m,_ in notes))
    def test_blues_shape_contains_minor_pent_and_flat_five(self):
        notes=scale_fingering(STANDARD_MIDI,BLUES_SCALE,9,1)
        base=pentatonic_box(STANDARD_MIDI,'Минорная пентатоника',9,1)
        self.assertTrue({(r,f) for r,f,_,_ in base}.issubset({(r,f) for r,f,_,_ in notes}))
        self.assertIn((4,6,51,'♭5'),notes)
        self.assertIn((2,8,63,'♭5'),notes)
        self.assertEqual({(m-9)%12 for _,_,m,_ in notes},{0,3,5,6,7,10})
    def test_uniform_transposition_and_reject_drop(self):
        for scale in FINGERING_SCALES:
            for number in range(1,len(shape_names(scale))+1):
                normal=scale_fingering(STANDARD_MIDI,scale,9,number)
                lowered=(63,58,54,49,44,39)
                other=scale_fingering(lowered,scale,8,number)
                self.assertEqual([(r,f) for r,f,_,_ in normal],[(r,f) for r,f,_,_ in other])
                with self.assertRaisesRegex(ValueError,'интервал'):
                    scale_fingering((64,59,55,50,45,38),scale,9,number)
    def test_invalid_number_and_key(self):
        for n in (0,8,42):
            with self.assertRaises(ValueError):scale_fingering(STANDARD_MIDI,'Мажор',2,n)
        with self.assertRaises(ValueError):scale_fingering(STANDARD_MIDI,'Мажор',12,1)

if __name__=='__main__':unittest.main()
