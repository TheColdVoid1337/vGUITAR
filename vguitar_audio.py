"""Offline guitar-string sound synthesis and system audio playback.

On Windows uses PortAudio (sounddevice) with WASAPI priority, as in TittyTatter.
Other platforms retain available OS players. On Windows install sounddevice.
"""
from __future__ import annotations

import array
import io
import math
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import wave
from typing import Any

SAMPLE_RATE = 22050


def midi_frequency(midi_note: int) -> float:
    """Equal temperament, A4 = 440 Hz."""
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def synthesize_string(midi_note: int, volume: float = 0.65,
                      duration: float = 1.55, buzzing: bool = False,
                      sample_rate: int = SAMPLE_RATE) -> bytes:
    """Render a soft, pitched guitar pluck or a short dead-fret buzz.

    Adapt TittyTatter's harmonic strengths (fundamental + 2nd..5th harmonics)
    for a sustained NOTE instead of its very short rhythm-game hit.  A lightly
    damped Karplus-Strong string adds organic motion; neither normal notes nor
    the note-test button use a separate percussive noise burst.

    This stays deterministic, standard-library-only, and pitch-aware for the
    selected string, fret and tuning.  The audio backend is unchanged (WASAPI).
    """
    if not 0 <= midi_note <= 127:
        raise ValueError("MIDI pitch must be 0..127")
    if not 0.0 <= volume <= 1.0:
        raise ValueError("Volume must be in 0..1")
    if not 0.1 <= duration <= 5.0:
        raise ValueError("Duration out of range")
    if not 8000 <= sample_rate <= 192000:
        raise ValueError("Unsupported sample rate")

    freq = midi_frequency(midi_note)
    if buzzing:
        duration = min(duration, 0.48)
    count = round(sample_rate * duration)
    rng = random.Random(73 * midi_note + (11 if buzzing else 5))
    nyquist = sample_rate / 2
    strengths = ((1, 1.0), (2, .48), (3, .26), (4, .14), (5, .08))
    harmonics = [(h, gain) for h, gain in strengths if h * freq < nyquist * .90]

    # Low-pass the initial string displacement: a hard white-noise excitation
    # sounds like percussion.  Subtract the DC offset before starting the loop.
    delay_size = max(8, round(sample_rate / freq - .5))
    displacement = []
    previous = 0.0
    for _ in range(delay_size):
        previous = .81 * previous + .19 * rng.uniform(-1, 1)
        displacement.append(previous)
    avg = sum(displacement) / len(displacement)
    displacement = [v - avg for v in displacement]
    peak = max(1e-6, max(abs(v) for v in displacement))
    displacement = [v / peak for v in displacement]
    cursor = 0

    values = array.array('h')
    for i in range(count):
        t = i / sample_rate
        if buzzing:
            # A wrongly fretted string: recognisable pitch, fast mute, fine rattle.
            body = sum(g * math.sin(2 * math.pi * freq * h * t)
                       for h, g in harmonics)
            # Subtle audible fret chatter instead of a loud percussion click.
            rattle = .065 * (rng.random() * 2 - 1) * max(
                0.0, math.sin(2 * math.pi * 66 * t))
            attack = min(1.0, t / .006)
            sound = (body * .46 + rattle) * math.exp(-t / .085) * attack
        else:
            # Natural short-lived pick followed by the longer ringing string.
            # Smoothstep fades the first 12ms without a hard transient.
            x = min(1.0, t / .012)
            attack = x * x * (3 - 2 * x)
            body = sum(g * math.sin(2 * math.pi * freq * h * t) *
                       math.exp(-t * (.20 + .35 * h))
                       for h, g in harmonics)
            pluck = displacement[cursor]
            after = displacement[(cursor + 1) % delay_size]
            displacement[cursor] = .996 * .5 * (pluck + after)
            cursor = (cursor + 1) % delay_size
            string_decay = math.exp(-t / (2.2 if freq < 200 else 1.5))
            sound = attack * (.52 * body + .21 * pluck * string_decay)
        fade_out = min(1.0, max(0.0, (duration - t) / .040))
        sample = math.tanh(sound * 1.20) * volume * fade_out
        values.append(int(max(-1.0, min(1.0, sample)) * 32767))

    if sys.byteorder != 'little':
        values.byteswap()
    output = io.BytesIO()
    with wave.open(output, 'wb') as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(sample_rate)
        out.writeframes(values.tobytes())
    return output.getvalue()



class AudioPlaybackError(RuntimeError):
    """Audio driver error with an actionable message for diagnostics."""


