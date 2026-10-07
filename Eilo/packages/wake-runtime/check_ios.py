#!/usr/bin/env python3
"""Offline, checksum-pinned iOS binding evaluation. Never opens a microphone or enables packs.

Download/extract the archives in ios-provenance.json under .local/kws/ios first.
Exit 0: limited synthetic acceptance; 1: acoustic failure; 2: unavailable/error.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from check_host import CACHE, HERE, digest, validate_manifest, verify_fixture


def run(arguments, timeout=120):
    return subprocess.run(arguments, check=True, capture_output=True, text=True, timeout=timeout)


def verify_candidates():
    provenance = json.loads((HERE / 'provenance.json').read_text())
    ios = json.loads((HERE / 'ios-provenance.json').read_text())
    fixtures = validate_manifest(json.loads((HERE / 'tests/fixtures/manifest.json').read_text()))
    root = CACHE / 'ios'
    for archive in ios['archives']:
        if digest(root / archive['file']) != archive['sha256']:
            raise ValueError('iOS archive integrity failed')
        for artifact in archive['files']:
            if digest(root / artifact['path']) != artifact['sha256']:
                raise ValueError('iOS extracted artifact integrity failed')
    model = provenance['model']
    if digest(CACHE / 'model.tar.bz2') != model['sha256']:
        raise ValueError('model archive integrity failed')
    for artifact in model['files']:
        if digest(CACHE / model['directory'] / artifact['path']) != artifact['sha256']:
            raise ValueError('model integrity failed')
    for fixture in fixtures:
        path = CACHE / 'fixtures' / fixture['file']
        if digest(path) != fixture['sha256']:
            raise ValueError('fixture integrity failed')
        verify_fixture(path)
    return root, CACHE / model['directory'], fixtures


def compile_runtime(root, variant, sdk, target):
    sherpa = root / 'sherpa-onnx.xcframework' / variant
    ort = root / 'onnxruntime.xcframework' / variant
    output = root / ('build-' + sdk)
    output.mkdir(exist_ok=True)
    sdk_path = run(['xcrun', '--sdk', sdk, '--show-sdk-path']).stdout.strip()
    obj = output / 'eilo_wake.o'
    run(['xcrun', '--sdk', sdk, 'clang++', '-target', target, '-isysroot', sdk_path,
         '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(HERE / 'include'),
         '-I', str(sherpa / 'SherpaOnnxC.framework/Headers'), '-c', str(HERE / 'eilo_wake.cc'),
         '-o', str(obj)])
    library = output / 'libeilo_wake.a'
    run(['xcrun', 'libtool', '-static', '-o', str(library), str(obj)])
    return output, sdk_path, ['-F', str(sherpa), '-F', str(ort), '-framework', 'SherpaOnnxC',
                              '-framework', 'onnxruntime', '-framework', 'CoreML', '-lc++'], library


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--udid', required=True, help='Explicit booted iOS simulator; never creates or erases it')
    args = parser.parse_args()
    devices = json.loads(run(['xcrun', 'simctl', 'list', 'devices', '--json'], 30).stdout)
    selected = [device for group in devices['devices'].values() for device in group
                if device['udid'] == args.udid and device['state'] == 'Booted' and device.get('isAvailable')]
    if len(selected) != 1:
        raise ValueError('selected simulator is not booted/available')
    root, model, fixtures = verify_candidates()
    output, sdk, link, library = compile_runtime(root, 'ios-arm64_x86_64-simulator',
                                               'iphonesimulator', 'arm64-apple-ios18.0-simulator')
    compile_runtime(root, 'ios-arm64', 'iphoneos', 'arm64-apple-ios18.0')
    executable = output / 'ios-wake-binding'
    sources = sorted((HERE.parent / 'native-test-seam/Sources/NativeTestSeam').glob('*.swift'))
    run(['xcrun', 'swiftc', '-target', 'arm64-apple-ios18.0-simulator', '-sdk', sdk,
         '-parse-as-library', '-D', 'DEBUG', '-D', 'EILO_WAKE_EVALUATION',
         '-I', str(HERE / 'include'), *map(str, sources), str(HERE / 'tests/ios_binding.swift'),
         str(library), *link, '-o', str(executable)])
    # Only Debug imports/links this local evaluation runtime. Standard builds retain fail-closed defaults.
    config = root / 'WakeEvaluation.xcconfig'
    config.write_text(
        'IPHONEOS_DEPLOYMENT_TARGET[config=Debug] = 18.0\n'
        'SWIFT_INCLUDE_PATHS[config=Debug] = $(inherited) "' + str(HERE / 'include') + '"\n'
        'SWIFT_ACTIVE_COMPILATION_CONDITIONS[config=Debug] = $(inherited) DEBUG EILO_WAKE_EVALUATION\n'
        'OTHER_LDFLAGS[config=Debug] = $(inherited) -force_load "' + str(library) + '" '
        + ' '.join('"' + item + '"' for item in link) + '\n')
    report = {'runtime': 'sherpa-onnx 1.13.8 / onnxruntime 1.28.2',
              'device': selected[0]['name'], 'udid': args.udid,
              'compiler': 'PASS: C++ simulator/device; Swift simulator binding',
              'microphone': 'not used', 'model_readiness': 'unchanged/unavailable', 'cases': []}
    failures = 0
    for fixture in fixtures:
        result = run(['xcrun', 'simctl', 'spawn', args.udid, str(executable), str(model),
                      str(CACHE / 'fixtures' / fixture['file'])], 60)
        value = json.loads(result.stdout)
        if value.get('closed_input_rejected') is not True or type(value.get('detections')) is not int:
            raise ValueError('invalid simulator binding result')
        expected = 1 if fixture['kind'] == 'wake' else 0 if fixture['kind'] == 'nonwake' else None
        passed = None if expected is None else value['detections'] == expected
        failures += passed is False
        report['cases'].append({'file': fixture['file'], 'kind': fixture['kind'],
                                'detections': value['detections'], 'expected': expected, 'pass': passed})
    report.update({'fixture_count': len(fixtures),
                   'unique_audio_count': len({item['sha256'] for item in fixtures}),
                   'failed_cases': failures,
                   'acoustic_acceptance': 'FAIL' if failures else 'PASS ON SYNTHETIC SET ONLY'})
    (root / 'ios-results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 1 if failures else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        print('iOS evaluation unavailable: integrity, compiler or simulator runner failed.', file=sys.stderr)
        sys.exit(2)
