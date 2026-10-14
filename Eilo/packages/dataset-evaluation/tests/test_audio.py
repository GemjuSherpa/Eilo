import hashlib
from pathlib import Path
import tempfile
import unittest
import wave
from audio import read_wav, resample, write_wav
from preprocess import freeze


class AudioTests(unittest.TestCase):
    def test_rates_constant_and_area_filter(self):
        for rate in (8000, 16000, 44100, 48000):
            result = resample([1000] * rate, rate)
            self.assertEqual(len(result), 16000)
            self.assertEqual(set(result), {1000})
        self.assertEqual(resample([1000, -1000] * 10, 32000), [0] * 10)

    def test_wav_roundtrip_extremes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'audio.wav'
            write_wav(path, [-32768, 0, 32767])
            self.assertEqual(read_wav(path), [-32768, 0, 32767])

    def test_stereo_unsigned_and_bad_duration(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'audio.wav'
            with wave.open(str(path), 'wb') as stream:
                stream.setparams((2, 1, 16000, 0, 'NONE', 'not compressed'))
                stream.writeframes(bytes([0, 255, 128, 128]))
            self.assertEqual(read_wav(path), [-128, 0])
            with self.assertRaises(ValueError):
                read_wav(path, max_seconds=0)

    def test_freeze_determinism_and_official_split(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'source'
            (root / 'yes').mkdir(parents=True)
            (root / 'testing_list.txt').write_text('yes/alice_nohash_0.wav\n')
            write_wav(root / 'yes/alice_nohash_0.wav', [10] * 160)
            receipt = {'version': '0.02', 'dataset': 'speech_commands',
                       'permission': 'APPROVED_BY_USER_TEST', 'checksum_status': 'LOCAL_OBSERVED'}
            a = freeze('speech_commands', root, Path(temp) / 'a', '0.02', receipt)
            b = freeze('speech_commands', root, Path(temp) / 'b', '0.02', receipt)
            self.assertEqual(a, b)
            self.assertNotIn('alice', str(a))
            with self.assertRaises(ValueError):
                freeze('speech_commands', root, Path(temp) / 'c', '0.02', receipt, split='train')
            with self.assertRaises(ValueError):
                freeze('speech_commands', root, Path(temp) / 'a', '0.02', receipt)

    def test_duplicate_and_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'testing_list.txt').write_text('../escape.wav\n')
            receipt = {'version': '0.02', 'dataset': 'speech_commands',
                       'permission': 'APPROVED_BY_USER_TEST', 'checksum_status': 'LOCAL_OBSERVED'}
            with self.assertRaises(ValueError):
                freeze('speech_commands', root, root / 'output', '0.02', receipt)
