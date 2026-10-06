#!/usr/bin/env python3
"""Verify pinned local candidates, compile C ABI checks and score synthetic fixtures.

No microphone, networking or package installation. Exit 1 means acoustic acceptance
failed; a successful compiler/contract check never makes a missed wake a pass.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import wave
import struct

HERE = Path(__file__).resolve().parent
CACHE = HERE.parents[1] / '.local' / 'kws'


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def verify_fixture(path):
    with wave.open(str(path), 'rb') as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getframerate() != 16000:
            raise ValueError('fixture format failed')
        samples = struct.iter_unpack('<h', audio.readframes(audio.getnframes()))
        if sum(abs(sample[0]) > 100 for sample in samples) < 1600:
            raise ValueError('fixture is empty or silent')


def main():
    provenance = json.loads((HERE / 'provenance.json').read_text())
    fixture_manifest = json.loads((HERE / 'tests/fixtures/manifest.json').read_text())
    for role in ('runtime', 'model'):
        item = provenance[role]
        if digest(CACHE / (role + '.tar.bz2')) != item['sha256']:
            raise ValueError('archive integrity failed')
        for artifact in item['files']:
            if digest(CACHE / item['directory'] / artifact['path']) != artifact['sha256']:
                raise ValueError('extracted candidate integrity failed')
    for fixture in fixture_manifest['fixtures']:
        path = CACHE / 'fixtures' / fixture['file']
        if digest(path) != fixture['sha256']:
            raise ValueError('fixture integrity failed')
        verify_fixture(path)
    runtime = CACHE / provenance['runtime']['directory']
    model = CACHE / provenance['model']['directory']
    flags = ['clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
             '-I', str(HERE / 'include'), '-I', str(runtime / 'include'), str(HERE / 'eilo_wake.cc')]
    contract = CACHE / 'contract'
    subprocess.run(flags + ['-fsanitize=address,undefined', str(HERE / 'tests/contract.cc'),
                            '-o', str(contract)], check=True)
    subprocess.run([str(contract)], check=True)
    acoustic = CACHE / 'acoustic'
    subprocess.run(flags + [str(HERE / 'tests/acoustic.cc'), '-L', str(runtime / 'lib'),
                            '-lsherpa-onnx-c-api', '-Wl,-rpath,' + str(runtime / 'lib'),
                            '-o', str(acoustic)], check=True)
    report = {'compiler': 'pass', 'scripted_abi_contract': 'pass', 'host': 'macOS ARM64',
              'phrase': provenance['phrase'], 'pronunciation': provenance['pronunciation'],
              'threshold': provenance['evaluation_threshold'], 'boost': provenance['evaluation_boost'], 'cases': []}
    failures = 0
    for fixture in fixture_manifest['fixtures']:
        result = subprocess.run([str(acoustic), str(model), str(CACHE / 'fixtures' / fixture['file']),
                                 str(provenance['evaluation_threshold']), str(provenance['evaluation_boost'])], capture_output=True, text=True, check=True)
        detections = json.loads(result.stdout)['detections']
        expected = 1 if fixture['kind'] == 'wake' else 0 if fixture['kind'] == 'nonwake' else None
        passed = None if expected is None else detections == expected
        failures += passed is False
        report['cases'].append({'file': fixture['file'], 'kind': fixture['kind'],
                                'detections': detections, 'expected': expected, 'pass': passed})
    report['acoustic_acceptance'] = 'FAIL' if failures else 'PASS ON SYNTHETIC SET ONLY'
    report['failed_cases'] = failures
    output = CACHE / 'host-results.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 1 if failures else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        print('Host check unavailable: candidate integrity, compiler or runner failed.', file=sys.stderr)
        sys.exit(2)
