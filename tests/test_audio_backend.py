"""Sounddevice / PortAudio Windows WASAPI backend tests without real speakers."""
from __future__ import annotations
import io
import sys
import threading
import types
import unittest
import wave
from unittest.mock import patch

from vguitar_audio import (AudioPlayer, PersistentCueStream, find_output_devices, play_portaudio_pcm,
                           synthesize_string, _stereo_pcm)


class FakePortAudio:
    def __init__(self, fail=False):
        self.devices = [
            dict(name='Old MME Speaker',hostapi=0,max_output_channels=2,default_samplerate=44100),
            dict(name='WASAPI Speakers',hostapi=1,max_output_channels=2,default_samplerate=48000),
            dict(name='WASAPI Mic',hostapi=1,max_output_channels=0,default_samplerate=48000),
        ]
        self.hostapis = [dict(name='MME',default_output_device=0),
                         dict(name='Windows WASAPI',default_output_device=1)]
        self.default = types.SimpleNamespace(device=[2,0])
        self.fail = fail
        self.streams=[]
    def query_devices(self):
        return self.devices
    def query_hostapis(self):
        return self.hostapis
    def RawOutputStream(self, **kwargs):
        if self.fail:
            raise RuntimeError('WASAPI endpoint unavailable')
        obj=FakeStream(kwargs)
        self.streams.append(obj)
        return obj


class FakeStream:
    def __init__(self, kwargs):
        self.kwargs=kwargs
        self.blocks=[]
        self.state=[]
    def start(self): self.state.append('start')
    def write(self, data): self.blocks.append(data)
    def stop(self): self.state.append('stop')
    def abort(self): self.state.append('abort')
    def close(self): self.state.append('close')


