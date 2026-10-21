"""Offline guitar-string sound synthesis and system audio playback.

Windows uses native WinMM waveOut PCM first, with winsound as a fallback.
Other platforms use available system players. No third-party Python modules.
"""
from __future__ import annotations

import array
import ctypes
import io
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave

SAMPLE_RATE = 22050


def midi_frequency(midi_note: int) -> float:
    """Equal temperament, A4 = 440 Hz."""
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def synthesize_string(midi_note: int, volume: float = 0.65,
                      duration: float = 1.55, buzzing: bool = False) -> bytes:
    """Render a deterministic guitar-like pluck / damped fret-buzz as PCM WAV."""
    if not 0 <= midi_note <= 127:
        raise ValueError("MIDI pitch must be 0..127")
    if not 0.0 <= volume <= 1.0:
        raise ValueError("Volume must be in 0..1")
    if not 0.1 <= duration <= 5.0:
        raise ValueError("Duration out of range")

    freq = midi_frequency(midi_note)
    if buzzing:
        duration = min(duration, 0.60)
    count = round(SAMPLE_RATE * duration)
    rng = random.Random(midi_note * 37 + (3 if buzzing else 1))
    nyquist = SAMPLE_RATE / 2
    partials = min(12, max(1, int(nyquist // freq) - 1))
    harmonics = [(h, (1.0 / (h ** 1.27)) * (0.75 if h % 4 == 0 else 1.0))
                 for h in range(1, partials + 1)]
    values = array.array('h')
    for i in range(count):
        t = i / SAMPLE_RATE
        attack = min(1.0, t / 0.004)
        decay = math.exp(-t * (1.50 if freq < 180 else 2.15))
        sample = 0.0
        for h, strength in harmonics:
            sample += strength * math.sin(2 * math.pi * freq * h * t) * math.exp(-t * h * 0.55)
        sample *= 0.40 * attack * decay
        sample += (rng.random() * 2 - 1) * 0.052 * math.exp(-t * 46)
        if buzzing:
            sample *= math.exp(-t * 14.0)
            buzz_gate = max(0.0, math.sin(2 * math.pi * 78.0 * t))
            buzz_env = math.exp(-t * 7.0)
            sample += (rng.random() * 2 - 1) * 0.20 * buzz_gate * buzz_env
            sample += 0.12 * math.sin(2 * math.pi * min(freq * 1.018, nyquist - 100) * t) * buzz_env
        sample = math.tanh(sample * 1.45)
        fade = min(1.0, (duration - t) / 0.025)
        values.append(int(max(-1.0, min(1.0, sample * volume * fade)) * 32767))

    output = io.BytesIO()
    with wave.open(output, 'wb') as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        out.writeframes(values.tobytes())
    return output.getvalue()


class AudioPlaybackError(RuntimeError):
    """Native audio playback failed; includes WinMM error number when possible."""


def _play_waveout(wav: bytes, stop_event: threading.Event) -> None:
    """Stream PCM through native Windows waveOut. Blocks only a worker thread.

    Unlike SND_ASYNC file playback this path reports native device errors and
    does not depend on the Windows sound-event configuration or file association.
    The PCM memory and WAVEHDR stay alive until the driver marks completion.
    """
    if sys.platform != "win32":
        raise AudioPlaybackError("waveOut requires Windows")
    from ctypes import wintypes

    class WaveFormatEx(ctypes.Structure):
        _fields_ = [("wFormatTag", wintypes.WORD),
                    ("nChannels", wintypes.WORD),
                    ("nSamplesPerSec", wintypes.DWORD),
                    ("nAvgBytesPerSec", wintypes.DWORD),
                    ("nBlockAlign", wintypes.WORD),
                    ("wBitsPerSample", wintypes.WORD),
                    ("cbSize", wintypes.WORD)]

    class WaveHeader(ctypes.Structure):
        _fields_ = [("lpData", ctypes.c_void_p),
                    ("dwBufferLength", wintypes.DWORD),
                    ("dwBytesRecorded", wintypes.DWORD),
                    ("dwUser", ctypes.c_size_t),
                    ("dwFlags", wintypes.DWORD),
                    ("dwLoops", wintypes.DWORD),
                    ("lpNext", ctypes.c_void_p),
                    ("reserved", ctypes.c_size_t)]

    winmm = ctypes.WinDLL("winmm")
    winmm.waveOutOpen.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint,
                                  ctypes.POINTER(WaveFormatEx), ctypes.c_size_t,
                                  ctypes.c_size_t, ctypes.c_uint]
    for name in ("waveOutPrepareHeader", "waveOutWrite", "waveOutUnprepareHeader"):
        getattr(winmm, name).argtypes = [ctypes.c_void_p,
                                         ctypes.POINTER(WaveHeader), ctypes.c_uint]
    winmm.waveOutReset.argtypes = [ctypes.c_void_p]
    winmm.waveOutClose.argtypes = [ctypes.c_void_p]

    with wave.open(io.BytesIO(wav), "rb") as data:
        channels, bits, rate = data.getnchannels(), data.getsampwidth() * 8, data.getframerate()
        pcm = data.readframes(data.getnframes())
    if channels != 1 or bits != 16:
        raise AudioPlaybackError("Expected mono 16-bit PCM WAV")
    fmt = WaveFormatEx(1, channels, rate, rate * channels * (bits // 8),
                       channels * (bits // 8), bits, 0)
    handle = ctypes.c_void_p()
    error = winmm.waveOutOpen(ctypes.byref(handle), 0xFFFFFFFF,
                              ctypes.byref(fmt), 0, 0, 0)
    if error:
        raise AudioPlaybackError(f"waveOutOpen: Windows MMRESULT {error}")
    prepared = False
    try:
        pcm_buffer = ctypes.create_string_buffer(pcm)
        header = WaveHeader(ctypes.cast(pcm_buffer, ctypes.c_void_p),
                            len(pcm), 0, 0, 0, 0, None, 0)
        header_size = ctypes.sizeof(header)
        error = winmm.waveOutPrepareHeader(handle, ctypes.byref(header), header_size)
        if error:
            raise AudioPlaybackError(f"waveOutPrepareHeader: Windows MMRESULT {error}")
        prepared = True
        error = winmm.waveOutWrite(handle, ctypes.byref(header), header_size)
        if error:
            raise AudioPlaybackError(f"waveOutWrite: Windows MMRESULT {error}")
        duration = len(pcm) / fmt.nAvgBytesPerSec
        deadline = time.monotonic() + duration + 2.0
        while not (header.dwFlags & 0x1):  # WHDR_DONE = 0x00000001
            if stop_event.wait(0.025):
                break
            if time.monotonic() > deadline:
                raise AudioPlaybackError("waveOut: timeout waiting for playback")
    finally:
        # Reset makes the header safe to unprepare even when playback interrupted.
        winmm.waveOutReset(handle)
        if prepared:
            winmm.waveOutUnprepareHeader(handle, ctypes.byref(header), ctypes.sizeof(header))
        winmm.waveOutClose(handle)


class AudioPlayer:
    """Non-blocking sound cues with inspectable playback status."""

    def __init__(self, volume: int = 65) -> None:
        self.volume = max(0, min(100, int(volume)))
        self._dir = tempfile.TemporaryDirectory(prefix="vguitar_audio_")
        self._file = Path(self._dir.name) / "note.wav"
        self._process = None
        self._stop_event: threading.Event | None = None
        self._worker: threading.Thread | None = None
        self._backend = self._select_backend()
        self.last_error = "" if self._backend else "Нет доступного аудиоплеера"
        self.last_result = "idle"
        self.last_used_backend = self._backend or "none"

    @staticmethod
    def _select_backend() -> str | None:
        if sys.platform == "win32":
            try:
                ctypes.WinDLL("winmm")
                return "waveout"
            except (OSError, AttributeError):
                try:
                    import winsound  # noqa: F401
                    return "winsound"
                except ImportError:
                    return None
        if sys.platform == "darwin" and shutil.which("afplay"):
            return "afplay"
        for name in ("ffplay", "paplay", "aplay"):
            if shutil.which(name):
                return name
        return None

    @property
    def available(self) -> bool:
        return self._backend is not None

    def diagnostic(self) -> str:
        """Short text suitable for copying into a troubleshooting chat."""
        device_count = "n/a"
        if sys.platform == "win32":
            try:
                device_count = str(ctypes.WinDLL("winmm").waveOutGetNumDevs())
            except (OSError, AttributeError):
                device_count = "unknown"
        return (f"platform={sys.platform}; backend={self._backend or 'none'}; "
                f"used={self.last_used_backend}; devices={device_count}; "
                f"volume={self.volume}; result={self.last_result}; "
                f"error={self.last_error or 'none'}")

    def _winsound(self, wav: bytes) -> None:
        import winsound
        # A new WAV filename avoids racing a still-open async previous sound.
        path = Path(self._dir.name) / f"cue_{time.monotonic_ns()}.wav"
        path.write_bytes(wav)
        winsound.PlaySound(str(path), winsound.SND_FILENAME |
                           winsound.SND_ASYNC | winsound.SND_NODEFAULT)

    def _play_windows_worker(self, wav: bytes, stop_event: threading.Event) -> None:
        try:
            if stop_event.is_set():
                return
            if self._backend == "waveout":
                try:
                    _play_waveout(wav, stop_event)
                    if not stop_event.is_set():
                        self.last_result, self.last_error = "played", ""
                    return
                except (AudioPlaybackError, OSError, AttributeError, RuntimeError) as err:
                    first_error = str(err)
                    if stop_event.is_set():
                        return
                    try:
                        self._winsound(wav)
                        self.last_used_backend = "winsound-fallback"
                        self.last_result = "started"
                        self.last_error = f"Primary waveOut failed: {first_error}"
                        return
                    except (OSError, RuntimeError, ImportError) as secondary:
                        raise AudioPlaybackError(f"waveOut: {first_error}; winsound: {secondary}")
            else:
                self._winsound(wav)
                self.last_result, self.last_error = "started", ""
        except (AudioPlaybackError, OSError, RuntimeError) as exc:
            if not stop_event.is_set():
                self.last_result, self.last_error = "error", str(exc)

    def play(self, midi_note: int, buzzing: bool = False) -> bool:
        if self.volume == 0:
            self.last_result, self.last_error = "muted", "Volume is 0%"
            return False
        if not self.available:
            self.last_result, self.last_error = "unavailable", "No audio output backend"
            return False
        self.stop()
        try:
            wav = synthesize_string(midi_note, volume=self.volume / 100,
                                    duration=0.55 if buzzing else 1.55, buzzing=buzzing)
            self.last_result, self.last_error = "starting", ""
            self.last_used_backend = self._backend
            if self._backend in ("waveout", "winsound"):
                event = threading.Event()
                self._stop_event = event
                self._worker = threading.Thread(target=self._play_windows_worker,
                                                args=(wav, event), daemon=True)
                self._worker.start()
            else:
                self._file.write_bytes(wav)
                command = {
                    "afplay": ["afplay", str(self._file)],
                    "ffplay": ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(self._file)],
                    "paplay": ["paplay", str(self._file)],
                    "aplay": ["aplay", "-q", str(self._file)],
                }[self._backend]
                self._process = subprocess.Popen(command, stdout=subprocess.DEVNULL,
                                                 stderr=subprocess.DEVNULL)
                self.last_result = "started"
            return True
        except (OSError, ValueError, RuntimeError) as exc:
            self.last_result, self.last_error = "error", str(exc)
            return False

    def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
            self._stop_event = None
        if self._process is not None:
            if self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=0.3)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait(timeout=0.3)
            self._process = None
        if self._backend in ("waveout", "winsound") and sys.platform == "win32":
            try:
                import winsound
                winsound.PlaySound(None, 0)
            except (ImportError, OSError, RuntimeError):
                pass

    def close(self) -> None:
        self.stop()
        # Native waveOut workers need to finish releasing handles before temp cleanup.
        if self._worker is not None and self._worker.is_alive():
            self._worker.join(timeout=2.5)
        self._dir.cleanup()
