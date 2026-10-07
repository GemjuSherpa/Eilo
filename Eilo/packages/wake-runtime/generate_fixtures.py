#!/usr/bin/env python3
"""Regenerate synthetic fixtures locally; never modify the frozen manifest."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import wave
from check_host import CACHE, HERE, verify_fixture


def main():
    manifest = json.loads((HERE / 'tests/fixtures/manifest.json').read_text())
    target = CACHE / 'fixtures'
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        scratch = Path(directory)
        for fixture in manifest['fixtures']:
            name = Path(fixture['file']).stem
            aiff, unpadded, padded = (scratch / filename for filename in ('speech.aiff', 'speech.wav', 'padded.wav'))
            subprocess.run(['say', '-v', 'Samantha', '-o', str(aiff), manifest['generation_text'][name]], check=True, timeout=30)
            subprocess.run(['afconvert', '-f', 'WAVE', '-d', 'LEI16@16000', '-c', '1', str(aiff), str(unpadded)], check=True, timeout=30)
            with wave.open(str(unpadded), 'rb') as audio:
                parameters, samples = audio.getparams(), audio.readframes(audio.getnframes())
            with wave.open(str(padded), 'wb') as audio:
                audio.setparams(parameters)
                audio.writeframes(bytes(32000) + samples + bytes(32000))
            verify_fixture(padded)
            if hashlib.sha256(padded.read_bytes()).hexdigest() != fixture['sha256']:
                raise ValueError('Installed voice output differs from frozen fixture')
            (target / fixture['file']).write_bytes(padded.read_bytes())
    print('Local synthetic fixtures match frozen hashes.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError):
        print('Fixture generation unavailable: voice conversion failed/timed out, or output is empty/changed from frozen hashes.', file=sys.stderr)
        sys.exit(2)
