"""Prevent empty/silent TTS generation from being scored as wake recognition."""
from pathlib import Path
import struct
import tempfile
import unittest
import wave
from check_host import verify_fixture, validate_manifest


class FixtureValidationTests(unittest.TestCase):
    def write(self, path, samples, rate=16000):
        with wave.open(str(path), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(rate)
            audio.writeframes(b''.join(struct.pack('<h', sample) for sample in samples))

    def test_empty_and_silence_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.wav'
            for samples in ([], [0] * 32000):
                self.write(path, samples)
                with self.assertRaises(ValueError):
                    verify_fixture(path)

    def test_wrong_rate_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.wav'
            self.write(path, [1000] * 16000, rate=8000)
            with self.assertRaises(ValueError):
                verify_fixture(path)

    def test_active_pcm_is_eligible_for_scoring(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.wav'
            self.write(path, [0] * 16000 + [1000, -1000] * 1600 + [0] * 16000)
            verify_fixture(path)


class ManifestValidationTests(unittest.TestCase):
    def fixture(self, name='wake.wav', kind='wake'):
        return {'file': name, 'kind': kind, 'sha256': 'a' * 64}

    def valid(self):
        return {'fixtures': [self.fixture(), self.fixture('ordinary.wav', 'nonwake')]}

    def test_valid_set_and_duplicate_audio_remain_explicit(self):
        manifest = self.valid()
        self.assertEqual(len(validate_manifest(manifest)), 2)

    def test_empty_one_sided_and_diagnostics_only_rejected(self):
        for fixtures in ([], [self.fixture()],
                         [self.fixture(), self.fixture('second.wav')],
                         [self.fixture('a.wav', 'spelling diagnostic'),
                          self.fixture('b.wav', 'pronunciation diagnostic')]):
            with self.subTest(fixtures=fixtures), self.assertRaises(ValueError):
                validate_manifest({'fixtures': fixtures})

    def test_misspelled_classification_rejected(self):
        manifest = self.valid()
        manifest['fixtures'][0]['kind'] = 'wkae'
        with self.assertRaises(ValueError):
            validate_manifest(manifest)

    def test_duplicate_or_escaping_filename_rejected(self):
        for name in ('wake.wav', '../outside.wav', '/outside.wav', 'folder\\outside.wav'):
            manifest = self.valid()
            manifest['fixtures'][1]['file'] = name
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_manifest(manifest)

    def test_malformed_shape_digest_or_unbounded_set_rejected(self):
        for manifest in (None, {}, {'fixtures': {}}, {'fixtures': [None, None]},
                         {'fixtures': [self.fixture(str(i) + '.wav') for i in range(257)]}):
            with self.subTest(manifest=manifest), self.assertRaises(ValueError):
                validate_manifest(manifest)
        for checksum in (None, '', 'g' * 64, 'a' * 63):
            manifest = self.valid()
            manifest['fixtures'][0]['sha256'] = checksum
            with self.subTest(checksum=checksum), self.assertRaises(ValueError):
                validate_manifest(manifest)


if __name__ == '__main__':
    unittest.main()
