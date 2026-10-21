"""Small offline plucked-string audio engine using Python's standard library.

The timbre is synthesized, not a recording of an acoustic/electric guitar.
Audio playback uses OS tools (winsound, afplay, ffplay/aplay/paplay) if available.
"""
from __future__ import annotations

import array
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import wave

SAMPLE_RATE = 22050


def midi_frequency(midi_note: int) -> float:
    """Equal temperament, A4 = 440 Hz."""
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def synthesize_string(midi_note: int, volume: float = 0.65,
                      duration: float = 1.55, buzzing: bool = False) -> bytes:
    """Render a guitar-like pluck or a short muted/fret-buzz sound as PCM WAV.

    Volume 0.0..1.0; note is real concert-pitch MIDI incl. string octave.
    Deterministic output supports tests and repeatable audio cues.
    """
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
    # A plucked-string approximation with a slightly noisy plectrum attack.
    values = array.array('h')
    for i in range(count):
        t = i / SAMPLE_RATE
        attack = min(1.0, t / 0.004)
        decay = math.exp(-t * (1.50 if freq < 180 else 2.15))
        sample = 0.0
        for h, strength in harmonics:
            # High harmonics damp more quickly on a real vibrating string.
            sample += strength * math.sin(2 * math.pi * freq * h * t) * math.exp(-t * h * 0.55)
        sample *= 0.40 * attack * decay
        sample += (rng.random() * 2 - 1) * 0.052 * math.exp(-t * 46)
        if buzzing:
            # A clipped/dead string: rapid damping, fret-rattle and a rasping buzz.
            sample *= math.exp(-t * 14.0)
            buzz_gate = max(0.0, math.sin(2 * math.pi * 78.0 * t))
            buzz_env = math.exp(-t * 7.0)
            sample += (rng.random() * 2 - 1) * 0.20 * buzz_gate * buzz_env
            sample += 0.12 * math.sin(2 * math.pi * min(freq * 1.018, nyquist - 100) * t) * buzz_env
        # Gentle saturation prevents harsh digital clipping on loud chords.
        sample = math.tanh(sample * 1.45)
        fade = min(1.0, (duration - t) / 0.025)
        values.append(int(max(-1.0, min(1.0, sample * volume * fade)) * 32767))

    import io
    output = io.BytesIO()
    with wave.open(output, 'wb') as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        out.writeframes(values.tobytes())
    return output.getvalue()


class AudioPlayer:
    """Best-effort non-blocking audio. No pip packages are required."""

    def __init__(self, volume: int = 65) -> None:
        self.volume = max(0, min(100, int(volume)))
        self._dir = tempfile.TemporaryDirectory(prefix="vguitar_audio_")
        self._file = Path(self._dir.name) / "note.wav"
        self._process = None
        self._backend = self._select_backend()
        self.last_error = "" if self._backend else "Нет доступного системного аудиоплеера"

    @staticmethod
    def _select_backend() -> str | None:
        if sys.platform == "win32":
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

    def play(self, midi_note: int, buzzing: bool = False) -> bool:
        if self.volume == 0 or not self.available:
            return False
        try:
            # Stop previous cue; quick answers do not play overlapping notes.
            self.stop()
            wav = synthesize_string(midi_note, volume=self.volume / 100,
                                    duration=0.55 if buzzing else 1.55, buzzing=buzzing)
            self._file.write_bytes(wav)
            if self._backend == "winsound":
                import winsound
                winsound.PlaySound(str(self._file), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            else:
                command = {
                    "afplay": ["afplay", str(self._file)],
                    "ffplay": ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(self._file)],
                    "paplay": ["paplay", str(self._file)],
                    "aplay": ["aplay", "-q", str(self._file)],
                }[self._backend]
                self._process = subprocess.Popen(command, stdout=subprocess.DEVNULL,
                                                 stderr=subprocess.DEVNULL)
            self.last_error = ""
            return True
        except (OSError, ValueError) as exc:
            self.last_error = str(exc)
            return False

    def stop(self) -> None:
        if self._process is not None:
            if self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=0.3)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait(timeout=0.3)
            self._process = None
        if self._backend == "winsound":
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except (OSError, RuntimeError):
                pass

    def close(self) -> None:
        self.stop()
        self._dir.cleanup()
