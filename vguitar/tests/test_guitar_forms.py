import unittest
from vguitar_forms import *

class FormsTest(unittest.TestCase):
    def test_major_d_e_form_reference(self):
        notes=caged_scale(STANDARD_MIDI,2,'E')
        self.assertIn((5,10,50,'1'),notes)
        self.assertIn((3,12,62,'1'),notes)
        self.assertIn((0,10,74,'1'),notes)
    def test_all_caged_major_and_minor(self):
        for tuning in [STANDARD_MIDI,tuple(x-2 for x in STANDARD_MIDI)]:
            for key in range(12):
                for form in CAGED_ORDER:
                    for minor in (False,True):
                        notes=caged_scale(tuning,key,form,minor)
                        degrees={'1','2','♭3','4','5','♭6','♭7'} if minor else {'1','2','3','4','5','6','7'}
                        self.assertEqual({d for _,_,_,d in notes},degrees)
                        self.assertEqual(len({(r,f) for r,f,_,_ in notes}),len(notes))
                        self.assertTrue(all(tuning[r]+f==m for r,f,m,d in notes))
    def test_no_drop_tuning_caged(self):
        with self.assertRaisesRegex(ValueError,'интервал'):
            caged_scale((64,59,55,50,45,38),2,'E')
    def test_power_chords_all_keys_strings(self):
        for tuning in [STANDARD_MIDI,tuple(x-1 for x in STANDARD_MIDI)]:
            for key in range(12):
                for s in (6,5,4):
                    for v in POWER_VOICES:
                        steps=power_chord(tuning,key,s,v)
                        self.assertEqual([x[3] for x in steps],['1','5'] if v=='1–5' else ['1','5','8'])
                        self.assertEqual(steps[0][0],{6:5,5:4,4:3}[s])
                        self.assertEqual([m-steps[0][2] for _,_,m,_ in steps],[0,7] if v=='1–5' else [0,7,12])
    def test_power_d_root_string_4_octave(self):
        self.assertEqual([(r,f) for r,f,_,_ in power_chord(STANDARD_MIDI,2,4,'1–5–8')],[(3,0),(2,2),(1,3)])
    def test_triad_all_keys_qualities_inversions_groups(self):
        for tuning in [STANDARD_MIDI,tuple(x-2 for x in STANDARD_MIDI)]:
            for key in range(12):
                for quality in TRIAD_QUALITIES:
                    for inv in range(3):
                        for group in ('1–2–3','2–3–4','3–4–5','4–5–6'):
                            steps=triad_voicing(tuning,key,quality,group,inv)
                            self.assertEqual(steps[0][3],TRIAD_LABELS[quality][inv])
                            self.assertEqual([m for _,_,m,_ in steps],sorted(m for _,_,m,_ in steps))
                            self.assertEqual(set(x[3] for x in steps),set(TRIAD_LABELS[quality]))
                            self.assertLessEqual(max(x[1] for x in steps)-min(x[1] for x in steps),5)
    def test_c_major_top_strings(self):
        a=triad_voicing(STANDARD_MIDI,0,'Мажор','1–2–3',0)
        self.assertEqual([(r,f) for r,f,_,_ in a],[(2,5),(1,5),(0,3)])
    def test_finger_hints(self):
        self.assertEqual(suggested_fingers(power_chord(STANDARD_MIDI,7,6))[(5,3)],'1')
        self.assertEqual(suggested_fingers(power_chord(STANDARD_MIDI,2,4))[(3,0)],'0')

if __name__=='__main__':unittest.main()
