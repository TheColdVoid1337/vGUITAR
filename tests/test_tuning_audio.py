"""Offline deterministic tests for tuning, audio, persistent user settings."""
import io
import json
from pathlib import Path
import tempfile
import unittest
import wave

from vguitar_audio import AudioPlayer, SAMPLE_RATE, midi_frequency, synthesize_string
from vguitar_notes import (STANDARD_MIDI, TUNINGS, CUSTOM_TUNING, midi_label,
                           note_at, pitch_at, read_settings, write_settings,
                           NoteTrainer, NOTE_EN, readable_note)


class Tunings(unittest.TestCase):
    def test_all_presets_six_strings_and_valid_range(self):
        for name, notes in TUNINGS.items():
            with self.subTest(preset=name):
                self.assertEqual(len(notes), 6)
                self.assertTrue(all(isinstance(v, int) and 24 <= v <= 96 for v in notes))

    def test_standard(self):
        self.assertEqual(STANDARD_MIDI, (64, 59, 55, 50, 45, 40))
        self.assertEqual([note_at(STANDARD_MIDI, r, 0) for r in range(6)],
                         ['E', 'B', 'G', 'D', 'A', 'E'])
        self.assertEqual(pitch_at(STANDARD_MIDI, 5, 12), 52)
        self.assertEqual(pitch_at(STANDARD_MIDI, 5, 5), pitch_at(STANDARD_MIDI, 4, 0))

    def test_drop_d_has_correct_pitch(self):
        drop_d = TUNINGS['Drop D (D A D G B E)']
        self.assertEqual(drop_d[5], 38)
        self.assertEqual(drop_d[:5], STANDARD_MIDI[:5])
        self.assertEqual(note_at(drop_d, 5, 0), 'D')
        self.assertEqual(note_at(drop_d, 5, 2), 'E')

    def test_drop_c_has_correct_pitch(self):
        drop_c = TUNINGS['Drop C (C G C F A D)']
        self.assertEqual(drop_c, (62, 57, 53, 48, 43, 36))
        self.assertEqual(note_at(drop_c, 5, 3), 'D♯')

    def test_enharmonic_labels(self):
        self.assertIn('E♭', midi_label(63))
        self.assertEqual(readable_note(3, prefer_flats=True), 'E♭ (Ми♭)')

    def test_custom_string_pitch(self):
        custom = (62, 58, 55, 50, 43, 36)
        self.assertEqual(pitch_at(custom, 0, 2), 64)
        self.assertEqual(note_at(custom, 5, 2), 'D')
        with self.assertRaises(ValueError):
            pitch_at((64,), 0, 0)
        with self.assertRaises(ValueError):
            pitch_at(custom, 6, 0)

    def test_quiz_pool_honors_new_tuning(self):
        app = NoteTrainer.__new__(NoteTrainer)
        app.active_strings, app.active_frets, app.question_count, app.mode = 1, 3, 10, 'find'
        app.tuning = TUNINGS['Drop D (D A D G B E)']
        self.assertEqual(app._pitch_class(5, 0), 2)
        self.assertEqual(app._pitch_class(5, 2), 4)
        questions = app._make_questions()
        self.assertTrue(all(q.row == 5 and q.fret <= 3 for q in questions))

    def test_settings_roundtrip_and_corrupt_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'settings.json'
            self.assertEqual(read_settings(path), (next(iter(TUNINGS)), STANDARD_MIDI, 65))
            custom = (64, 60, 55, 50, 45, 38)
            write_settings(path, CUSTOM_TUNING, custom, 41)
            self.assertEqual(read_settings(path), (CUSTOM_TUNING, custom, 41))
            self.assertEqual(json.loads(path.read_text())['schema_version'], 1)
            path.write_text('not json')
            self.assertEqual(read_settings(path)[1], STANDARD_MIDI)

    def test_preset_not_overridden_by_stale_custom_values(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'settings.json'
            write_settings(path, 'Drop D (D A D G B E)', STANDARD_MIDI, 78)
            name, tuning, volume = read_settings(path)
            self.assertEqual(tuning, TUNINGS[name])
            self.assertEqual(volume, 78)


class Audio(unittest.TestCase):
    def test_equal_temperament(self):
        self.assertAlmostEqual(midi_frequency(69), 440)
        self.assertAlmostEqual(midi_frequency(40), 82.406889, places=5)
        self.assertAlmostEqual(midi_frequency(52), midi_frequency(40)*2, places=4)

    def test_wav_is_mono_pcm_and_nonempty(self):
        b = synthesize_string(40, volume=0.6, duration=0.2)
        with wave.open(io.BytesIO(b), 'rb') as wav:
            self.assertEqual(wav.getnchannels(), 1)
            self.assertEqual(wav.getsampwidth(), 2)
            self.assertEqual(wav.getframerate(), SAMPLE_RATE)
            self.assertEqual(wav.getnframes(), round(SAMPLE_RATE*0.2))
            self.assertNotEqual(wav.readframes(500), b'\x00' * 1000)

    def test_buzz_duration_and_distinct_sound(self):
        clean = synthesize_string(60, duration=0.55)
        buzz = synthesize_string(60, duration=0.55, buzzing=True)
        self.assertNotEqual(clean, buzz)
        self.assertEqual(len(clean), len(buzz))

    def test_zero_volume_silence(self):
        b = synthesize_string(60, volume=0, duration=0.1)
        with wave.open(io.BytesIO(b), 'rb') as w:
            self.assertEqual(set(w.readframes(w.getnframes())), {0})

    def test_player_no_sound_when_muted(self):
        p = AudioPlayer(volume=0)
        try:
            self.assertFalse(p.play(40))
        finally:
            p.close()

    def test_reject_invalid_audio_inputs(self):
        for kwargs in [dict(midi_note=-1), dict(midi_note=128), dict(midi_note=60, volume=1.1),
                       dict(midi_note=60, duration=0.01)]:
            with self.subTest(args=kwargs), self.assertRaises(ValueError):
                synthesize_string(**kwargs)


if __name__ == '__main__':
    unittest.main()
