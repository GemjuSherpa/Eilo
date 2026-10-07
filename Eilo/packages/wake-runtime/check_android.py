#!/usr/bin/env python3
"""Pinned offline Android cross-link and host-JVM JNI evaluation; no microphone/device claim."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from check_host import CACHE, HERE, digest, validate_manifest, verify_fixture


def run(args, timeout=120, env=None):
    return subprocess.run(list(map(str, args)), check=True, capture_output=True, text=True, timeout=timeout, env=env)


def verify_candidates():
    android = json.loads((HERE / 'android-provenance.json').read_text())
    provenance = json.loads((HERE / 'provenance.json').read_text())
    root = CACHE / 'android'
    archive = android['archive']
    if digest(root / archive['file']) != archive['sha256']:
        raise ValueError('Android archive integrity failed')
    for item in archive['files']:
        if digest(root / item['path']) != item['sha256']:
            raise ValueError('Android extracted artifact integrity failed')
    # The matching official release C header and host runtime are pinned separately.
    for kind, name in [('runtime', 'runtime.tar.bz2'), ('model', 'model.tar.bz2')]:
        record = provenance[kind]
        if digest(CACHE / name) != record['sha256']:
            raise ValueError('candidate archive integrity failed')
        for item in record['files']:
            if digest(CACHE / record['directory'] / item['path']) != item['sha256']:
                raise ValueError('candidate file integrity failed')
    fixtures = validate_manifest(json.loads((HERE / 'tests/fixtures/manifest.json').read_text()))
    for fixture in fixtures:
        path = CACHE / 'fixtures' / fixture['file']
        if digest(path) != fixture['sha256']:
            raise ValueError('fixture integrity failed')
        verify_fixture(path)
    return root, CACHE / provenance['runtime']['directory'], fixtures


def verify_report(report, fixtures):
    cases = report.get('cases')
    if (report.get('fixture_count') != len(fixtures) or not isinstance(cases, list)
            or len(cases) != len(fixtures) or report.get('jni_invalid_stale_handles') != 'PASS'
            or report.get('acoustic_acceptance') != 'PASS ON SYNTHETIC SET ONLY'):
        raise ValueError('host JNI report failed')
    for case, fixture in zip(cases, fixtures):
        expected = 1 if fixture['kind'] == 'wake' else 0 if fixture['kind'] == 'nonwake' else None
        if (case.get('file') != fixture['file'] or case.get('kind') != fixture['kind']
                or type(case.get('detections')) is not int or case['detections'] < 0
                or (expected is not None and case['detections'] != expected)
                or case.get('closed_input_rejected') is not True
                or case.get('controller_stop_rejected') is not True):
            raise ValueError('host JNI case failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ndk', required=True, type=Path)
    parser.add_argument('--java-home', required=True, type=Path)
    parser.add_argument('--android-sdk', required=True, type=Path)
    args = parser.parse_args()
    if 'Pkg.Revision = 27.1.12297006' not in (args.ndk / 'source.properties').read_text():
        raise ValueError('unexpected NDK version')
    root, host, fixtures = verify_candidates()
    toolchain = args.ndk / 'toolchains/llvm/prebuilt/darwin-x86_64/bin'
    targets = {'arm64-v8a': 'aarch64-linux-android26', 'armeabi-v7a': 'armv7a-linux-androideabi26',
               'x86': 'i686-linux-android26', 'x86_64': 'x86_64-linux-android26'}
    for abi, target in targets.items():
        output = root / 'build' / abi
        output.mkdir(parents=True, exist_ok=True)
        libs = root / 'jniLibs' / abi
        run([toolchain / (target + '-clang++'), '-std=c++17', '-Wall', '-Wextra', '-Werror',
             '-fPIC', '-shared', '-static-libstdc++', '-Wl,--no-undefined', '-Wl,-z,max-page-size=16384',
             '-I', HERE / 'include', '-I', host / 'include', HERE / 'eilo_wake.cc', HERE / 'eilo_wake_jni.cc',
             '-L', libs, '-Wl,-rpath-link,' + str(libs), '-lsherpa-onnx-c-api', '-o', output / 'libeilo_wake_jni.so'])
    host_lib = root / 'libeilo_wake_jni.dylib'
    run(['xcrun', 'clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-dynamiclib',
         '-I', args.java_home / 'include', '-I', args.java_home / 'include/darwin',
         '-I', HERE / 'include', '-I', host / 'include', HERE / 'eilo_wake.cc', HERE / 'eilo_wake_jni.cc',
         '-L', host / 'lib', '-lsherpa-onnx-c-api', '-Wl,-rpath,' + str(host / 'lib'), '-o', host_lib])
    # Only this explicitly requested offline evaluation adds the host harness to the test source set.
    init = root / 'evaluation.init.gradle'
    def quoted(path):
        return json.dumps(str(path))
    init.write_text('gradle.afterProject { p ->\n if (p.path == ":app") {\n'
                    ' p.android.sourceSets.test.java.srcDir(' + quoted(HERE / 'tests/android') + ')\n'
                    ' p.tasks.withType(Test).configureEach {\n'
                    ' systemProperty "eilo.wake.root", ' + quoted(HERE) + '\n'
                    ' systemProperty "eilo.wake.cache", ' + quoted(CACHE) + '\n'
                    ' systemProperty "eilo.wake.library", ' + quoted(host_lib) + '\n'
                    ' filter { includeTestsMatching "com.eilo.foundation.NativeWakeEvaluationTest" }\n'
                    ' }\n }\n}\n')
    env = dict(os.environ, JAVA_HOME=str(args.java_home), ANDROID_HOME=str(args.android_sdk))
    (root / 'host-jni-results.json').unlink(missing_ok=True)
    project = HERE.parents[1] / 'apps/mobile/android'
    run([project / 'gradlew', '-p', project, '-I', init, ':app:testDebugUnitTest', '--offline',
         '--rerun-tasks', '--max-workers=2'], timeout=900, env=env)
    report = json.loads((root / 'host-jni-results.json').read_text())
    verify_report(report, fixtures)
    report['unique_audio_count'] = len({item['sha256'] for item in fixtures})
    report['android_compiler'] = 'PASS: NDK 27.1.12297006 / API 26, all four ABI shared-library links'
    report['android_execution'] = 'NOT RUN: no connected Android emulator or physical device'
    (root / 'android-results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        print('Android evaluation unavailable: integrity, compiler or host-JVM runner failed.', file=sys.stderr)
        sys.exit(2)
