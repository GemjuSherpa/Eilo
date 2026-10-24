#!/usr/bin/env python3
"""Explicit offline file-fed probe. Requires an already running ARM64 API35 emulator."""
import argparse
import hashlib
import json
import pathlib
import struct
import subprocess
import wave

HERE = pathlib.Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent
REMOTE = '/data/local/tmp/eilo-sdk-score-probe'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source(source):
    manifest = json.loads((HERE.parent / 'asr-confidence-probe/source-manifest.json').read_text())
    for item in manifest['files']:
        rel = pathlib.PurePosixPath(item['path'])
        if rel.is_absolute() or '..' in rel.parts:
            raise ValueError('invalid source path')
        path = source / rel
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing regular source')
        data = path.read_bytes()
        blob = b'blob ' + str(len(data)).encode() + b'\0' + data
        if len(data) != item['bytes'] or hashlib.sha1(blob).hexdigest() != item['git_blob_sha1']:
            raise ValueError('source integrity failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('source', 'cache', 'build', 'ndk', 'android-sdk', 'cmake', 'output'):
        parser.add_argument('--' + key, type=pathlib.Path, required=True)
    parser.add_argument('--serial', choices=['emulator-5554'], required=True)
    args = parser.parse_args()
    for key in ('source', 'cache', 'build', 'ndk', 'android_sdk', 'cmake', 'output'):
        setattr(args, key, getattr(args, key).resolve())
    verify_source(args.source)
    provenance = json.loads((HERE.parent / 'asr-runtime/provenance.json').read_text())
    model = args.cache / provenance['model']['directory']
    for item in provenance['model']['files']:
        path = model / item['file']
        if path.stat().st_size != item['bytes'] or digest(path) != item['local_sha256']:
            raise ValueError('model integrity failed')
    ort = args.cache / 'android-0.1.5/jni/arm64-v8a/libonnxruntime.so'
    if digest(ort) != '86e85022fc539963177e478c8e9a8a8219bc3b0d7515bf5297a62986dbc45e7a':
        raise ValueError('ORT integrity failed')
    if args.ndk.name != '27.1.12297006':
        raise ValueError('requires the existing pinned NDK')
    if args.output.exists():
        raise ValueError('refusing to overwrite report')
    if args.build.exists():raise ValueError('refusing to reuse SDK probe build')
    args.build.mkdir(parents=True)
    from overlay import generate
    overlay_pins=generate(args.source,args.build/'overlay')
    def build_run(command):
        with (args.build / 'build.log').open('a') as log:
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=300)
    build_run([str(args.cmake), '-S', str(HERE), '-B', str(args.build),
               '-DCMAKE_TOOLCHAIN_FILE=' + str(args.ndk / 'build/cmake/android.toolchain.cmake'),
               '-DANDROID_ABI=arm64-v8a', '-DANDROID_PLATFORM=android-26',
               '-DSOURCE_ROOT=' + str(args.source), '-DORT_LIBRARY=' + str(ort), '-DOVERLAY='+str(args.build/'overlay')])
    build_run([str(args.cmake), '--build', str(args.build), '-j', '2'])
    if sum(p.stat().st_size for p in args.build.rglob('*') if p.is_file()) > 5 * 1024**3:
        raise ValueError('build space limit exceeded')
    adb = args.android_sdk / 'platform-tools/adb'
    def run(*command, check=True):
        return subprocess.run([str(adb), '-s', args.serial, *command], check=check,
                              capture_output=True, text=True, timeout=180)
    if (run('shell', 'getprop', 'ro.kernel.qemu').stdout.strip() != '1' or
        run('shell', 'getprop', 'ro.product.cpu.abi').stdout.strip() != 'arm64-v8a' or
        run('shell', 'getprop', 'ro.build.version.sdk').stdout.strip() != '35'):
        raise ValueError('requires the explicitly selected API35 ARM64 emulator')
    if run('shell', 'test', '-e', REMOTE, check=False).returncode == 0:
        raise ValueError('remote probe directory already exists; review before cleanup')
    fixtures = json.loads((HERE.parent / 'asr-runtime/tests/fixtures.json').read_text())
    binary = args.build / 'sdk-score-probe'
    cxx = args.ndk / 'toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/lib/aarch64-linux-android/libc++_shared.so'
    results = []
    run('shell', 'mkdir', REMOTE)
    try:
        for path in (binary, ort, cxx, model):
            run('push', str(path), REMOTE + '/')
        run('shell', 'chmod', '700', REMOTE + '/sdk-score-probe')
        command = f'LD_LIBRARY_PATH={REMOTE} {REMOTE}/sdk-score-probe {REMOTE}/{model.name} {REMOTE}/input.f32'
        def invoke(raw):
            input_path = args.build / 'input.f32'
            input_path.write_bytes(raw)
            run('push', str(input_path), REMOTE + '/input.f32')
            return run('shell', command, check=False)
        for case in fixtures['cases']:
            path = args.cache / 'fixtures' / case['file']
            if digest(path) != case['sha256']:
                raise ValueError('fixture integrity failed')
            with wave.open(str(path), 'rb') as audio:
                if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth(), audio.getnframes()) != (16000, 1, 2, case['samples']):
                    raise ValueError('invalid fixture')
                raw = audio.readframes(case['samples'])
            samples = struct.unpack('<' + 'h' * (len(raw) // 2), raw)
            result = invoke(struct.pack('<' + 'f' * len(samples), *(x / 32768 for x in samples)))
            if result.returncode:
                partial=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
                stage=[line for line in result.stderr.splitlines() if line.startswith('SDK score probe unavailable: ')]
                (args.build/'failed-case.json').write_text(json.dumps({'case':case['id'],'completed_paths':partial,'stage':stage},indent=2)+'\n')
                raise RuntimeError('native fixture failed: ' + case['id'])
            lines = [line for line in result.stdout.splitlines() if line.startswith('{')]
            if len(lines) != 6:
                raise ValueError('missing native aggregate')
            record = {'case':case['id'],'paths':[json.loads(line) for line in lines[:5]],'faults':json.loads(lines[5])}
            results.append(record)
            print('Verified fixture:', case['id'], flush=True)
        rejected = []
        for name, raw in [('empty', b''), ('unaligned', b'x'), ('nan', struct.pack('<f', float('nan'))), ('out_of_range', struct.pack('<f', 2))]:
            result = invoke(raw)
            if result.returncode == 0 or '{' in result.stdout:
                raise ValueError('invalid input produced a score')
            rejected.append(name)
    finally:
        run('shell', 'rm', '-rf', REMOTE)
        (args.build / 'input.f32').unlink(missing_ok=True)
    pins = {name: digest(HERE / name) for name in ['main.cpp', 'score_trace.h', 'overlay.py', 'CMakeLists.txt', 'check_android.py']}
    report = {'version': 1, 'status': 'SDK_PATH_DIAGNOSTIC_ONLY', 'platform': 'Android API35 ARM64 emulator',
              'calibrated': False, 'policy_authorized': False, 'physical': 'NOT_RUN',
              'source_commit': '234f60faa0eb388b01cdf7e60aca232af37aefda', 'source_pins': pins,'overlay_pins':overlay_pins,'upstream_inventory_sha256':digest(HERE.parent/'asr-confidence-probe/source-manifest.json'),
              'binary_sha256': digest(binary), 'ort_sha256': digest(ort), 'cxx_sha256': digest(cxx),
              'model_provenance_sha256': digest(HERE.parent / 'asr-runtime/provenance.json'),
              'fixtures_sha256': digest(HERE.parent / 'asr-runtime/tests/fixtures.json'),
              'rejected_inputs': rejected, 'cases': results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as out:
        out.write(json.dumps(report, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
