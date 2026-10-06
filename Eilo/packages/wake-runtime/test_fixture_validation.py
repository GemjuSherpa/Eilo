"""Prevent empty/silent TTS generation from being scored as wake recognition."""
from pathlib import Path
import struct
import tempfile
import unittest
import wave
from check_host import verify_fixture


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


if __name__ == '__main__':
    unittest.main()