class WindowsWasapiTests(unittest.TestCase):
    def test_chooses_wasapi_over_mme_default(self):
        devices, selected=find_output_devices(FakePortAudio())
        self.assertEqual(len(devices),2)
        self.assertEqual(selected['index'],1)
        self.assertTrue(selected['wasapi'])
        self.assertEqual(selected['samplerate'],48000)

    def test_default_portaudio_fallback_when_no_wasapi_device(self):
        fake=FakePortAudio()
        fake.hostapis[1]['name']='Windows MME'
        _, selected=find_output_devices(fake)
        self.assertEqual(selected['index'],0)
        self.assertFalse(selected['wasapi'])

    def test_device_enumeration_empty(self):
        fake=FakePortAudio()
        fake.devices=[]
        self.assertIsNone(find_output_devices(fake)[1])

    def test_16000_stereo_frames_have_matching_channels(self):
        pcm=b'\x01\x00\xff\x7f'
        self.assertEqual(_stereo_pcm(pcm,2),b'\x01\x00\x01\x00\xff\x7f\xff\x7f')
        self.assertEqual(_stereo_pcm(pcm,1),pcm)

    def test_native_samplerate_pcm_is_valid(self):
        data=synthesize_string(40,duration=0.1,sample_rate=48000)
        with wave.open(io.BytesIO(data),'rb') as fd:
            self.assertEqual(fd.getframerate(),48000)
            self.assertEqual(fd.getnframes(),4800)

    def test_stream_lifecycle_and_16bit_stereo(self):
        fake=FakePortAudio()
        _, device=find_output_devices(fake)
        pcm=b'\x01\x00\x01\x00'*3000
        play_portaudio_pcm(fake,pcm,device,threading.Event())
        stream=fake.streams[0]
        self.assertEqual(stream.kwargs['device'],1)
        self.assertEqual(stream.kwargs['dtype'],'int16')
        self.assertEqual(stream.kwargs['channels'],2)
        self.assertEqual(stream.state,['start','stop','close'])
        self.assertEqual(b''.join(stream.blocks),pcm)

    def test_stream_interrupts_on_stop(self):
        fake=FakePortAudio()
        _, device=find_output_devices(fake)
        event=threading.Event()
        class InterruptedStream(FakeStream):
            def write(self,chunk):
                self.blocks.append(chunk)
                event.set()
        fake.RawOutputStream=lambda **kw: InterruptedStream(kw)
        # Wrapper stores the created stream for inspection.
        stream=InterruptedStream({})
        fake.RawOutputStream=lambda **kw: stream
        play_portaudio_pcm(fake,b'\x00'*16000,device,event)
        self.assertEqual(stream.state,['start','abort','close'])
        self.assertEqual(len(stream.blocks),1)

    def test_output_error_reported_no_false_fallback(self):
        player=AudioPlayer(volume=51)
        try:
            fake=FakePortAudio(fail=True)
            player._sd=fake
            _, player._device=find_output_devices(fake)
            player._backend='wasapi'
            with patch.object(sys, 'platform', 'win32'):
                self.assertFalse(player._ensure_stream())
            self.assertEqual(player.last_result,'error')
            self.assertIn('WASAPI endpoint unavailable',player.diagnostic())
            self.assertNotIn('winsound-fallback',player.diagnostic())
        finally:
            player.close()

    def test_backend_selection_win32_with_mocked_sounddevice(self):
        fake=FakePortAudio()
        with patch.object(sys,'platform','win32'),patch.dict(sys.modules,{'sounddevice':fake}):
            player=AudioPlayer(65)
            try:
                self.assertEqual(player._backend,'wasapi')
                self.assertTrue(player.available)
                self.assertIn('WASAPI Speakers',player.diagnostic())
                self.assertIn('48000',player.diagnostic())
            finally:
                player.close()

    def test_backend_missing_sounddevice_has_actionable_error(self):
        # Emulate a corrupt/wrong Python environment (no PortAudio wheel).
        with patch.object(sys,'platform','win32'),patch.dict(sys.modules,{'sounddevice':None}):
            player=AudioPlayer(60)
            try:
                self.assertFalse(player.available)
                self.assertIn('pip install',player.diagnostic())
            finally:
                player.close()

    def test_play_uses_one_persistent_wasapi_stream(self):
        fake=FakePortAudio()
        with patch.object(sys,'platform','win32'),patch.dict(sys.modules,{'sounddevice':fake}):
            player=AudioPlayer(50)
            try:
                self.assertTrue(player.play(40))
                player._worker.join(timeout=8)
                self.assertFalse(player._worker.is_alive())
                self.assertEqual(player.last_result,'playing')
                self.assertEqual(player.last_used_backend,'wasapi')
                self.assertEqual(len(fake.streams),1)
                self.assertEqual(fake.streams[0].kwargs['samplerate'],48000)
                self.assertTrue(callable(fake.streams[0].kwargs['callback']))
                self.assertTrue(player.play(40))
                self.assertEqual(len(fake.streams),1)
                output=bytearray(2*2*256)
                fake.streams[0].kwargs['callback'](output,256,None,None)
                self.assertNotEqual(output,bytearray(len(output)))
                self.assertIn('stream=open',player.diagnostic())
            finally:
                player.close()
        self.assertEqual(fake.streams[0].state, ['start','stop','close'])

    def test_callback_silence_and_quick_cue_replacement(self):
        fake=FakePortAudio()
        _,device=find_output_devices(fake)
        engine=PersistentCueStream(fake,device)
        try:
            render=lambda value: (value.to_bytes(2,'little',signed=True)*2)*512
            output=bytearray(2*2*128)
            engine._callback(output,128,None,None)
            self.assertEqual(output,bytearray(len(output)))
            engine.play(render(700))
            engine._callback(output,128,None,None)
            self.assertNotEqual(output,bytearray(len(output)))
            engine.play(render(-700))
            engine._callback(output,128,None,None)
            self.assertEqual(engine.callback_count,3)
            self.assertEqual(engine.underflows,0)
            engine.silence()
            engine._callback(output,128,None,None)
            self.assertEqual(engine.callback_count,4)
        finally:
            engine.close()

    def test_stale_render_does_not_interrupt_new_note(self):
        fake=FakePortAudio()
        with patch.object(sys,'platform','win32'),patch.dict(sys.modules,{'sounddevice':fake}):
            player=AudioPlayer(60)
            try:
                self.assertTrue(player._ensure_stream())
                player._ticket=2
                note=(1).to_bytes(2,'little')*2*128
                player._emit(note,1)
                self.assertIsNone(player._cue_stream._pcm)
                player._emit(note,2)
                self.assertEqual(player._cue_stream._pcm,note)
            finally:
                player.close()

    def test_zero_volume_is_not_reported_as_played(self):
        player=AudioPlayer(0)
        try:
            self.assertFalse(player.play(40))
            self.assertIn('muted',player.diagnostic())
        finally:
            player.close()


if __name__ == '__main__':
    unittest.main()
