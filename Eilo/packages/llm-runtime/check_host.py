#!/usr/bin/env python3
"""Explicit offline CPU-core evaluation using existing local assets; no downloader.

Only frozen synthetic prompts are used. Python orchestrates the build/test;
inference itself executes in-process C++ without Python, HTTP or cloud inference.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import tarfile
import tempfile
import time

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
CACHE = WORKSPACE / '.local/llm'
PROVENANCE = json.loads((HERE / 'provenance.json').read_text())
PIN = PROVENANCE['runtime']['commit']
SOURCE = CACHE / f'llama.cpp-{PIN}'
BUILD = CACHE / 'build-cpu'
CMAKE = WORKSPACE / '.local/model-build/venv/bin/cmake'
PROFILE = '(version 1)(allow default)(deny network*)(deny process-fork)'


def digest(stream):
    return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_tree(archive, source, prefix):
    """Reject edited/extra source and nonregular/traversing archive entries."""
    if source.is_symlink() or not source.is_dir():
        raise ValueError('invalid source root')
    expected = set()
    with tarfile.open(archive) as tar:
        for item in tar:
            parts = Path(item.name).parts
            if not parts or parts[0] != prefix or any(p in ('..', '') for p in parts):
                raise ValueError('invalid source archive path')
            if item.isdir():
                continue
            if not item.isfile() or len(parts) < 2:
                raise ValueError('invalid source archive entry')
            relative = Path(*parts[1:])
            if relative in expected:
                raise ValueError('duplicate source archive entry')
            expected.add(relative)
            path = source / relative
            if path.is_symlink() or not path.is_file():
                raise ValueError('source entry missing or replaced')
            with path.open('rb') as local, tar.extractfile(item) as original:
                if digest(local) != digest(original):
                    raise ValueError('source entry changed')
    actual = set()
    for path in source.rglob('*'):
        if path.is_symlink():
            raise ValueError('source contains a symlink')
        if path.is_file():
            actual.add(path.relative_to(source))
    if actual != expected or not expected:
        raise ValueError('source inventory changed')


def verify_source():
    archive = CACHE / 'llama-v0.6.0.tar.gz'
    with archive.open('rb') as stream:
        if digest(stream) != PROVENANCE['runtime']['source_archive_sha256']:
            raise ValueError('runtime archive integrity failed')
    verify_tree(archive, SOURCE, SOURCE.name)


def run(command, log, timeout=120, **kwargs):
    with (CACHE / log).open('w') as stream:
        subprocess.run([str(x) for x in command], stdout=stream, stderr=subprocess.STDOUT,
                       check=True, timeout=timeout, **kwargs)


def compile_contract():
    includes = ['-I' + str(HERE / 'include'), '-I' + str(SOURCE / 'include'),
                '-I' + str(SOURCE / 'ggml/include')]
    base = ['xcrun', 'clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', *includes,
            str(HERE / 'eilo_llm.cc')]
    run([*base, '-fsanitize=address,undefined', HERE / 'tests/contract.cc', '-o', CACHE / 'contract'], 'contract-compile.log')
    run([CACHE / 'contract'], 'contract.log')
    result = (CACHE / 'contract.log').read_text().strip()
    if result != '27 scripted C ABI lifecycle scenarios PASS':
        raise ValueError('contract report mismatch')
    return base


def build_runtime():
    options = {'CMAKE_BUILD_TYPE': 'Release', 'BUILD_SHARED_LIBS': 'OFF', 'GGML_CPU': 'ON',
               'GGML_ACCELERATE': 'ON', 'GGML_BLAS': 'OFF', 'GGML_OPENMP': 'OFF',
               'GGML_BACKEND_DL': 'OFF', 'LLAMA_OPENSSL': 'OFF', 'LLAMA_SUBPROCESS': 'OFF'}
    for backend in ('METAL', 'CUDA', 'HIP', 'MUSA', 'SYCL', 'VULKAN', 'OPENCL', 'RPC',
                    'WEBGPU', 'HEXAGON', 'OPENVINO', 'VIRTGPU', 'ET', 'ZDNN', 'ZENDNN'):
        options['GGML_' + backend] = 'OFF'
    for target in ('COMMON', 'EXAMPLES', 'TESTS', 'TOOLS', 'SERVER', 'APP', 'MTMD'):
        options['LLAMA_BUILD_' + target] = 'OFF'
    run([CMAKE, '-S', SOURCE, '-B', BUILD, *[f'-D{k}={v}' for k, v in options.items()]], 'configure.log')
    run([CMAKE, '--build', BUILD, '--target', 'llama', '-j', '3'], 'build.log', timeout=600)
    libraries = [BUILD / 'src/libllama.a', *[BUILD / f'ggml/src/lib{name}.a' for name in ('ggml', 'ggml-cpu', 'ggml-base')]]
    process_refs = {}
    for path in libraries:
        symbols = subprocess.run(['xcrun', 'nm', '-u', str(path)], capture_output=True,
                                 text=True, check=True, timeout=30).stdout
        names = {line.split()[-1] for line in symbols.splitlines() if line.strip()}
        if names & {'_socket', '_connect', '_sendto', '_getaddrinfo', '_curl_easy_perform'}:
            raise ValueError('unexpected network dependency')
        refs = names & {'_fork', '_execlp', '_execve', '_posix_spawn'}
        if refs:
            # Official ggml fatal-backtrace code has fork/execlp references.
            # Report them truthfully; inference denies fork and Eilo installs
            # content-free fatal hooks. Do not call them absent from the binary.
            if path.name != 'libggml-base.a' or refs != {'_fork', '_execlp'}:
                raise ValueError('unexpected subprocess dependency')
            process_refs[path.name] = sorted(refs)
    return libraries, options, process_refs


def evaluate(base, libraries, options, process_refs):
    run([*base, HERE / 'tests/host.cc', *libraries, '-framework', 'Accelerate', '-o', CACHE / 'host'], 'host-compile.log')
    model = WORKSPACE / '.local/model-build' / PROVENANCE['model']['file']
    fd = os.open(model, os.O_RDONLY | os.O_NOFOLLOW)
    start = time.monotonic()
    with os.fdopen(fd, 'rb') as verified, tempfile.TemporaryFile() as corrupt:
        info = os.fstat(verified.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != PROVENANCE['model']['bytes'] or digest(verified) != PROVENANCE['model']['sha256']:
            raise ValueError('model integrity failed')
        verified.seek(0)
        # Sparse generic invalid GGUF, not a second copied model or personal data.
        corrupt.truncate(PROVENANCE['model']['bytes'])
        command = ['/usr/bin/sandbox-exec', '-p', PROFILE,
                   str(CACHE / 'host'), str(verified.fileno()), str(corrupt.fileno())]
        run(command, 'host.log', timeout=240, pass_fds=(verified.fileno(), corrupt.fileno()))
    lines = (CACHE / 'host.log').read_text().splitlines()
    if len(lines) != 5 or lines[0] != 'NETWORK\tIPv4_TCP,IPv6_TCP,IPv4_UDP,process_fork\tDENIED' or not lines[-1].startswith('LIFECYCLE\t') or not lines[-1].endswith('\tPASS'):
        raise ValueError('native report mismatch')
    prompts = ['The opposite of cold is', 'One, two, three,', 'The sky on a clear day is']
    cases = []
    for index, line in enumerate(lines[1:4]):
        kind, identifier, count, byte_hex = line.split('\t')
        raw = bytes.fromhex(byte_hex)
        if kind != 'GEN' or int(identifier) != index + 1 or not 1 <= int(count) <= 8 or not raw or len(raw) > 8192:
            raise ValueError('invalid bounded generation report')
        cases.append({'id': int(identifier), 'prompt': prompts[index], 'tokens': int(count),
                      'output': raw.decode('utf-8'), 'kind': 'raw completion, not speech-approved'})
    result = {'task': 'VC-LLM-01', 'platform': f'{platform.system()} {platform.machine()} native CPU',
              'runtime': PROVENANCE['runtime'], 'model': PROVENANCE['model'], 'build_options': options,
              'contract_scenarios': 27, 'sanitizers': 'ASan/UBSan PASS (adapter/scripted backend only)',
              'native_lifecycle_cases': lines[-1].split('\t')[1].split(','),
              'network': {'policy': 'all network operations denied for inference process',
                          'IPv4_TCP': 'DENIED', 'IPv6_TCP': 'DENIED', 'IPv4_UDP': 'DENIED'},
              'process_fork': 'DENIED', 'CPU_devices_only': 'PASS',
              'static_library_network_symbols': 'ABSENT', 'fatal_backtrace_process_symbols': process_refs,
              'cases': cases, 'evaluation_seconds_including_hashing': round(time.monotonic() - start, 3),
              'physical': 'NOT RUN', 'production_readiness': 'NOT ENABLED',
              'remaining': ['mobile bindings/pack lease/controller integration', 'non-thinking template',
                            'speech policy', 'vendor allocator/logits retention audit', 'phone performance']}
    (CACHE / 'host-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print('27 scripted lifecycle scenarios, three real CPU completions and six real lifecycle cases PASS; inference network probes denied.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract-only', action='store_true')
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    verify_source()
    base = compile_contract()
    if args.contract_only:
        print('27 scripted C ABI lifecycle scenarios PASS with ASan/UBSan.')
        return
    libraries, options, process_refs = build_runtime()
    evaluate(base, libraries, options, process_refs)


if __name__ == '__main__':
    main()
