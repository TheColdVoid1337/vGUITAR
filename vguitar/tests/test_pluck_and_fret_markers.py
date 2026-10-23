"""Per-note tone and fret geometry regression tests (without real audio hardware)."""
import io
import math
import statistics
import unittest
import wave
from array import array

from vguitar_audio import synthesize_string, midi_frequency
from vguitar_notes import ROW_H, TOP, fret_inlay_centers, note_disc_bbox, fret_center


def wav_samples(note, **opts):
    data = synthesize_string(note, **opts)
    with wave.open(io.BytesIO(data), 'rb') as w:
        samples = array('h')
        samples.frombytes(w.readframes(w.getnframes()))
        return samples, w.getframerate()


def rms(values):
    return math.sqrt(sum(v * v for v in values) / len(values))


class PluckSoundTests(unittest.TestCase):
    def test_smooth_onset_no_percussive_click(self):
        samples, sr = wav_samples(40, duration=1.55, sample_rate=48000)
        self.assertEqual(samples[0], 0)
        # A note should bloom rather than start with a full-volume noise burst.
        self.assertLess(rms(samples[:int(.002*sr)]), rms(samples[int(.03*sr):int(.06*sr)]) * .20)
        self.assertLess(abs(samples[-1]), 1200)

    def test_sustained_body_remains_audible(self):
        samples, sr = wav_samples(40, duration=1.55, sample_rate=48000)
        early = rms(samples[int(.08*sr):int(.18*sr)])
        late = rms(samples[int(.90*sr):int(1.05*sr)])
        self.assertGreater(late, 0.01 * 32767)
        self.assertLess(late, early)

    def test_distinct_muted_fret_buzz(self):
        normal, sr = wav_samples(50, duration=1.55, sample_rate=48000)
        buzz, _ = wav_samples(50, duration=.55, sample_rate=48000, buzzing=True)
        self.assertLess(len(buzz), len(normal) * .4)
        self.assertNotEqual(normal[:1000], buzz[:1000])
        self.assertLess(rms(buzz[-1000:]), rms(buzz[1000:3000]))

    def test_deterministic_and_pitch_dependent(self):
        a, sr = wav_samples(40, duration=.2)
        b, _ = wav_samples(40, duration=.2)
        c, _ = wav_samples(41, duration=.2)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertAlmostEqual(midi_frequency(40), 82.406889, places=4)


class FretMarkersTests(unittest.TestCase):
    def test_standard_single_and_double_markers(self):
        singles = (3, 5, 7, 9, 15, 17, 19, 21)
        doubles = (12, 24)
        for fret in range(25):
            dots = fret_inlay_centers(fret, 120)
            self.assertEqual(len(dots), 2 if fret in doubles else 1 if fret in singles else 0)
            for x, y in dots:
                self.assertEqual(x, fret_center(fret, 120))
                self.assertGreater(y, TOP)
                self.assertLess(y, TOP + 6*ROW_H)

    def test_note_disc_stays_round_at_multiple_widths(self):
        for width in (66, 90, 120, 220):
            bbox = note_disc_bbox(300, TOP+ROW_H*2+.5*ROW_H, width)
            self.assertAlmostEqual(bbox[2]-bbox[0],bbox[3]-bbox[1])
            self.assertLessEqual(bbox[2]-bbox[0],27)


if __name__ == '__main__':
    unittest.main()
