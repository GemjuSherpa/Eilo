"""Synthetic integrity regressions; no vendor downloads, simulator or microphone."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

import check_ios


class IOSIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.here = self.root / 'source'
        self.cache = self.root / 'cache'
        (self.here / 'tests/fixtures').mkdir(parents=True)
        (self.cache / 'ios').mkdir(parents=True)
        (self.cache / 'model').mkdir()
        (self.cache / 'fixtures').mkdir()
        for name in ['ios/archive.zip', 'ios/runtime', 'model.tar.bz2', 'model/encoder']:
            (self.cache / name).write_bytes(b'synthetic verified asset')
        def record(name):
            return {'path': name, 'sha256': hashlib.sha256((self.cache / name).read_bytes()).hexdigest()}
        self.write('ios-provenance.json', {'archives': [{
            'file': 'archive.zip', 'sha256': record('ios/archive.zip')['sha256'],
            'files': [{'path': 'runtime', 'sha256': record('ios/runtime')['sha256']}]}]})
        self.write('provenance.json', {'model': {
            'directory': 'model', 'sha256': record('model.tar.bz2')['sha256'],
            'files': [{'path': 'encoder', 'sha256': record('model/encoder')['sha256']}]}})
        fixtures = []
        for name, kind in [('wake.wav', 'wake'), ('ordinary.wav', 'nonwake')]:
            with wave.open(str(self.cache / 'fixtures' / name), 'wb') as audio:
                audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000)
                audio.writeframes(b'\xf4\x01' * 1600)
            fixtures.append({'file': name, 'kind': kind, 'sha256': record('fixtures/' + name)['sha256']})
        self.write('tests/fixtures/manifest.json', {'fixtures': fixtures})
        self.addCleanup(patch.stopall)
        patch.object(check_ios, 'HERE', self.here).start()
        patch.object(check_ios, 'CACHE', self.cache).start()

    def write(self, name, value):
        (self.here / name).write_text(json.dumps(value))

    def testVerifiedSyntheticCandidatesReturnCompleteAcceptanceSet(self):
        root, model, fixtures = check_ios.verify_candidates()
        self.assertEqual(root, self.cache / 'ios')
        self.assertEqual(model, self.cache / 'model')
        self.assertEqual(len(fixtures), 2)

    def testChangedArchivesExtractedRuntimeModelAndFixtureFailClosed(self):
        for name in ['ios/archive.zip', 'ios/runtime', 'model.tar.bz2', 'model/encoder', 'fixtures/wake.wav']:
            with self.subTest(asset=name):
                target = self.cache / name
                original = target.read_bytes()
                target.write_bytes(b'tampered synthetic asset')
                with self.assertRaises(ValueError):
                    check_ios.verify_candidates()
                target.write_bytes(original)

    def testMissingArtifactCannotRun(self):
        (self.cache / 'ios/runtime').unlink()
        with self.assertRaises(OSError):
            check_ios.verify_candidates()

    def testEmptyOrOneSidedAcceptanceCannotRun(self):
        for fixtures in [[], [{'file': 'wake.wav', 'kind': 'wake', 'sha256': 'a' * 64}]]:
            self.write('tests/fixtures/manifest.json', {'fixtures': fixtures})
            with self.assertRaises(ValueError):
                check_ios.verify_candidates()


if __name__ == '__main__':
    unittest.main()
