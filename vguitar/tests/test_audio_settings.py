"""vGUITAR device-selection and persistent WASAPI-configuration regression tests."""
from __future__ import annotations
import sys
import types
import unittest
from unittest.mock import patch
from vguitar_audio import AudioPlayer, PersistentCueStream, find_output_devices

class FakeStream:
    def __init__(self, config):
        self.config=config
        self.started=False
        self.closed=False
    def start(self): self.started=True
    def stop(self): self.started=False
    def close(self): self.closed=True

class FakeSounddevice:
    def __init__(self):
        self.default=types.SimpleNamespace(device=[-1,1])
        self._devices=[
            dict(name='MME default',hostapi=0,max_output_channels=2,default_samplerate=44100),
            dict(name='Headphones',hostapi=1,max_output_channels=2,default_samplerate=48000),
            dict(name='Speakers',hostapi=1,max_output_channels=2,default_samplerate=48000),
        ]
        self._apis=[dict(name='MME',default_output_device=0),dict(name='Windows WASAPI',default_output_device=1)]
        self.streams=[]
        self.exclusive_calls=[]
    def query_devices(self):return self._devices
    def query_hostapis(self):return self._apis
    def WasapiSettings(self,**kwargs):
        self.exclusive_calls.append(kwargs)
        return dict(kwargs)
    def RawOutputStream(self,**kwargs):
        obj=FakeStream(kwargs)
        self.streams.append(obj)
        return obj

class AudioOutputSettingsTests(unittest.TestCase):
    def test_device_ids_are_stable_by_name_and_api(self):
        fake=FakeSounddevice()
        all_devices, default=find_output_devices(fake)
        self.assertEqual(default['name'],'Headphones')
        self.assertEqual(all_devices[2]['id'],'Windows WASAPI|Speakers')
        self.assertEqual(len(set(d['id'] for d in all_devices)),3)

    def test_switch_reopens_only_when_needed(self):
        fake=FakeSounddevice()
        with patch.object(sys,'platform','win32'),patch.dict(sys.modules,{'sounddevice':fake}):
            player=AudioPlayer(45)
            try:
                self.assertTrue(player._ensure_stream())
                first=fake.streams[0]
                player.configure_output(output_id='Windows WASAPI|Speakers',latency='low',blocksize=512,exclusive=True)
                self.assertTrue(first.closed)
                self.assertEqual(player.device_name,'Speakers')
                self.assertTrue(player._ensure_stream())
                second=fake.streams[1]
                self.assertEqual(second.config['device'],2)
                self.assertEqual(second.config['latency'],'low')
                self.assertEqual(second.config['blocksize'],512)
                self.assertEqual(second.config['extra_settings'],{'exclusive':True})
                self.assertIn('exclusive=True',player.diagnostic())
                player.configure_output(output_id='Windows WASAPI|Speakers',latency='low',blocksize=512,exclusive=True)
                self.assertFalse(second.closed)
                player.configure_output(output_id='',latency='high',blocksize=0,exclusive=False)
                self.assertTrue(second.closed)
                self.assertEqual(player.device_name,'Headphones')
            finally:
                player.close()

    def test_reject_disconnected_device_and_unsupported_exclusive(self):
        fake=FakeSounddevice()
        with patch.object(sys,'platform','win32'),patch.dict(sys.modules,{'sounddevice':fake}):
            player=AudioPlayer(65)
            try:
                with self.assertRaisesRegex(ValueError,'no longer available'):
                    player.configure_output(output_id='Windows WASAPI|Disappeared')
                with self.assertRaisesRegex(ValueError,'requires WASAPI'):
                    player.configure_output(output_id='MME|MME default', exclusive=True)
                self.assertEqual(player.output_id,'')
            finally:
                player.close()

    def test_startup_prefers_selected_output_if_present(self):
        fake=FakeSounddevice()
        with patch.object(sys,'platform','win32'),patch.dict(sys.modules,{'sounddevice':fake}):
            player=AudioPlayer(60,output_id='Windows WASAPI|Speakers',blocksize=1024)
            try:
                self.assertEqual(player.device_name,'Speakers')
                self.assertEqual(player.blocksize,1024)
            finally:
                player.close()

if __name__=='__main__':unittest.main()
