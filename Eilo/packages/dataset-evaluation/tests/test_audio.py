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
                       'permission': 'APPROVED_BY_USER_TEST', 'checksum_status': 'LOCAL_OBSERVED',
                       'schema_version': 1, 'sha256': '0' * 64, 'bytes': 1,
                       'license': 'CC-BY-4.0', 'license_evidence_sha256': '1' * 64}
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
                       'permission': 'APPROVED_BY_USER_TEST', 'checksum_status': 'LOCAL_OBSERVED',
                       'schema_version': 1, 'sha256': '0' * 64, 'bytes': 1,
                       'license': 'CC-BY-4.0', 'license_evidence_sha256': '1' * 64}
            with self.assertRaises(ValueError):
                freeze('speech_commands', root, root / 'output', '0.02', receipt)

    def test_musan_filters_reviewed_component_and_marks_weak_labels(self):
        from preprocess import candidates
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'noise/free-sound').mkdir(parents=True)
            (root / 'noise/sound-bible').mkdir(parents=True)
            license_path = root / 'noise/free-sound/LICENSE'
            license_path.write_text('All selected recordings were marked as in the Public Domain')
            write_wav(root / 'noise/free-sound/a.wav', [100] * 160)
            write_wav(root / 'noise/sound-bible/b.wav', [100] * 160)
            rows = list(candidates('musan', root, 'test'))
            self.assertEqual(len(rows), 1)
            self.assertIn('free-sound', rows[0]['path'])
            self.assertEqual(rows[0]['annotation_status'], 'CORPUS_CATEGORY_WEAK_LABEL')
            license_path.write_text('changed terms')
            with self.assertRaises(ValueError): list(candidates('musan', root, 'test'))

    def test_pinned_afconvert_decode_and_oversized_output_rejection(self):
        from unittest.mock import patch
        from audio import decode_mp3
        from manifests import sha256
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, decoder = root / 'source.mp3', root / 'decoder'
            source.write_bytes(b'synthetic encoded input')
            decoder.write_bytes(b'pinned test decoder')
            def convert(command, **kwargs):
                self.assertIn('--mix', command)
                write_wav(command[-1], [100] * 160)
            with patch('audio.subprocess.run', side_effect=convert):
                self.assertEqual(decode_mp3(source, decoder, sha256(decoder), 'afconvert'), [100] * 160)
            with self.assertRaises(ValueError): decode_mp3(source, decoder, '0' * 64, 'afconvert')
            def too_long(command, **kwargs): write_wav(command[-1], [1] * 480000)
            with patch('audio.subprocess.run', side_effect=too_long):
                with self.assertRaises(ValueError): decode_mp3(source, decoder, sha256(decoder), 'afconvert')
