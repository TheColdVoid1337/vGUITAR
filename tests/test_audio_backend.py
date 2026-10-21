"""Native Windows playback plumbing without requiring Windows or a speaker."""
import ctypes
import io
import sys
import threading
import unittest
from unittest.mock import Mock, patch
import wave

from vguitar_audio import AudioPlayer, _play_waveout, synthesize_string


class FakeWinmm:
    def __init__(self, open_error=0):
        self.calls = []
        self.open_error = open_error
        self.waveOutOpen = Mock(side_effect=self._open)
        self.waveOutPrepareHeader = Mock(side_effect=self._prepare)
        self.waveOutWrite = Mock(side_effect=self._write)
        self.waveOutReset = Mock(return_value=0)
        self.waveOutUnprepareHeader = Mock(return_value=0)
        self.waveOutClose = Mock(return_value=0)

    def _open(self, ptr, device, fmt_ptr, *args):
        self.calls.append("open")
        if not self.open_error:
            ptr._obj.value = 321
            fmt = fmt_ptr._obj
            assert fmt.nChannels == 1 and fmt.wBitsPerSample == 16
            assert fmt.nSamplesPerSec == 22050
        return self.open_error

    def _prepare(self, *args):
        self.calls.append("prepare")
        return 0

    def _write(self, handle, header_ptr, size):
        self.calls.append("write")
        header_ptr._obj.dwFlags = 1  # Simulate WHDR_DONE after hardware playback.
        return 0


class TestAudioBackend(unittest.TestCase):
    def test_winmm_native_pcm_lifecycle(self):
        fake = FakeWinmm()
        wav = synthesize_string(40, duration=0.1)
        with patch.object(sys, "platform", "win32"), patch.object(ctypes, "WinDLL", return_value=fake, create=True):
            _play_waveout(wav, threading.Event())
        self.assertEqual(fake.calls, ["open", "prepare", "write"])
        self.assertEqual(fake.waveOutUnprepareHeader.call_count, 1)
        self.assertEqual(fake.waveOutClose.call_count, 1)

    def test_waveout_error_contains_native_code(self):
        fake = FakeWinmm(open_error=4)
        with patch.object(sys, "platform", "win32"), patch.object(ctypes, "WinDLL", return_value=fake, create=True):
            with self.assertRaisesRegex(RuntimeError, "waveOutOpen.*4"):
                _play_waveout(synthesize_string(40, duration=0.1), threading.Event())
        self.assertEqual(fake.waveOutClose.call_count, 0)

    def test_winmm_worker_falls_back_to_winsound(self):
        obj = AudioPlayer(volume=60)
        try:
            obj._backend = "waveout"
            with patch("vguitar_audio._play_waveout", side_effect=RuntimeError("native failure")), \
                 patch.object(obj, "_winsound") as fallback:
                obj._play_windows_worker(synthesize_string(40, duration=0.1), threading.Event())
            fallback.assert_called_once()
            self.assertEqual(obj.last_used_backend, "winsound-fallback")
            self.assertIn("native failure", obj.last_error)
        finally:
            obj.close()

    def test_fallback_diagnostic_when_both_backends_fail(self):
        obj = AudioPlayer(volume=65)
        try:
            obj._backend = "waveout"
            with patch("vguitar_audio._play_waveout", side_effect=RuntimeError("primary")), \
                 patch.object(obj, "_winsound", side_effect=RuntimeError("fallback")):
                obj._play_windows_worker(synthesize_string(40, duration=0.1), threading.Event())
            self.assertEqual(obj.last_result, "error")
            self.assertIn("primary", obj.diagnostic())
            self.assertIn("fallback", obj.diagnostic())
        finally:
            obj.close()

    def test_volume_zero_reports_muted(self):
        obj = AudioPlayer(volume=0)
        try:
            self.assertFalse(obj.play(40))
            self.assertIn("muted", obj.diagnostic())
        finally:
            obj.close()


if __name__ == "__main__":
    unittest.main()
