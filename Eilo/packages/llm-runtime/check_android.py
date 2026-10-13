#!/usr/bin/env python3
"""Offline Kotlin/JNI CPU evaluation on an explicitly selected existing emulator.

Uses only already-present pinned source, model, NDK, SDK and Gradle dependencies.
The temporary Debug APK has no INTERNET permission. Always rebuilds/restores a
normal APK afterwards, preserving app data. No microphone or physical trials.
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

from check_host import CACHE, CMAKE, HERE, PROVENANCE, SOURCE, verify_source

ABIS = {'arm64-v8a': 'aarch64-linux-android26',
        'armeabi-v7a': 'armv7a-linux-androideabi26',
        'x86': 'i686-linux-android26', 'x86_64': 'x86_64-linux-android26'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command, log, timeout=120, **kwargs):
    with (CACHE / log).open('w') as output:
        subprocess.run(list(map(str, command)), check=True, timeout=timeout,
                       stdout=output, stderr=subprocess.STDOUT, **kwargs)


def options(ndk, abi):
    values = {'CMAKE_TOOLCHAIN_FILE': str(ndk / 'build/cmake/android.toolchain.cmake'),
              'ANDROID_ABI': abi, 'ANDROID_PLATFORM': 'android-26', 'ANDROID_STL': 'c++_static',
              'CMAKE_BUILD_TYPE': 'Release', 'CMAKE_POSITION_INDEPENDENT_CODE': 'ON',
              'BUILD_SHARED_LIBS': 'OFF', 'GGML_CPU': 'ON', 'GGML_NATIVE': 'OFF',
              'GGML_ACCELERATE': 'OFF', 'GGML_BLAS': 'OFF', 'GGML_OPENMP': 'OFF',
              'GGML_BACKEND_DL': 'OFF', 'GGML_LLAMAFILE': 'OFF',
              'LLAMA_OPENSSL': 'OFF', 'LLAMA_SUBPROCESS': 'OFF'}
    if abi == 'arm64-v8a':
        values['GGML_CPU_ARM_ARCH'] = 'armv8-a'
    for instruction in ('SSE42', 'AVX', 'AVX2', 'BMI2', 'FMA', 'F16C'):
        values['GGML_' + instruction] = 'OFF'
    for backend in ('METAL', 'CUDA', 'HIP', 'MUSA', 'SYCL', 'VULKAN', 'OPENCL', 'RPC',
                    'WEBGPU', 'HEXAGON', 'OPENVINO', 'VIRTGPU', 'ET', 'ZDNN', 'ZENDNN'):
        values['GGML_' + backend] = 'OFF'
    for target in ('COMMON', 'EXAMPLES', 'TESTS', 'TOOLS', 'SERVER', 'APP', 'MTMD'):
        values['LLAMA_BUILD_' + target] = 'OFF'
    return values


def build(ndk, abi, target):
    directory = CACHE / ('build-android-' + abi)
    values = options(ndk, abi)
    run([CMAKE, '-S', SOURCE, '-B', directory,
         *[f'-D{k}={v}' for k, v in values.items()]], abi + '-configure.log')
    run([CMAKE, '--build', directory, '--target', 'llama', '-j', '3'], abi + '-build.log', 900)
    libraries = [directory / 'src/libllama.a',
                 *[directory / f'ggml/src/lib{x}.a' for x in ('ggml', 'ggml-cpu', 'ggml-base')]]
    tool = ndk / 'toolchains/llvm/prebuilt/darwin-x86_64/bin'
    output = directory / 'libeilo_llm_jni.so'
    run([tool / (target + '-clang++'), '-std=c++17', '-Wall', '-Wextra', '-Werror',
         '-fPIC', '-shared', '-DEILO_LLM_EVALUATION', '-static-libstdc++', '-Wl,--no-undefined',
         '-Wl,-z,max-page-size=16384', '-I', HERE / 'include', '-I', SOURCE / 'include',
         '-I', SOURCE / 'ggml/include', HERE / 'eilo_llm.cc', HERE / 'eilo_llm_jni.cc',
         HERE / 'tests/android_probe.cc', *libraries, '-llog', '-o', output], abi + '-jni-link.log')
    symbols = subprocess.run([tool / 'llvm-nm', '-u', output], check=True, capture_output=True,
                             text=True, timeout=30).stdout
    names = {line.split()[-1].split('@')[0] for line in symbols.splitlines() if line.strip()}
    # The evaluator's explicit socket probes are expected; the inference archives
    # themselves must have no networking clients. Vendor fatal-backtrace refs are reported.
    process_refs = {}
    for library in libraries:
        raw = subprocess.run([tool / 'llvm-nm', '-u', library], check=True,
                             capture_output=True, text=True, timeout=30).stdout
        refs = {line.split()[-1] for line in raw.splitlines() if line.strip()}
        if refs & {'socket', 'connect', 'sendto', 'getaddrinfo', 'curl_easy_perform'}:
            raise ValueError('unexpected inference network dependency')
        process = refs & {'fork', 'execlp', 'execve', 'posix_spawn'}
        if process:
            if library.name != 'libggml-base.a' or process != {'fork', 'execlp'}:
                raise ValueError('unexpected subprocess dependency')
            process_refs[library.name] = sorted(process)
    if names & {'getaddrinfo', 'curl_easy_perform'}:
        raise ValueError('unexpected JNI network client')
    elf = subprocess.run([tool / 'llvm-readelf', '-l', '-d', output], check=True,
                         capture_output=True, text=True, timeout=30).stdout
    needed = re.findall(r'\(NEEDED\).*\[(.*?)\]', elf)
    if not set(needed) <= {'libc.so', 'libm.so', 'libdl.so', 'liblog.so'}:
        raise ValueError('unexpected dynamic dependency')
    loads = [line.split() for line in elf.splitlines() if line.strip().startswith('LOAD ')]
    if not loads or any(int(line[-1], 16) < 16384 for line in loads):
        raise ValueError('ELF load alignment failed')
    return output, {'abi': abi, 'target': target, 'jni_sha256': digest(output),
                    'evaluation_compile_define': 'EILO_LLM_EVALUATION',
                    'CPU_only_build_options': values, 'needed': needed,
                    'ELF_LOAD_minimum_alignment': 16384,
                    'inference_archive_network_symbols': 'ABSENT',
                    'fatal_backtrace_process_symbols': process_refs,
                    'JNI_probe_socket_symbols': 'present for explicit permission-denial probes',
                    'execution': 'NOT RUN' if abi != 'arm64-v8a' else 'pending'}


def evaluate(args, libraries, builds):
    if not re.fullmatch(r'emulator-[0-9]+', args.serial or ''):
        raise ValueError('explicit emulator required')
    adb = args.android_sdk / 'platform-tools/adb'
    def device(*values, timeout=120):
        return subprocess.run([str(adb), '-s', args.serial, *map(str, values)], check=True,
                              capture_output=True, text=True, timeout=timeout)
    for prop, expected in [('sys.boot_completed', '1'), ('ro.build.version.sdk', '35'),
                           ('ro.product.cpu.abi', 'arm64-v8a')]:
        if device('shell', 'getprop', prop).stdout.strip() != expected:
            raise ValueError('booted API35 ARM64 emulator required')
    model = HERE.parents[1] / '.local/model-build' / PROVENANCE['model']['file']
    if model.is_symlink() or model.stat().st_size != PROVENANCE['model']['bytes'] or digest(model) != PROVENANCE['model']['sha256']:
        raise ValueError('model integrity failed')
    libs = CACHE / 'android-eval-jni/arm64-v8a'
    libs.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(libraries['arm64-v8a'], libs / 'libeilo_llm_jni.so')
    manifest = CACHE / 'android-eval-manifest.xml'
    manifest.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
                        'xmlns:tools="http://schemas.android.com/tools">'
                        '<uses-permission android:name="android.permission.INTERNET" tools:node="remove" />'
                        '<instrumentation android:name="com.eilo.foundation.LlmEvaluationInstrumentation" '
                        'android:targetPackage="com.eilo" android:label="Eilo generic LLM evaluation" /></manifest>')
    init = CACHE / 'android-eval.init.gradle'
    init.write_text('gradle.afterProject { p ->\n if (p.path == ":app") {\n'
                    'p.android.sourceSets.debug.java.srcDir(' + json.dumps(str(HERE / 'tests/android-device')) + ')\n'
                    'p.android.sourceSets.debug.jniLibs.srcDir(' + json.dumps(str(libs.parent)) + ')\n'
                    'p.android.sourceSets.debug.manifest.srcFile(' + json.dumps(str(manifest)) + ')\n'
                    'p.android.packagingOptions.jniLibs.useLegacyPackaging = true\n }\n}\n')
    project = HERE.parents[1] / 'apps/mobile/android'
    env = dict(os.environ, JAVA_HOME=str(args.java_home), ANDROID_HOME=str(args.android_sdk))
    apk = project / 'app/build/outputs/apk/debug/app-debug.apk'
    work = 'files/llm-evaluation'
    report_file = 'files/llm-android-results.json'
    host_report = CACHE / 'android-results.json'
    host_report.unlink(missing_ok=True)
    try:
        run([project / 'gradlew', '-p', project, '-I', init, ':app:assembleDebug', '--offline',
             '--max-workers=2'], 'android-eval-build.log', 900, env=env)
        device('install', '-r', apk)
        device('shell', 'run-as', 'com.eilo', 'mkdir', '-p', work)
        # Generic model only; stream to the private evaluator slot, never to shared storage.
        with model.open('rb') as stream:
            subprocess.run([str(adb), '-s', args.serial, 'exec-in', 'run-as', 'com.eilo', 'dd',
                            f'of={work}/model.gguf', 'bs=65536'], stdin=stream, capture_output=True,
                           check=True, timeout=180)
        device('shell', 'run-as', 'com.eilo', 'chmod', '400', work + '/model.gguf')
        result = device('shell', 'am', 'instrument', '-w',
                        'com.eilo/com.eilo.foundation.LlmEvaluationInstrumentation', timeout=900).stdout
        (CACHE / 'android-instrumentation.log').write_text(result)
        if 'eilo_llm_evaluation=PASS' not in result or 'INSTRUMENTATION_CODE: -1' not in result:
            raise ValueError('native Android evaluation failed')
        report = json.loads(device('exec-out', 'run-as', 'com.eilo', 'cat', report_file).stdout)
        expected_lifecycle = ['pre_cancel', 'corrupt_gguf', 'post_token_cancel', 'lease_revocation',
                              'concurrent_load_cancel', 'concurrent_begin_cancel', 'destroy_during_load']
        if (len(report.get('cases', [])) != 3 or report.get('CPU_registry_only') != 'PASS'
                or report.get('network_probes') != 'DENIED' or report.get('INTERNET_permission') != 'ABSENT'
                or report.get('model_sha256') != PROVENANCE['model']['sha256']
                or report.get('destroy_load_worker_gate_observed') is not True
                or report.get('destroy_load_native_status') not in (0, -2)
                or report.get('native_lifecycle_cases') != expected_lifecycle):
            raise ValueError('native Android report failed')
        device('shell', 'run-as', 'com.eilo', 'test', '!', '-e', work)
        builds[0]['execution'] = 'ART/JNI API35 ARM64 emulator PASS'
        report.update({'runtime': PROVENANCE['runtime'], 'model': PROVENANCE['model'],
                       'builds': builds, 'source_modifications': 'NONE', 'apk_sha256': digest(apk),
                       'page_size': device('shell', 'getconf', 'PAGESIZE').stdout.strip(),
                       'temporary_model_removed': True, 'physical_inference': 'NOT RUN',
                       'app_attachment': 'NOT ENABLED; normal runtime/model default unavailable'})
        device('shell', 'run-as', 'com.eilo', 'rm', report_file)
        print('Android ART/JNI: three real CPU completions and native lifecycle cases PASS; network socket probes denied.')
    finally:
        try:
            # Also stop a timed-out evaluator before cleanup, preventing late writes.
            device('shell', 'am', 'force-stop', 'com.eilo')
            device('shell', 'run-as', 'com.eilo', 'rm', '-rf', work, report_file)
        finally:
            # Attempt restoration even if temporary-file cleanup failed. Never
            # uninstall or erase app data; finish the normal build before install.
            run([project / 'gradlew', '-p', project, ':app:assembleDebug', '--offline', '--max-workers=2'],
                'android-normal-restore.log', 900, env=env)
            with zipfile.ZipFile(apk) as archive:
                if any('eilo_llm_jni' in name or 'llm-evaluation' in name for name in archive.namelist()):
                    raise ValueError('normal APK retains evaluation files')
                for name in archive.namelist():
                    if re.fullmatch(r'classes[0-9]*\.dex', name):
                        dex = archive.read(name)
                        if any(marker in dex for marker in (b'Lcom/eilo/foundation/LlmEvaluationInstrumentation;',
                                                            b'Lcom/eilo/foundation/LlmEvaluationProbe;')):
                            raise ValueError('normal APK retains evaluation source')
            device('install', '-r', apk)
            if 'LlmEvaluationInstrumentation' in device('shell', 'pm', 'list', 'instrumentation').stdout:
                raise ValueError('normal package retains instrumentation')
            print('Normal Android APK restored without evaluation library/assets/source; app data preserved.')
    report['normal_APK_evaluation_contents'] = 'ABSENT'
    report['normal_restoration'] = 'PASS'
    host_report.write_text(json.dumps(report, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('ndk', 'java-home', 'android-sdk'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--serial')
    parser.add_argument('--compile-only', action='store_true')
    args = parser.parse_args()
    if 'Pkg.Revision = 27.1.12297006' not in (args.ndk / 'source.properties').read_text():
        raise ValueError('pinned NDK required')
    verify_source()
    libraries, builds = {}, []
    for abi, target in ABIS.items():
        libraries[abi], record = build(args.ndk, abi, target)
        builds.append(record)
        print(f'{abi} CPU/JNI link and ELF checks PASS', flush=True)
    (CACHE / 'android-builds.json').write_text(json.dumps(builds, indent=2) + '\n')
    if not args.compile_only:
        evaluate(args, libraries, builds)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Android CPU binding check unavailable ({type(error).__name__}); see ignored build logs.') from None
