"""Explicit cached-model Android ART signed VAD/ASR evaluation. Restores normal APK.
No microphone, downloads, production activation, physical trial or network observer.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

from check_installer import ASR, HERE, verify, verified_asr, verify_fixture, sha256, require, validate_result

SCOPE = 'ANDROID_ART_SIGNED_SPEECH_INSTALLER'
LIBRARIES = ('libonnxruntime.so', 'libeilo_vad_jni.so', 'libmoonshine.so', 'libeilo_asr_jni.so')


def run(command, timeout=180, **kwargs):
    return subprocess.run(list(map(str, command)), check=True, capture_output=True,
                          text=True, timeout=timeout, **kwargs).stdout


def serial(value):
    require(type(value) is str and re.fullmatch(r'emulator-[0-9]{4,5}', value), 'explicit emulator required')
    return value


def inspect_apk(apk, aapt, evaluation):
    permissions = run([aapt, 'dump', 'permissions', apk])
    for permission in ('INTERNET', 'RECORD_AUDIO'):
        present = 'android.permission.' + permission in permissions
        require(present is not evaluation, 'APK permission profile mismatch')
    with zipfile.ZipFile(apk) as archive:
        names = set(archive.namelist())
        for name in LIBRARIES:
            present = 'lib/arm64-v8a/' + name in names
            require(present is evaluation, 'APK native package profile mismatch')
    manifest = run([aapt, 'dump', 'xmltree', apk, '--file', 'AndroidManifest.xml'])
    require(('SignedSpeechArtInstrumentation' in manifest) is evaluation, 'APK instrumentation profile mismatch')


def require_ort_symbols(moonshine_versions, runtime_symbols):
    needed = set(re.findall(r'(Ort[A-Za-z0-9_]+)@(VERS_[0-9.]+)', moonshine_versions))
    available = set(re.findall(r'(Ort[A-Za-z0-9_]+)@@?(VERS_[0-9.]+)', runtime_symbols))
    require(bool(needed) and needed <= available, 'Moonshine/ORT versioned symbol mismatch; no binary rewrite allowed')


def verify_headers(directory):
    record = json.loads((HERE / 'android-ort-header-provenance.json').read_text())
    names = {'onnxruntime_c_api.h', 'onnxruntime_cxx_api.h', 'onnxruntime_cxx_inline.h',
             'onnxruntime_float16.h', 'onnxruntime_ep_c_api.h'}
    require(record['version'] == 'v1.23.2' and record['license'] == 'MIT'
            and {row['file'] for row in record['files']} == names and len(record['files']) == 5, 'header inventory changed')
    for row in record['files']:
        path = directory / row['file']
        require(not path.is_symlink() and path.stat().st_size == row['bytes']
                and sha256(path) == row['sha256'], 'ORT source header changed')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('asr-cache', 'vad-cache', 'vad-model', 'output', 'ndk', 'java-home', 'android-sdk', 'ort-headers'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--serial', required=True, type=serial)
    args = parser.parse_args()
    asr, vad, model, output, ndk, java, sdk = [p.resolve() for p in
        (args.asr_cache, args.vad_cache, args.vad_model, args.output, args.ndk, args.java_home, args.android_sdk)]
    header_record = verify_headers(args.ort_headers.resolve())
    require(not output.exists(), 'refusing to overwrite evaluation evidence')
    verify(vad, model)
    model_root, record = verified_asr(asr)
    raw, fixture = verify_fixture(asr)
    android = record['android']
    require(sha256(asr / 'moonshine-voice-0.1.5.aar') == android['publisher_sha256'], 'ASR Android archive changed')
    for item in android['files']:
        require(sha256(asr / item['path']) == item['sha256'], 'ASR Android runtime changed')
    runtime_record = json.loads((HERE.parent / 'wake-runtime/android-provenance.json').read_text())['archive']
    require(sha256(vad / 'android' / runtime_record['file']) == runtime_record['sha256'], 'ORT Android archive changed')
    for item in runtime_record['files']:
        require(sha256(vad / 'android' / item['path']) == item['sha256'], 'ORT Android runtime changed')
    require('Pkg.Revision = 27.1.12297006' in (ndk / 'source.properties').read_text(), 'unexpected NDK')
    adb = sdk / 'platform-tools/adb'
    def device(*values, timeout=120):
        return run([adb, '-s', args.serial, *values], timeout=timeout)
    for prop, value in [('sys.boot_completed', '1'), ('ro.build.version.sdk', '35'), ('ro.product.cpu.abi', 'arm64-v8a')]:
        require(device('shell', 'getprop', prop).strip() == value, 'booted API35 ARM64 emulator required')
    output.mkdir(parents=True)
    converter_source = HERE / 'tests/android-device/convert_vad_model.cc'
    converter = output / 'convert-vad'
    run(['clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', args.ort_headers.resolve(),
         converter_source, asr / 'moonshine-voice-macos-arm64/lib/libmoonshine.a',
         '-framework', 'Accelerate', '-framework', 'Foundation', '-o', converter])
    vad_for_android = output / 'silero_vad_v5.ort'
    conversion_output = run([converter, model, vad_for_android])
    require(conversion_output.splitlines() == ['HOST_ORT_1.23.0', 'ORT_CONVERSION_PASS'], 'unexpected local converter/runtime')
    libs = output / 'jni/arm64-v8a'
    libs.mkdir(parents=True)
    tools = ndk / 'toolchains/llvm/prebuilt/darwin-x86_64/bin'
    compiler = tools / 'aarch64-linux-android26-clang++'
    moon = asr / 'android-0.1.5/jni/arm64-v8a'
    shared = moon
    headers = args.ort_headers.resolve()
    common = [compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
              '-static-libstdc++', '-Wl,--no-undefined', '-Wl,-z,max-page-size=16384']
    run([*common, '-I', HERE / 'include', '-I', headers, HERE / 'eilo_vad.cc', HERE / 'eilo_vad_onnx.cc',
         HERE / 'eilo_vad_jni.cc', HERE / 'tests/android-device/vad_model_probe.cc', '-L', shared, '-Wl,-rpath-link,' + str(shared), '-lonnxruntime',
         '-o', libs / 'libeilo_vad_jni.so'])
    moon = asr / 'android-0.1.5/jni/arm64-v8a'
    run([*common, '-I', ASR / 'include', '-I', asr / 'moonshine-voice-macos-arm64/include',
         ASR / 'eilo_asr.cc', ASR / 'eilo_asr_jni.cc', '-L', moon, '-L', shared,
         '-Wl,-rpath-link,' + str(moon), '-lmoonshine', '-o', libs / 'libeilo_asr_jni.so'])
    shutil.copyfile(shared / 'libonnxruntime.so', libs / 'libonnxruntime.so')
    shutil.copyfile(moon / 'libmoonshine.so', libs / 'libmoonshine.so')
    require_ort_symbols(run([tools / 'llvm-nm', '-D', '-u', libs / 'libmoonshine.so']),
                        run([tools / 'llvm-nm', '-D', '--defined-only', libs / 'libonnxruntime.so']))
    # One explicitly recorded ORT distribution serves both APIs. Its compatibility
    # is exercised by all native cases, not inferred from duplicate sonames.
    hashes = {name: sha256(libs / name) for name in LIBRARIES}
    for name in LIBRARIES:
        elf = run([tools / 'llvm-readelf', '-l', '-d', libs / name])
        (output / (name + '.elf.txt')).write_text(elf)
        needed = set(re.findall(r'\(NEEDED\).*\[(.*?)\]', elf))
        require(needed <= {'libonnxruntime.so', 'libmoonshine.so', 'libc.so', 'libm.so', 'libdl.so', 'liblog.so', 'libandroid.so'}, 'unexpected native dependency')
    manifest = output / 'AndroidManifest.xml'
    manifest.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android" xmlns:tools="http://schemas.android.com/tools">'
        '<uses-permission android:name="android.permission.INTERNET" tools:node="remove" />'
        '<uses-permission android:name="android.permission.RECORD_AUDIO" tools:node="remove" />'
        '<instrumentation android:name="com.eilo.foundation.SignedSpeechArtInstrumentation" android:targetPackage="com.eilo" '
        'android:label="Eilo file-fed signed speech evaluation" /></manifest>')
    init = output / 'evaluation.init.gradle'
    init.write_text('gradle.afterProject { p ->\n if(p.path == ":app") {\n'
        'p.android.sourceSets.debug.java.srcDir(' + json.dumps(str(HERE / 'tests/android-device')) + ')\n'
        'p.android.sourceSets.debug.jniLibs.srcDir(' + json.dumps(str(libs.parent)) + ')\n'
        'p.android.sourceSets.debug.manifest.srcFile(' + json.dumps(str(manifest)) + ')\n'
        'p.android.packagingOptions.jniLibs.useLegacyPackaging = true\n'
        'p.android.packagingOptions.jniLibs.keepDebugSymbols.add("**/*.so")\n }\n}\n')
    project = HERE.parents[1] / 'apps/mobile/android'
    env = dict(os.environ, JAVA_HOME=str(java), ANDROID_HOME=str(sdk))
    apk = project / 'app/build/outputs/apk/debug/app-debug.apk'
    aapt = sdk / 'build-tools/37.0.0/aapt2'
    work = 'files/signed-speech-art'
    result_path = 'files/signed-speech-art-results.json'
    owned = False
    result = None
    def gradle(extra, log):
        completed = subprocess.run([str(project / 'gradlew'), '-p', str(project), *map(str, extra),
                                   ':app:assembleDebug', '--offline', '--max-workers=2'], env=env,
                                  capture_output=True, text=True, timeout=900)
        (output / log).write_text(completed.stdout + completed.stderr)
        require(completed.returncode == 0, 'APK build failed; inspect ignored build log')
    try:
        gradle(['-I', init], 'evaluation-build.log')
        inspect_apk(apk, aapt, True)
        with zipfile.ZipFile(apk) as archive:
            for name in LIBRARIES:
                with archive.open('lib/arm64-v8a/' + name) as stream:
                    require(hashlib.file_digest(stream, 'sha256').hexdigest() == hashes[name], 'APK native bytes changed during packaging')
        apk_hash = sha256(apk)
        device('install', '-r', apk, timeout=180)
        # Refuse to destroy an existing evaluator slot or its earlier evidence.
        device('shell', 'run-as', 'com.eilo', 'test', '!', '-e', work)
        device('shell', 'run-as', 'com.eilo', 'test', '!', '-e', result_path)
        device('shell', 'run-as', 'com.eilo', 'mkdir', '-p', work + '/inputs'); owned = True
        pins = [dict(id='asr-' + str(i), filename=row['file'], sha256=row['local_sha256'], bytes=row['bytes'])
                for i, row in enumerate(record['model']['files'])]
        pins.append(dict(id='vad', filename='silero_vad_v5.ort', sha256=sha256(vad_for_android), bytes=vad_for_android.stat().st_size))
        config = {key + 'Sha': hashes[name] for key, name in zip(('runtime', 'vadJni', 'asrCore', 'asrJni'), LIBRARIES)}
        (output / 'manifest.json').write_text(json.dumps(pins))
        (output / 'input.json').write_text(json.dumps(config))
        (output / 'synthetic.f32').write_bytes(raw)
        copies = [(model_root / row['file'], 'inputs/' + row['file']) for row in record['model']['files']]
        copies += [(vad_for_android, 'inputs/silero_vad_v5.ort'), *[(output / name, name) for name in ('manifest.json', 'input.json', 'synthetic.f32')]]
        for source, name in copies:
            with source.open('rb') as stream:
                subprocess.run([str(adb), '-s', args.serial, 'exec-in', 'run-as', 'com.eilo', 'dd',
                                'of=' + work + '/' + name, 'bs=65536'], stdin=stream, capture_output=True, check=True, timeout=180)
        instrumentation = device('shell', 'am', 'instrument', '-w',
                                 'com.eilo/com.eilo.foundation.SignedSpeechArtInstrumentation', timeout=900)
        (output / 'instrumentation.log').write_text(instrumentation)
        require('eilo_signed_speech_art=PASS' in instrumentation and 'INSTRUMENTATION_CODE: -1' in instrumentation, 'Android ART evaluator failed')
        result = json.loads(device('exec-out', 'run-as', 'com.eilo', 'cat', result_path))
        validate_result(result, SCOPE)
        device('shell', 'run-as', 'com.eilo', 'test', '!', '-e', work)
    finally:
        try:
            device('shell', 'am', 'force-stop', 'com.eilo')
            if owned:
                device('shell', 'run-as', 'com.eilo', 'rm', '-rf', work, result_path)
                device('shell', 'run-as', 'com.eilo', 'test', '!', '-e', work)
        finally:
            gradle([], 'normal-restore-build.log')
            inspect_apk(apk, aapt, False)
            device('install', '-r', apk, timeout=180)
    require(result is not None, 'no native result')
    result.update(schema_version=1, runtime_profile='SINGLE_PINNED_MOONSHINE_ORT_1_23_2',
        ort_header_commit=header_record['commit'],
        abi='arm64-v8a', android_api=35, library_sha256=hashes, evaluation_apk_sha256=apk_hash,
        normal_apk_sha256=sha256(apk), temporary_files_removed=True, normal_app_restored=True,
        internet_permission='ABSENT', microphone_permission='ABSENT', fixture_sha256=fixture['sha256'],
        vad_model_sha256=sha256(vad_for_android), vad_source_model_sha256=sha256(model),
        vad_conversion={'runtime':'1.23.0','format':'ORT','optimization':'DISABLED','converter_sha256':sha256(converter_source),'bytes':vad_for_android.stat().st_size}, asr_model_files=[dict(file=r['file'], sha256=r['local_sha256']) for r in record['model']['files']],
        controller_permission_and_readiness='SYNTHETIC', network_acceptance='NOT_RUN')
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Android ART signed VAD/ASR eight-case PASS; normal APK restored; physical NOT_RUN.')


if __name__ == '__main__':
    main()
