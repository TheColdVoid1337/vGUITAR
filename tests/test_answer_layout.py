"""Layout geometry and note-order tests without a display server."""
import math
import unittest

from vguitar_notes import NoteTrainer


class AnswerLayoutTests(unittest.TestCase):
    def test_twelve_pitch_classes_in_circle(self):
        points = NoteTrainer._circle_points(340, 230)
        self.assertEqual(set(points), set(range(12)))

    def test_natural_notes_are_on_outer_ring(self):
        points = NoteTrainer._circle_points(340, 230)
        naturals = (0, 2, 4, 5, 7, 9, 11)
        outer = [math.hypot(points[n][0] - 170, points[n][1] - 115) for n in naturals]
        inner = [math.hypot(points[n][0] - 170, points[n][1] - 115) for n in (1, 3, 6, 8, 10)]
        self.assertTrue(all(abs(r - outer[0]) < 1e-6 for r in outer))
        self.assertTrue(all(abs(r - inner[0]) < 1e-6 for r in inner))
        self.assertGreater(outer[0], inner[0])

    def test_no_marker_outside_wheel_on_small_screen(self):
        for w, h in ((190,125),(270,160),(340,215),(700,300)):
            with self.subTest(size=(w,h)):
                for x,y,r in NoteTrainer._circle_points(w,h).values():
                    self.assertGreaterEqual(x-r,0)
                    self.assertGreaterEqual(y-r,0)
                    self.assertLessEqual(x+r,w)
                    self.assertLessEqual(y+r,h)

    def test_sharps_align_radially_with_parent_naturals(self):
        # Each accidental sits directly inside its base natural, not between angles.
        for w,h in ((190, 125), (340,230), (700,500)):
            with self.subTest(size=(w,h)):
                points = NoteTrainer._circle_points(w,h)
                cx,cy=w/2,h/2
                for natural,sharp in ((0,1),(2,3),(5,6),(7,8),(9,10)):
                    nx,ny,nr=points[natural]
                    sx,sy,sr=points[sharp]
                    self.assertAlmostEqual((nx-cx)*(sy-cy)-(ny-cy)*(sx-cx),0,places=5)
                    self.assertLess(math.hypot(sx-cx,sy-cy),math.hypot(nx-cx,ny-cy))
                    self.assertGreater(math.hypot(nx-sx,ny-sy),nr+sr)

    def test_valid_answers_are_unique_pitch_classes(self):
        self.assertEqual(len(NoteTrainer._circle_points(340,230)), 12)


if __name__ == '__main__':
    unittest.main()
