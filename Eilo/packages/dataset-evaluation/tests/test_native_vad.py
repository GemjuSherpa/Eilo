import ctypes as C
import unittest
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
from manifests import sha256
from native_vad_adapter import detect, Segment, SETTINGS, verified_config


class Fake:
    def __init__(self, fail=False):
        self.events = []
        self.queue = []
        self.fail = fail
        self.functions = {name: getattr(self, name) for name in (
            'CreateVoiceActivityDetector', 'DestroyVoiceActivityDetector',
            'VoiceActivityDetectorAcceptWaveform', 'VoiceActivityDetectorEmpty',
            'VoiceActivityDetectorFront', 'DestroySpeechSegment',
            'VoiceActivityDetectorPop', 'VoiceActivityDetectorFlush', 'VoiceActivityDetectorReset')}
    def CreateVoiceActivityDetector(self, config, seconds): return 1
    def DestroyVoiceActivityDetector(self, handle): self.events.append('destroy')
    def VoiceActivityDetectorAcceptWaveform(self, handle, samples, n):
        self.events.append(('accept', n, samples[n-1]))
        if self.fail: raise ValueError('native failure')
    def VoiceActivityDetectorEmpty(self, handle): return not self.queue
    def VoiceActivityDetectorFront(self, handle): return C.pointer(self.queue[0])
    def DestroySpeechSegment(self, segment): self.events.append('free')
    def VoiceActivityDetectorPop(self, handle): self.queue.pop(0)
    def VoiceActivityDetectorFlush(self, handle):
        self.events.append('flush')
        self.queue.append(Segment(0, None, 512))
    def VoiceActivityDetectorReset(self, handle): self.events.append('reset')


class NativeVadTests(unittest.TestCase):
    def test_tail_padding_flush_clamp_and_cleanup(self):
        fake = Fake()
        self.assertEqual(detect([100]*513, {'model': {'path': 'unused'}}, fake.functions), [[0, 512/16000]])
        self.assertEqual(fake.events[1], ('accept', 512, 0.0))
        self.assertEqual(fake.events[-4:], ['flush', 'free', 'reset', 'destroy'])
        fake = Fake()
        self.assertEqual(detect([0]*7, {'model': {'path': 'unused'}}, fake.functions), [[0, 7/16000]])

    def test_failure_always_resets_and_destroys(self):
        fake = Fake(fail=True)
        with self.assertRaises(ValueError): detect([0]*10, {'model': {'path': 'unused'}}, fake.functions)
        self.assertEqual(fake.events[-2:], ['reset', 'destroy'])

    def test_input_bounds_before_native_call(self):
        for samples in ([], [32768], [float('nan')], [0]*480001):
            with self.assertRaises(ValueError): detect(samples, {}, {})

    def test_unreviewed_model_and_changed_config_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder) / 'model'
            model.write_bytes(b'unreviewed')
            config = Path(folder) / 'config.json'
            value = {'runtime_version': '1.13.8', 'settings': SETTINGS,
                     'model': {'path': str(model), 'sha256': sha256(model)},
                     'runtime_files': [], 'library': 'unused'}
            config.write_text(json.dumps(value))
            with patch.dict(os.environ, {'EILO_DATA_ADAPTER_CONFIG_SHA256': sha256(config),
                                        'EILO_DATA_ADAPTER_MODEL_SHA256': sha256(model)}):
                with self.assertRaisesRegex(ValueError, 'unreviewed model'):
                    verified_config(config)
                config.write_text('{}')
                with self.assertRaisesRegex(ValueError, 'config changed'):
                    verified_config(config)
