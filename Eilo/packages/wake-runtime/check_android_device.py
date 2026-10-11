#!/usr/bin/env python3
"""Explicit installed-emulator synthetic JNI evaluation; no microphone or default readiness."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from check_android import run, verify_candidates, verify_report
from check_android_package import verify_apk
from check_host import HERE, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ndk', required=True, type=Path)
    parser.add_argument('--java-home', required=True, type=Path)
    parser.add_argument('--android-sdk', required=True, type=Path)
    parser.add_argument('--serial', required=True)
    args = parser.parse_args()
    if not args.serial.startswith('emulator-') or not args.serial[9:].isdigit():
        raise ValueError('explicit emulator serial required')
    adb = args.android_sdk / 'platform-tools/adb'
    def device(*values, timeout=120):
        return run([adb, '-s', args.serial, *values], timeout=timeout)
    if device('shell', 'getprop', 'sys.boot_completed').stdout.strip() != '1':
        raise ValueError('emulator not booted')
    if device('shell', 'getprop', 'ro.build.version.sdk').stdout.strip() != '35':
        raise ValueError('evaluation requires API35 emulator')
    if device('shell', 'getprop', 'ro.product.cpu.abi').stdout.strip() != 'arm64-v8a':
        raise ValueError('evaluation requires ARM64 emulator')
    root, _, fixtures = verify_candidates()
    output = root / 'device-results.json'
    output.unlink(missing_ok=True)
    options = ['--ndk', args.ndk, '--java-home', args.java_home, '--android-sdk', args.android_sdk]
    run([sys.executable, HERE / 'check_android_package.py', *options], timeout=900)
    # Only pinned synthetic evaluation assets; no recordings or production trust configuration.
    assets = root / 'device-assets/wake-evaluation'
    if assets.parent.exists():
        shutil.rmtree(assets.parent)
    assets.mkdir(parents=True)
    shutil.copyfile(HERE / 'provenance.json', assets / 'provenance.json')
    (assets / 'tests/fixtures').mkdir(parents=True)
    shutil.copyfile(HERE / 'tests/fixtures/manifest.json', assets / 'tests/fixtures/manifest.json')
    provenance = json.loads((HERE / 'provenance.json').read_text())
    model = provenance['model']
    cache = root.parent
    (assets / model['directory']).mkdir(parents=True)
    for item in model['files']:
        source = cache / model['directory'] / item['path']
        target = assets / model['directory'] / item['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (assets / 'fixtures').mkdir()
    for item in fixtures:
        shutil.copyfile(cache / 'fixtures' / item['file'], assets / 'fixtures' / item['file'])
    manifest = root / 'device-manifest.xml'
    manifest.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android">'
                        '<instrumentation android:name="com.eilo.foundation.WakeEvaluationInstrumentation" '
                        'android:targetPackage="com.eilo" android:label="Eilo synthetic wake evaluation" /></manifest>')
    init = root / 'device.init.gradle'
    init.write_text((root / 'package.init.gradle').read_text() +
                   'gradle.afterProject { p ->\n if (p.path == ":app") {\n'
                   ' p.android.sourceSets.debug.java.srcDir(' + json.dumps(str(HERE / 'tests/android-shared')) + ')\n'
                   ' p.android.sourceSets.debug.java.srcDir(' + json.dumps(str(HERE / 'tests/android-device')) + ')\n'
                   ' p.android.sourceSets.debug.assets.srcDir(' + json.dumps(str(assets.parent)) + ')\n'
                   ' p.android.sourceSets.debug.manifest.srcFile(' + json.dumps(str(manifest)) + ')\n'
                   ' p.dependencies.add("debugImplementation", "junit:junit:4.13.2")\n'
                   ' }\n}\n')
    project = HERE.parents[1] / 'apps/mobile/android'
    env = dict(os.environ, JAVA_HOME=str(args.java_home), ANDROID_HOME=str(args.android_sdk))
    run([project / 'gradlew', '-p', project, '-I', init, ':app:assembleDebug', '--offline', '--max-workers=2'], timeout=900, env=env)
    apk = project / 'app/build/outputs/apk/debug/app-debug.apk'
    package = json.loads((root / 'package-results.json').read_text())
    verify_apk(apk, package['packaged_hashes'])
    run([args.android_sdk / 'build-tools/37.0.0/zipalign', '-c', '-P', '16', '4', apk])
    device('install', '-r', apk)
    execution = device('shell', 'am', 'instrument', '-w', 'com.eilo/com.eilo.foundation.WakeEvaluationInstrumentation', timeout=900).stdout
    if 'eilo_wake_evaluation=PASS' not in execution or 'INSTRUMENTATION_CODE: -1' not in execution:
        raise ValueError('Android instrumentation failed')
    report = json.loads(device('exec-out', 'run-as', 'com.eilo', 'cat', 'files/wake-android-results.json').stdout)
    if report.get('runtime_loader_probe') != 'PASS: Android System.loadLibrary and linked version probe':
        raise ValueError('Android loader evidence missing')
    verify_report(report, fixtures, runtime_loader_probe='PASS: Android System.loadLibrary and linked version probe')
    if device('shell', 'run-as', 'com.eilo', 'test', '!', '-e', 'files/wake-evaluation').returncode != 0:
        raise ValueError('temporary evaluation assets remain')
    report.update({'android_execution': 'PASS: Android API35 ARM64 emulator; synthetic only',
                   'android_api': device('shell', 'getprop', 'ro.build.version.sdk').stdout.strip(),
                   'page_size': device('shell', 'getconf', 'PAGESIZE').stdout.strip(),
                   'apk_sha256': digest(apk), 'temporary_assets_removed': True,
                   'unique_audio_count': len({item['sha256'] for item in fixtures})})
    device('shell', 'run-as', 'com.eilo', 'rm', 'files/wake-android-results.json')
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        print('Android execution evaluation failed: emulator, integrity, build or synthetic checks.', file=sys.stderr)
        sys.exit(2)
