"""Offline guitar-string sound synthesis and system audio playback.

On Windows uses PortAudio (sounddevice) with WASAPI priority, as in TittyTatter.
Other platforms retain available OS players. On Windows install sounddevice.
"""
from __future__ import annotations

import array
from collections import OrderedDict
import io
import math
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
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
            'id': f"{host_name}|{device.get('name', 'unknown')}",
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


class PersistentCueStream:
    """A single long-lived PortAudio/WASAPI stream; no device churn per note.

    RawOutputStream's callback only copies already rendered PCM.  Rendering and
    filesystem work always happen outside the realtime audio callback.
    """

    FADE_MS = 18

    def __init__(self, sd: Any, device: dict[str, Any], *, latency: str = 'high',
                 blocksize: int = 0, exclusive: bool = False) -> None:
        self.device = device
        self.channels = int(device['channels'])
        self.rate = int(device['samplerate'])
        self._lock = threading.Lock()
        self._pcm: bytes | None = None
        self._position = 0
        self._tail: bytes | None = None
        self._tail_pos = 0
        self._tail_frame = 0
        self._fade_frames = max(1, round(self.rate * self.FADE_MS / 1000))
        self.callback_flags: list[str] = []
        self.callback_count = 0
        self.underflows = 0
        extras = None
        if exclusive and device['wasapi']:
            extras = sd.WasapiSettings(exclusive=True)
        self._stream = sd.RawOutputStream(
            device=device['index'], samplerate=self.rate,
            channels=self.channels, dtype='int16',
            latency=latency, blocksize=blocksize, callback=self._callback,
            extra_settings=extras,
        )
        try:
            self._stream.start()
        except Exception:
            self._stream.close()
            raise

    def _callback(self, outdata: Any, frames: int, _time: Any, status: Any) -> None:
        frame_bytes = self.channels * 2
        needed = frames * frame_bytes
        output = bytearray(needed)
        with self._lock:
            self.callback_count += 1
            if status:
                self.callback_flags.append(str(status))
                self.callback_flags = self.callback_flags[-8:]
                if getattr(status, 'output_underflow', False):
                    self.underflows += 1
            if self._pcm is not None:
                segment = self._pcm[self._position:self._position + needed]
                output[:len(segment)] = segment
                self._position += len(segment)
                if self._position >= len(self._pcm):
                    self._pcm = None
                    self._position = 0
            if self._tail is not None:
                fade_count = min(frames, self._fade_frames - self._tail_frame,
                                 (len(self._tail) - self._tail_pos) // frame_bytes)
                if fade_count > 0:
                    # Only the very short crossfade needs sample-by-sample mixing.
                    samples = array.array('h')
                    samples.frombytes(output[:fade_count * frame_bytes])
                    fading = array.array('h')
                    fading.frombytes(self._tail[self._tail_pos:self._tail_pos + fade_count * frame_bytes])
                    if sys.byteorder != 'little':
                        samples.byteswap(); fading.byteswap()
                    for j in range(fade_count):
                        gain = max(0.0, 1.0 - (self._tail_frame + j) / self._fade_frames)
                        for channel in range(self.channels):
                            i = j * self.channels + channel
                            samples[i] = max(-32768, min(32767, samples[i] + round(fading[i] * gain)))
                    if sys.byteorder != 'little':
                        samples.byteswap()
                    output[:fade_count * frame_bytes] = samples.tobytes()
                    self._tail_pos += fade_count * frame_bytes
                    self._tail_frame += fade_count
                if self._tail_frame >= self._fade_frames or self._tail_pos >= len(self._tail):
                    self._tail = None
        outdata[:] = output

    def play(self, pcm: bytes) -> None:
        with self._lock:
            self._tail = self._pcm
            self._tail_pos = self._position
            self._tail_frame = 0
            self._pcm = pcm
            self._position = 0

    def silence(self) -> None:
        with self._lock:
            self._tail = self._pcm
            self._tail_pos = self._position
            self._tail_frame = 0
            self._pcm = None
            self._position = 0

    def close(self) -> None:
        self._stream.stop()
        self._stream.close()


class AudioPlayer:
    """Cached guitar cues on a persistent WASAPI output, with device diagnostics.

    A warmup/preload runs in background before testing; the first uncached cue
    renders in its own worker so Tk never blocks.  PCM is kept in an LRU cache.
    """

    def __init__(self, volume: int = 65, *, output_id: str = '',
                 latency: str = 'high', blocksize: int = 0,
                 exclusive: bool = False) -> None:
        self.output_id = str(output_id)
        self.latency = latency if latency in ('high', 'low') else 'high'
        self.blocksize = blocksize if blocksize in (0, 256, 512, 1024, 2048) else 0
        self.exclusive = bool(exclusive)
        self.volume = max(0, min(100, int(volume)))
        self._backend: str | None = None
        self._sd: Any = None
        self._device: dict[str, Any] | None = None
        self.device_name = 'none'
        self.host_api_name = 'none'
        self.available_devices: list[dict[str, Any]] = []
        self.last_used_backend = 'none'
        self.last_result = 'idle'
        self.last_error = ''
        self._lock = threading.RLock()
        self._cue_stream: PersistentCueStream | None = None
        self._cache: OrderedDict[tuple[int, bool, int, int, int], bytes] = OrderedDict()
        self._cache_limit = 96
        self._ticket = 0
        self._closing = False
        self._preloader: threading.Thread | None = None
        self._preload_generation = 0
        self._process: subprocess.Popen | None = None
        self._worker: threading.Thread | None = None
        self._stop_event: threading.Event | None = None
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
                self.available_devices, default = find_output_devices(sd)
                requested = next((d for d in self.available_devices if d.get('id') == self.output_id), None)
                self._device = requested or default
                if self.output_id and requested is None:
                    self.last_error = 'Saved audio output not found; using automatic output'
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


    def list_outputs(self) -> list[dict[str, Any]]:
        """Refresh available PortAudio outputs without disrupting playback."""
        if self._sd is None:
            return []
        try:
            devices, _default = find_output_devices(self._sd)
            self.available_devices = devices
        except Exception as exc:
            self.last_error = f'Output enumeration failed: {exc}'
        return list(self.available_devices)

    def configure_output(self, *, output_id: str, latency: str = 'high',
                         blocksize: int = 0, exclusive: bool = False) -> None:
        """Switch device/options, releasing only the old stream (not the player)."""
        if latency not in ('high', 'low'):
            raise ValueError('Invalid latency setting')
        if blocksize not in (0, 256, 512, 1024, 2048):
            raise ValueError('Unsupported block size')
        devices = self.list_outputs()
        if output_id and not any(d['id'] == output_id for d in devices):
            raise ValueError('Selected output is no longer available')
        new_device = (next((d for d in devices if d['id'] == output_id), None)
                      if output_id else find_output_devices(self._sd)[1] if self._sd else None)
        if exclusive and (new_device is None or not new_device['wasapi']):
            raise ValueError('Exclusive mode requires WASAPI output')
        if (self.output_id, self.latency, self.blocksize, self.exclusive) == (output_id, latency, blocksize, exclusive):
            return
        # Invalidate pending rendering and detach before closing; callbacks
        # may acquire their own locks and must not race a new stream.
        with self._lock:
            self._ticket += 1
            self._preload_generation += 1
            stream, self._cue_stream = self._cue_stream, None
            self.output_id, self.latency = output_id, latency
            self.blocksize, self.exclusive = blocksize, exclusive
            self._device = new_device
            if new_device is not None:
                self.device_name, self.host_api_name = new_device['name'], new_device['hostapi']
                self._backend = 'wasapi' if new_device['wasapi'] else 'portaudio'
            self._cache.clear()
        if stream is not None:
            stream.close()
        if sys.platform == 'win32' and self._device is None:
            self.last_result = 'error'
            self.last_error = 'No output device found'
        else:
            self.last_result = 'idle'
            self.last_error = ''

    @property
    def available(self) -> bool:
        return self._backend is not None

    def _ensure_stream(self) -> bool:
        if sys.platform != 'win32':
            return True
        with self._lock:
            if self._closing:
                return False
            if self._cue_stream is not None:
                return True
            try:
                if self._sd is None or self._device is None:
                    raise AudioPlaybackError('WASAPI device not configured')
                self._cue_stream = PersistentCueStream(
                    self._sd, self._device, latency=self.latency,
                    blocksize=self.blocksize, exclusive=self.exclusive)
                self.last_error = ''
                return True
            except Exception as exc:
                self.last_result = 'error'
                self.last_error = f'{type(exc).__name__}: {exc}'
                return False

    def diagnostic(self) -> str:
        dev = self._device
        desc = ('n/a' if dev is None else
                f"{dev['index']}:{dev['name']} ({dev['hostapi']}, {dev['samplerate']} Hz, {dev['channels']}ch)")
        detected = ', '.join(f"{d['index']}:{d['name']} [{d['hostapi']}]" for d in self.available_devices)
        stream = self._cue_stream
        return (f'platform={sys.platform}; backend={self._backend or "none"}; used={self.last_used_backend}; '
                f'device={desc}; outputs={detected or "none"}; volume={self.volume}; '
                f'output_id={self.output_id or "auto"}; latency={self.latency}; '
                f'blocksize={self.blocksize}; exclusive={self.exclusive}; '
                f'stream={"open" if stream else "closed"}; '
                f'callback_count={stream.callback_count if stream else 0}; '
                f'underruns={stream.underflows if stream else 0}; '
                f'callback_status={",".join(stream.callback_flags) if stream else "none"}; '
                f'cached={len(self._cache)}; result={self.last_result}; error={self.last_error or "none"}')

    def _cache_key(self, note: int, buzzing: bool, volume: int) -> tuple[int, bool, int, int, int]:
        device = self._device or {'samplerate': SAMPLE_RATE, 'channels': 1}
        return (note, buzzing, volume, int(device['samplerate']), int(device['channels']))

    def _prepare(self, note: int, buzzing: bool, volume: int) -> bytes:
        key = self._cache_key(note, buzzing, volume)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        wav = synthesize_string(note, volume=volume/100,
                                duration=.48 if buzzing else 1.55,
                                buzzing=buzzing, sample_rate=key[3])
        with wave.open(io.BytesIO(wav), 'rb') as fd:
            pcm = fd.readframes(fd.getnframes())
        if sys.platform == 'win32':
            pcm = _stereo_pcm(pcm, key[4])
        with self._lock:
            if not self._closing:
                self._cache[key] = pcm
                self._cache.move_to_end(key)
                if len(self._cache) > self._cache_limit:
                    self._cache.popitem(last=False)
        return pcm

    def preload(self, notes: list[int] | tuple[int, ...]) -> None:
        """Warm playable notes in the background, without delaying the GUI."""
        if not self.available or self.volume == 0 or self._closing or sys.platform != 'win32':
            return
        if not self._ensure_stream():
            return
        notes = list(dict.fromkeys(n for n in notes if isinstance(n, int) and 0 <= n <= 127))
        if not notes:
            return
        volume = self.volume
        with self._lock:
            self._preload_generation += 1
            generation = self._preload_generation
        def warm() -> None:
            for note in notes:
                if self._closing or generation != self._preload_generation:
                    break
                try:
                    self._prepare(note, False, volume)
                except Exception as exc:
                    self.last_error = str(exc)
                # Yield CPU to WASAPI callback threads during cache warmup.
                time.sleep(.005)
        self._preloader = threading.Thread(target=warm, name='vGUITAR-audio-preload', daemon=True)
        self._preloader.start()

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
        if sys.platform == 'win32' and not self._ensure_stream():
            return False
        volume = self.volume
        with self._lock:
            self._ticket += 1
            ticket = self._ticket
            self.last_result, self.last_error = 'starting', ''
            self.last_used_backend = self._backend or 'none'
        key = self._cache_key(midi_note, buzzing, volume)
        with self._lock:
            cached = self._cache.get(key)
        if cached is not None:
            self._emit(cached, ticket)
        else:
            worker = threading.Thread(target=self._render_play, args=(midi_note, buzzing, volume, ticket),
                                      name='vGUITAR-audio-cue', daemon=True)
            self._worker = worker
            worker.start()
        return True

    def _render_play(self, note: int, buzzing: bool, volume: int, ticket: int) -> None:
        try:
            pcm = self._prepare(note, buzzing, volume)
            self._emit(pcm, ticket)
        except Exception as exc:
            with self._lock:
                if self._ticket == ticket:
                    self.last_result, self.last_error = 'error', f'{type(exc).__name__}: {exc}'

    def _emit(self, pcm: bytes, ticket: int) -> None:
        with self._lock:
            if ticket != self._ticket or self._closing:
                return
            if sys.platform == 'win32':
                if self._cue_stream is None:
                    return
                self._cue_stream.play(pcm)
                self.last_result = 'playing'
            else:
                self._worker = threading.Thread(target=self._play_other_pcm, args=(pcm, ticket), daemon=True)
                self._worker.start()

    def _play_other_pcm(self, pcm: bytes, ticket: int) -> None:
        try:
            rate = self._cache_key(40, False, self.volume)[3]
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                path = Path(tmp.name)
                with wave.open(tmp, 'wb') as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
                    w.writeframes(pcm)
            try:
                cmd = {'afplay':['afplay',str(path)], 'ffplay':['ffplay','-nodisp','-autoexit','-loglevel','quiet',str(path)],
                       'paplay':['paplay',str(path)], 'aplay':['aplay','-q',str(path)]}[self._backend]
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                self._process = proc
                _, stderr = proc.communicate()
                if proc.returncode:
                    raise AudioPlaybackError(f'{self._backend}: {stderr.decode(errors="replace")[:150]}')
            finally:
                path.unlink(missing_ok=True)
            with self._lock:
                if ticket == self._ticket:
                    self.last_result = 'played'
        except Exception as exc:
            with self._lock:
                if ticket == self._ticket:
                    self.last_result, self.last_error = 'error', str(exc)

    def stop(self) -> None:
        with self._lock:
            self._ticket += 1
            if self._cue_stream is not None:
                self._cue_stream.silence()
            proc = self._process
            self._process = None
        if proc is not None and proc.poll() is None:
            proc.terminate()

    def close(self) -> None:
        self.stop()
        with self._lock:
            self._closing = True
            self._preload_generation += 1
            stream = self._cue_stream
            self._cue_stream = None
        if stream is not None:
            stream.close()
        for worker in (self._preloader, self._worker):
            if worker is not None and worker.is_alive():
                worker.join(timeout=.2)
