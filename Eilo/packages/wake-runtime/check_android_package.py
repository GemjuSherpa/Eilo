#!/usr/bin/env python3
"""Explicit offline Debug APK evaluation; no default packaging, microphone or device claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

from check_android import build_android_jni, run, verify_candidates
from check_host import HERE, digest

ABIS = ('arm64-v8a', 'armeabi-v7a', 'x86', 'x86_64')
LIBRARIES = ('libonnxruntime.so', 'libsherpa-onnx-c-api.so', 'libeilo_wake_jni.so')
SYSTEM_LIBRARIES = {'libandroid.so', 'liblog.so', 'libm.so', 'libdl.so', 'libc.so'}


def verify_elf(program_headers, dynamic, abi):
    loads = [line.split() for line in program_headers.splitlines() if line.strip().startswith('LOAD ')]
    if not loads:
        raise ValueError('missing ELF load segments')
    alignments = [int(row[-1], 16) for row in loads]
    if abi in ('arm64-v8a', 'x86_64') and any(value < 16384 or value & (value - 1) for value in alignments):
        raise ValueError('64-bit ELF is not 16 KB aligned')
    needed = re.findall(r'\(NEEDED\).*\[([^]]+)\]', dynamic)
    if any(name not in SYSTEM_LIBRARIES | set(LIBRARIES) for name in needed):
        raise ValueError('unpackaged native dependency')
    return {'load_alignments': alignments, 'needed': needed}


def verify_apk(apk, expected):
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('duplicate APK entries')
        actual = {name for name in names if Path(name).name in LIBRARIES}
        if actual != set(expected):
            raise ValueError('missing or unexpected wake APK entries')
        for name, checksum in expected.items():
            entry = archive.getinfo(name)
            if entry.compress_type != zipfile.ZIP_STORED or hashlib.sha256(archive.read(name)).hexdigest() != checksum:
                raise ValueError('packaged library compression or integrity failed')
    return {'wake_library_entries': len(expected), 'packaged_hashes': expected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ndk', required=True, type=Path)
    parser.add_argument('--java-home', required=True, type=Path)
    parser.add_argument('--android-sdk', required=True, type=Path)
    args = parser.parse_args()
    if 'Pkg.Revision = 27.1.12297006' not in (args.ndk / 'source.properties').read_text():
        raise ValueError('unexpected NDK version')
    root, host, _ = verify_candidates()
    report_path = root / 'package-results.json'
    report_path.unlink(missing_ok=True)
    build_android_jni(root, host, args.ndk)
    stage = root / 'package-jni'
    if stage.exists():
        shutil.rmtree(stage)  # Only this tool's generated ignored directory.
    stage.mkdir()
    readelf = args.ndk / 'toolchains/llvm/prebuilt/darwin-x86_64/bin/llvm-readelf'
    expected, elf = {}, {}
    for abi in ABIS:
        (stage / abi).mkdir()
        for name in LIBRARIES:
            source = root / ('build' if name == 'libeilo_wake_jni.so' else 'jniLibs') / abi / name
            target = stage / abi / name
            shutil.copyfile(source, target)
            key = f'lib/{abi}/{name}'
            expected[key] = digest(target)
            elf[key] = verify_elf(run([readelf, '-lW', target]).stdout, run([readelf, '-dW', target]).stdout, abi)
    init = root / 'package.init.gradle'
    init.write_text('gradle.afterProject { p ->\n if (p.path == ":app") {\n'
                    ' p.android.sourceSets.debug.jniLibs.srcDir(' + json.dumps(str(stage)) + ')\n'
                    ' p.android.packaging.jniLibs.keepDebugSymbols.addAll(' + json.dumps(['**/' + name for name in LIBRARIES]) + ')\n'
                    ' }\n}\n')
    project = HERE.parents[1] / 'apps/mobile/android'
    apk = project / 'app/build/outputs/apk/debug/app-debug.apk'
    apk.unlink(missing_ok=True)
    env = dict(os.environ, JAVA_HOME=str(args.java_home), ANDROID_HOME=str(args.android_sdk))
    run([project / 'gradlew', '-p', project, '-I', init, ':app:assembleDebug', '--offline', '--max-workers=2'], timeout=900, env=env)
    report = verify_apk(apk, expected)
    run([args.android_sdk / 'build-tools/37.0.0/zipalign', '-c', '-P', '16', '4', apk])
    # Preserve explicit evaluation evidence separately; a later normal build replaces app-debug.apk.
    shutil.copyfile(apk, root / 'wake-evaluation-debug.apk')
    report.update({'scope': 'explicit Debug APK evaluation only', 'apk_sha256': digest(apk),
                   'elf': elf, 'zip_alignment': 'PASS: zipalign -c -P 16 4',
                   'android_execution': 'NOT RUN: no Android device/emulator',
                   'default_readiness': 'unchanged; unavailable', 'microphone': 'not used'})
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.SubprocessError):
        print('Android package evaluation failed: integrity, ELF, build or APK checks.', file=sys.stderr)
        sys.exit(2)