def find_output_devices(sd: Any) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Prefer WASAPI's default output, then WASAPI speakers, then PortAudio default.

    Matches TittyTatter's sounddevice/PortAudio WASAPI device discovery.
    Returns a list for diagnostics, even when no output is available.
    """
    devices = sd.query_devices()
    apis = sd.query_hostapis()
    results: list[dict[str, Any]] = []
    for i, device in enumerate(devices):
        if int(device.get('max_output_channels', 0)) < 1:
            continue
        host = int(device.get('hostapi', -1))
        host_name = str(apis[host].get('name', 'unknown')) if 0 <= host < len(apis) else 'unknown'
        results.append({
            'index': i, 'name': str(device.get('name', 'unknown')),
            'hostapi': host_name,
            'samplerate': int(round(float(device.get('default_samplerate', 48000)))) or 48000,
            'channels': 2 if int(device.get('max_output_channels', 0)) >= 2 else 1,
            'wasapi': 'WASAPI' in host_name.upper(),
        })
    for host in apis:
        if 'WASAPI' in str(host.get('name', '')).upper():
            idx = int(host.get('default_output_device', -1))
            item = next((x for x in results if x['index'] == idx and x['wasapi']), None)
            if item:
                return results, item
    wasapi = next((x for x in results if x['wasapi']), None)
    if wasapi:
        return results, wasapi
    try:
        idx = int(sd.default.device[1])
    except (AttributeError, TypeError, ValueError, IndexError):
        idx = -1
    fallback = next((x for x in results if x['index'] == idx), None)
    return results, fallback or (results[0] if results else None)


def _stereo_pcm(mono_pcm: bytes, channels: int) -> bytes:
    """Expand little-endian 16-bit mono to dual-channel PCM without numpy."""
    if channels == 1:
        return mono_pcm
    if channels != 2:
        raise AudioPlaybackError(f'Unsupported channel count: {channels}')
    frames = array.array('h')
    frames.frombytes(mono_pcm)
    if sys.byteorder != 'little':
        frames.byteswap()
    output = array.array('h', (item for sample in frames for item in (sample, sample)))
    if sys.byteorder != 'little':
        output.byteswap()
    return output.tobytes()


def play_portaudio_pcm(sd: Any, pcm: bytes, device: dict[str, Any],
                       stop_event: threading.Event) -> None:
    """Blocking PortAudio writes in a worker: never blocks Tk's event loop.

    The device's native sample rate is used to avoid WASAPI format mismatch.
    A new stream per cue avoids process-global Windows mixer configuration.
    """
    stream = None
    try:
        stream = sd.RawOutputStream(
            samplerate=device['samplerate'], channels=device['channels'],
            dtype='int16', device=device['index'], blocksize=0,
            latency='high',
        )
        stream.start()
        bytes_per_frame = device['channels'] * 2
        chunk = 1024 * bytes_per_frame
        for offset in range(0, len(pcm), chunk):
            if stop_event.is_set():
                break
            stream.write(pcm[offset:offset + chunk])
        if stop_event.is_set():
            stream.abort()
        else:
            stream.stop()  # Drain the final queued frames before reporting played.
    finally:
        if stream is not None:
            stream.close()


class AudioPlayer:
    """Nonblocking audio with WASAPI device discovery and truthful diagnostics."""

    def __init__(self, volume: int = 65) -> None:
        self.volume = max(0, min(100, int(volume)))
        self._stop_event: threading.Event | None = None
        self._worker: threading.Thread | None = None
        self._process: subprocess.Popen | None = None
        self._backend = None
        self._sd = None
        self._device: dict[str, Any] | None = None
        self.device_name = 'none'
        self.host_api_name = 'none'
        self.available_devices: list[dict[str, Any]] = []
        self.last_used_backend = 'none'
        self.last_result = 'idle'
        self.last_error = ''
        self._lock = threading.Lock()
        self._init_backend()

    def _init_backend(self) -> None:
        if sys.platform == 'win32':
            try:
                import sounddevice as sd
            except (ImportError, OSError) as exc:
                self.last_error = f'sounddevice/PortAudio unavailable: {exc}. Run RUN.bat or pip install -r requirements.txt'
                return
            self._sd = sd
            try:
                self.available_devices, self._device = find_output_devices(sd)
            except Exception as exc:
                self.last_error = f'Cannot enumerate PortAudio devices: {exc}'
                return
            if self._device is None:
                self.last_error = 'PortAudio found no output device; check Windows Sound settings'
                return
            self.device_name = self._device['name']
            self.host_api_name = self._device['hostapi']
            self._backend = 'wasapi' if self._device['wasapi'] else 'portaudio'
            self.last_used_backend = self._backend
            return
        if sys.platform == 'darwin' and shutil.which('afplay'):
            self._backend = 'afplay'
        else:
            self._backend = next((name for name in ('ffplay', 'paplay', 'aplay')
                                  if shutil.which(name)), None)
        self.last_used_backend = self._backend or 'none'
        if self._backend is None:
            self.last_error = 'No system audio player found'

    @property
    def available(self) -> bool:
        return self._backend is not None

    def diagnostic(self) -> str:
        selected = self._device
        device_desc = ('n/a' if selected is None else
                       f"{selected['index']}:{selected['name']} ({selected['hostapi']}, "
                       f"{selected['samplerate']} Hz, {selected['channels']}ch)")
        detected = ', '.join(f"{d['index']}:{d['name']} [{d['hostapi']}]"
                             for d in self.available_devices)
        return (f'platform={sys.platform}; backend={self._backend or "none"}; '
                f'used={self.last_used_backend}; device={device_desc}; '
                f'outputs={detected or "none"}; volume={self.volume}; '
                f'result={self.last_result}; error={self.last_error or "none"}')

    def _publish(self, event: threading.Event, result: str, error: str = '', used: str | None = None) -> None:
        with self._lock:
            if self._stop_event is event and not event.is_set():
                self.last_result, self.last_error = result, error
                if used:
                    self.last_used_backend = used

    def _play_windows(self, note: int, volume: float, buzzing: bool,
                      event: threading.Event) -> None:
        try:
            if event.is_set():
                return
            assert self._sd is not None and self._device is not None
            active_device = self._device
            # Generate matching the actual WASAPI mix rate, not 22050 Hz.
            wav = synthesize_string(note, volume=volume,
                                    duration=0.55 if buzzing else 1.55, buzzing=buzzing,
                                    sample_rate=active_device['samplerate'])
            with wave.open(io.BytesIO(wav), 'rb') as source:
                pcm = source.readframes(source.getnframes())
            pcm = _stereo_pcm(pcm, active_device['channels'])
            if event.is_set():
                return
            self._publish(event, 'playing')
            play_portaudio_pcm(self._sd, pcm, active_device, event)
            if not event.is_set():
                self._publish(event, 'played', used=self._backend)
        except Exception as exc:
            self._publish(event, 'error', f'{type(exc).__name__}: {exc}', used=self._backend)

    def _play_other(self, note: int, volume: float, buzzing: bool,
                    event: threading.Event) -> None:
        try:
            wav = synthesize_string(note, volume=volume,
                                    duration=0.55 if buzzing else 1.55, buzzing=buzzing)
            if event.is_set():
                return
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                path = Path(tmp.name)
                path.write_bytes(wav)
            try:
                cmd = {
                    'afplay': ['afplay', str(path)],
                    'ffplay': ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', str(path)],
                    'paplay': ['paplay', str(path)],
                    'aplay': ['aplay', '-q', str(path)],
                }[self._backend]
                process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                self._process = process
                _stdout, stderr = process.communicate()
                if process.returncode != 0:
                    raise AudioPlaybackError(f'{self._backend} exited {process.returncode}: {stderr.decode(errors="replace")[:150]}')
                self._publish(event, 'played')
            finally:
                path.unlink(missing_ok=True)
        except Exception as exc:
            self._publish(event, 'error', str(exc))

    def play(self, midi_note: int, buzzing: bool = False) -> bool:
        if self.volume == 0:
            self.last_result, self.last_error = 'muted', 'Volume is 0%'
            return False
        if not self.available:
            self.last_result, self.last_error = 'unavailable', self.last_error or 'No audio device'
            return False
        if not isinstance(midi_note, int) or not 0 <= midi_note <= 127:
            self.last_result, self.last_error = 'error', f'Invalid MIDI note: {midi_note}'
            return False
        self.stop()
        event = threading.Event()
        with self._lock:
            self._stop_event = event
            self.last_result, self.last_error = 'starting', ''
            self.last_used_backend = self._backend or 'none'
        target = self._play_windows if sys.platform == 'win32' else self._play_other
        worker = threading.Thread(target=target, args=(midi_note, self.volume / 100.0, buzzing, event), daemon=True)
        self._worker = worker
        worker.start()
        return True

    def stop(self) -> None:
        with self._lock:
            previous = self._stop_event
            self._stop_event = None
        if previous is not None:
            previous.set()
        proc = self._process
        if proc is not None and proc.poll() is None:
            proc.terminate()
        self._process = None

    def close(self) -> None:
        self.stop()
        if self._worker is not None and self._worker.is_alive():
            self._worker.join(timeout=2.0)
