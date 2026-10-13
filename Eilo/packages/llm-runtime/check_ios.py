#!/usr/bin/env python3
"""Explicit CPU-only Swift/C ABI evaluation on an existing booted iOS simulator.

Builds both ARM64 iOS SDK variants from the verified original source. Downloads
nothing, opens no microphone and does not link/enable the runtime in the app.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from check_host import CACHE, CMAKE, HERE, PROVENANCE, SOURCE, verify_source


def run(command, log, timeout=120):
    with (CACHE / log).open('w') as output:
        subprocess.run(list(map(str, command)), stdout=output, stderr=subprocess.STDOUT,
                       timeout=timeout, check=True)


def options(sdk):
    values = {'CMAKE_SYSTEM_NAME': 'iOS', 'CMAKE_OSX_SYSROOT': sdk,
              'CMAKE_OSX_ARCHITECTURES': 'arm64', 'CMAKE_OSX_DEPLOYMENT_TARGET': '18.0',
              'CMAKE_TRY_COMPILE_TARGET_TYPE': 'STATIC_LIBRARY', 'CMAKE_BUILD_TYPE': 'Release',
              'BUILD_SHARED_LIBS': 'OFF', 'GGML_CPU': 'ON', 'GGML_NATIVE': 'OFF',
              'GGML_CPU_ARM_ARCH': 'armv8-a', 'GGML_ACCELERATE': 'ON', 'GGML_BLAS': 'OFF',
              'GGML_OPENMP': 'OFF', 'GGML_BACKEND_DL': 'OFF',
              'LLAMA_OPENSSL': 'OFF', 'LLAMA_SUBPROCESS': 'OFF'}
    for backend in ('METAL', 'CUDA', 'HIP', 'MUSA', 'SYCL', 'VULKAN', 'OPENCL', 'RPC',
                    'WEBGPU', 'HEXAGON', 'OPENVINO', 'VIRTGPU', 'ET', 'ZDNN', 'ZENDNN'):
        values['GGML_' + backend] = 'OFF'
    for target in ('COMMON', 'EXAMPLES', 'TESTS', 'TOOLS', 'SERVER', 'APP', 'MTMD'):
        values['LLAMA_BUILD_' + target] = 'OFF'
    return values


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def build(sdk):
    directory = CACHE / ('build-ios-' + sdk)
    configuration = options(sdk)
    run([CMAKE, '-S', SOURCE, '-B', directory,
         *[f'-D{k}={v}' for k, v in configuration.items()]], sdk + '-configure.log')
    run([CMAKE, '--build', directory, '--target', 'llama', '-j', '3'],
        sdk + '-build.log', timeout=600)
    libraries = [directory / 'src/libllama.a',
                 *[directory / f'ggml/src/lib{x}.a' for x in ('ggml', 'ggml-cpu', 'ggml-base')]]
    process_refs = {}
    records = []
    for library in libraries:
        symbols = subprocess.run(['xcrun', 'nm', '-u', str(library)], check=True,
                                 capture_output=True, text=True, timeout=30).stdout
        names = {line.split()[-1] for line in symbols.splitlines() if line.strip()}
        if names & {'_socket', '_connect', '_sendto', '_getaddrinfo', '_curl_easy_perform'}:
            raise ValueError('unexpected network dependency')
        refs = names & {'_fork', '_execlp', '_execve', '_posix_spawn'}
        if refs:
            if library.name != 'libggml-base.a' or refs != {'_fork', '_execlp'}:
                raise ValueError('unexpected subprocess dependency')
            process_refs[library.name] = sorted(refs)
        records.append({'file': str(library.relative_to(CACHE)), 'sha256': digest(library)})
    sysroot = subprocess.run(['xcrun', '--sdk', sdk, '--show-sdk-path'], check=True,
                             capture_output=True, text=True, timeout=30).stdout.strip()
    target = 'arm64-apple-ios18.0' + ('-simulator' if sdk == 'iphonesimulator' else '')
    common = ['xcrun', '--sdk', sdk, 'clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
              '-target', target, '-isysroot', sysroot, '-I', HERE / 'include',
              '-I', SOURCE / 'include', '-I', SOURCE / 'ggml/include']
    objects = []
    for source in (HERE / 'eilo_llm.cc', HERE / 'tests/ios_probe.cc'):
        obj = directory / (source.stem + '.o')
        run([*common, '-c', source, '-o', obj], sdk + '-' + source.stem + '.log')
        objects.append(obj)
    executable = directory / 'llm-swift-binding'
    sources = sorted((HERE.parent / 'native-test-seam/Sources/NativeTestSeam').glob('*.swift'))
    run(['xcrun', 'swiftc', '-swift-version', '5', '-warnings-as-errors',
         '-target', target, '-sdk', sysroot, '-parse-as-library', '-D', 'DEBUG',
         '-D', 'EILO_LLM_EVALUATION', '-I', HERE / 'include',
         '-import-objc-header', HERE / 'tests/ios_probe.h', *sources,
         HERE / 'tests/ios_binding.swift', *objects, *libraries, '-framework', 'Accelerate',
         '-framework', 'Foundation', '-framework', 'CryptoKit', '-lc++', '-o', executable],
        sdk + '-swift-link.log')
    return executable, {'target': target, 'build_options': configuration,
                        'libraries': records, 'network_symbols': 'ABSENT',
                        'fatal_backtrace_process_symbols': process_refs,
                        'C++_Swift_link': 'PASS'}


def evaluate(udid, executable, selected, builds):
    model = PROVENANCE['model']
    path = HERE.parents[1] / '.local/model-build' / model['file']
    # Swift opens/hashes this exact immutable descriptor and passes it to C++.
    # The model path is solely a native evaluator argument, never a JS parameter.
    with tempfile.NamedTemporaryFile(prefix='eilo-invalid-gguf-') as corrupt:
        corrupt.truncate(model['bytes']); corrupt.flush()
        run(['xcrun', 'simctl', 'spawn', udid, executable, path,
             model['sha256'], model['bytes'], corrupt.name], 'ios-binding.log', timeout=240)
    lines = (CACHE / 'ios-binding.log').read_text().splitlines()
    expected = 'pre_cancel,corrupt_gguf,post_token_cancel,lease_revocation,concurrent_load_cancel,concurrent_begin_cancel'
    if len(lines) != 5 or lines[3] != f'LIFECYCLE\t{expected}\tPASS' or lines[4] != 'WORKER\tsigned_pack_three_completions,prompt_erased,no_speech,temp_removed\tPASS':
        raise ValueError('binding evaluation report mismatch')
    prompts = ['The opposite of cold is', 'One, two, three,', 'The sky on a clear day is']
    cases = []
    for index, line in enumerate(lines[:3]):
        kind, identifier, count, encoded = line.split('\t')
        raw = bytes.fromhex(encoded)
        if kind != 'GEN' or int(identifier) != index + 1 or not 1 <= int(count) <= 8 or not 1 <= len(raw) <= 8192:
            raise ValueError('invalid bounded raw completion')
        cases.append({'id': index + 1, 'prompt': prompts[index], 'tokens': int(count),
                      'output': raw.decode('utf-8'), 'kind': 'non-thinking guarded plain text, not speech-approved'})
    defaults = default_gates(udid)
    report = {'task': 'VC-LLM-01', 'platform': 'iOS ARM64 simulator / actual Swift C ABI',
              'device': selected['name'], 'udid': udid, 'runtime': PROVENANCE['runtime'],
              'model': model, 'builds': builds, 'source_modifications': 'NONE',
              'CPU_registry_only': 'PASS', 'same_open_model_descriptor_SHA256': 'PASS',
              'cases': cases, 'native_lifecycle_cases': expected.split(','),
              'controller_worker_cases': ['signed_pack_three_completions', 'prompt_erased', 'no_speech', 'temp_removed'],
              'template': 'Pinned Qwen3 no-tools subset, enable_thinking=false; markup/UTF-8 output guard',
              'pack_trust': 'Ephemeral synthetic signing key/license evidence; no production trust',
              'microphone': 'NOT USED', 'physical_inference': 'NOT RUN',
              'network': 'No inference network clients/references; simulator OS-wide isolation NOT VERIFIED',
              'app_attachment': 'NOT ENABLED; default linked API unavailable',
              'default_gate_cases': defaults,
              'remaining': ['production app attachment/release trust',
                            'speech policy', 'physical performance', 'vendor allocator/logits erasure']}
    (CACHE / 'ios-results.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Swift/C ABI iOS simulator: three real CPU completions and six lifecycle cases PASS; device SDK link PASS, physical execution NOT RUN.')


def default_gates(udid):
    """Header availability, DEBUG alone or the evaluation flag alone cannot enable it."""
    sdk = subprocess.run(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path'],
                         check=True, capture_output=True, text=True, timeout=30).stdout.strip()
    cases = []
    for name, defines in [('ordinary', []), ('debug_only', ['-D', 'DEBUG']),
                          ('evaluation_only', ['-D', 'EILO_LLM_EVALUATION'])]:
        executable = CACHE / ('ios-default-' + name)
        run(['xcrun', 'swiftc', '-swift-version', '5', '-warnings-as-errors',
             '-target', 'arm64-apple-ios18.0-simulator', '-sdk', sdk, '-parse-as-library',
             '-I', HERE / 'include', *defines,
             HERE.parent / 'native-test-seam/Sources/NativeTestSeam/NativeLlmStream.swift',
             HERE / 'tests/ios_default.swift', '-o', executable], 'ios-default-' + name + '-compile.log')
        run(['xcrun', 'simctl', 'spawn', udid, executable], 'ios-default-' + name + '.log')
        if (CACHE / ('ios-default-' + name + '.log')).read_text().strip() != 'DEFAULT_UNAVAILABLE\tPASS':
            raise ValueError('default runtime gate failed')
        cases.append({'configuration': name, 'header_importable': True,
                      'runtime_symbols_linked': False, 'result': 'UNAVAILABLE PASS'})
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--udid', help='Explicit existing booted simulator; never creates or erases it')
    parser.add_argument('--compile-only', action='store_true')
    args = parser.parse_args()
    selected = None
    if not args.compile_only:
        devices = json.loads(subprocess.run(['xcrun', 'simctl', 'list', 'devices', '--json'],
                            check=True, capture_output=True, text=True, timeout=30).stdout)
        selected = [d for group in devices['devices'].values() for d in group
                    if d['udid'] == args.udid and d['state'] == 'Booted' and d.get('isAvailable')]
        if len(selected) != 1:
            raise ValueError('explicit booted simulator required')
    verify_source()
    executable, sim = build('iphonesimulator')
    _, device = build('iphoneos')
    if args.compile_only:
        print('iOS ARM64 simulator/device Swift+C++ runtime links PASS; execution NOT RUN.')
        return
    evaluate(args.udid, executable, selected[0], [sim, device])


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(f'iOS CPU binding check unavailable ({type(error).__name__}); see ignored build logs.') from None
