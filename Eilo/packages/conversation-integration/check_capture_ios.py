"""Offline file-fed signed VAD/ASR -> local reply -> SDK speech evaluation.
No microphone, physical acceptance, production activation, download or package installation.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / 'vad-runtime'))
from check_installer import compile_ios, verify, verified_asr, verify_fixture, sha256, require, run


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('asr-cache', 'vad-cache', 'vad-model', 'llm-cache', 'llm-model', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--udid', required=True)
    a = p.parse_args()
    asr, vad, model, llm, gguf, output = [x.resolve() for x in
        (a.asr_cache, a.vad_cache, a.vad_model, a.llm_cache, a.llm_model, a.output)]
    verify(vad, model); asr_model, record = verified_asr(asr); raw, fixture = verify_fixture(asr)
    provenance = json.loads((HERE.parent / 'llm-runtime/provenance.json').read_text())
    require(gguf.stat().st_size == provenance['model']['bytes'] and sha256(gguf) == provenance['model']['sha256'], 'LLM model changed')
    source = llm / ('llama.cpp-' + provenance['runtime']['commit'])
    archive = llm / 'llama-v0.6.0.tar.gz'
    require(sha256(archive) == provenance['runtime']['source_archive_sha256'], 'LLM archive changed')
    spec = importlib.util.spec_from_file_location('joined_capture_llm_host', HERE.parent / 'llm-runtime/check_host.py')
    host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)
    host.verify_tree(archive, source, source.name)
    devices = json.loads(run(['xcrun', 'simctl', 'list', 'devices', 'booted', '--json']))
    require(any(d['udid'] == a.udid and d['name'] == 'iPhone 18 Pro' and d['isAvailable']
                for rows in devices['devices'].values() for d in rows), 'same booted simulator required')
    require(not output.exists(), 'refusing to overwrite evidence'); output.mkdir(parents=True)
    # Rebuild from the verified source tree rather than trusting mutable cached libraries.
    cmake = llm.parent / 'model-build/venv/bin/cmake'
    build = output / 'llm-build'
    options = json.loads((HERE.parent / 'llm-runtime/tests/ios-results.json').read_text())['builds'][0]['build_options']
    with (output / 'llm-build.log').open('w') as log:
        subprocess.run(list(map(str, [cmake, '-S', source, '-B', build, *['-D' + k + '=' + str(v) for k, v in options.items()]])),
                       stdout=log, stderr=log, check=True, timeout=180)
        subprocess.run(list(map(str, [cmake, '--build', build, '--target', 'llama', '-j', '3'])),
                       stdout=log, stderr=log, check=True, timeout=600)
    libraries = [build / 'src/libllama.a', *[build / ('ggml/src/lib' + n + '.a') for n in ('ggml', 'ggml-cpu', 'ggml-base')]]
    for library in libraries:
        symbols = run(['xcrun', 'nm', '-u', library])
        names = {line.split()[-1] for line in symbols.splitlines() if line.strip()}
        require(not names & {'_socket', '_connect', '_sendto', '_getaddrinfo', '_curl_easy_perform'}, 'unexpected network dependency')
    _, dynamic = compile_ios(output, asr, vad)
    sdk = run(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path']).strip()
    llm_here = HERE.parent / 'llm-runtime'
    obj = output / 'eilo_llm.o'
    run(['xcrun', 'clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-target', 'arm64-apple-ios18.0-simulator',
         '-isysroot', sdk, '-I', llm_here / 'include', '-I', source / 'include', '-I', source / 'ggml/include',
         '-c', llm_here / 'eilo_llm.cc', '-o', obj])
    binary = output / 'joined-capture'
    # Protected-key provisioning is outside this speech-only executable.
    sources = sorted(x for x in (HERE.parent / 'native-test-seam/Sources/NativeTestSeam').glob('*.swift')
                     if x.name != 'ProtectedKey.swift')
    run(['xcrun', 'swiftc', '-swift-version', '5', '-warnings-as-errors', '-parse-as-library', '-target',
         'arm64-apple-ios18.0-simulator', '-sdk', sdk, '-D', 'DEBUG', '-D', 'EILO_VAD_EVALUATION',
         '-D', 'EILO_ASR_EVALUATION', '-D', 'EILO_LLM_EVALUATION', '-I', HERE.parent / 'vad-runtime/include',
         '-I', HERE.parent / 'asr-runtime/include', '-I', llm_here / 'include', *sources,
         HERE / 'tests/ios_capture.swift', output / 'eilo_vad.o', output / 'eilo_vad_onnx.o', obj,
         *libraries, dynamic, '-Xlinker', '-rpath', '-Xlinker', '@executable_path',
         '-F', vad / 'ios/onnxruntime.xcframework/ios-arm64_x86_64-simulator', '-framework', 'onnxruntime',
         '-framework', 'CoreML', '-framework', 'Accelerate', '-framework', 'Foundation', '-framework', 'CryptoKit',
         '-framework', 'AVFoundation', '-lc++', '-o', binary])
    with tempfile.TemporaryDirectory(prefix='eilo-joined-capture-') as folder:
        stage = Path(folder)
        for file in (binary, dynamic):
            shutil.copy2(file, stage / file.name)
            require(sha256(file) == sha256(stage / file.name), 'staged binary changed')
        pins = [dict(id='asr-' + str(i), filename=r['file'], source=str(asr_model / r['file']),
                     sha256=r['local_sha256'], bytes=r['bytes']) for i, r in enumerate(record['model']['files'])]
        pins.append(dict(id='vad', filename='silero.onnx', source=str(model), sha256=sha256(model), bytes=model.stat().st_size))
        pins.append(dict(id='llm', filename='model.gguf', source=str(gguf), sha256=provenance['model']['sha256'], bytes=gguf.stat().st_size))
        manifest = stage / 'pins.json'; manifest.write_text(json.dumps(pins))
        audio = stage / 'synthetic.f32'; audio.write_bytes(raw)
        executed = subprocess.run(list(map(str, ['xcrun', 'simctl', 'spawn', a.udid, stage / binary.name, manifest, audio])),
                                  capture_output=True, text=True, timeout=660)
        (output / 'evaluation.log').write_text(executed.stdout + executed.stderr)
        require(executed.returncode == 0, 'joined evaluation failed; inspect ignored evaluation log')
        lines = [s.removeprefix('EILO_CAPTURE_RESULT\t') for s in executed.stdout.splitlines() if s.startswith('EILO_CAPTURE_RESULT\t')]
        require(len(lines) == 1, 'one aggregate report required'); result = json.loads(lines[0])
    validate(result)
    result.update(schema_version=1, fixture_sha256=fixture['sha256'], vad_model_sha256=sha256(model),
                  llm_model_sha256=provenance['model']['sha256'], binary_sha256=sha256(binary),
                  source_sha256=sha256(HERE / 'tests/ios_capture.swift'),
                  llm_libraries=[dict(file=str(x.relative_to(output)), sha256=sha256(x)) for x in libraries])
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Signed VAD/ASR capture -> local reply -> SDK speech PASS; synthetic simulator, physical NOT_RUN.')


def validate(result):
    require(isinstance(result, dict) and set(result) == {'scope', 'physical', 'production', 'microphone', 'confidence',
        'voice_evidence', 'cases', 'temporary_pack_removed'}, 'unexpected joined report fields')
    require(result['scope'] == 'IOS_SIMULATOR_SIGNED_CAPTURE_REPLY' and result['physical'] == 'NOT_RUN'
            and result['production'] == 'NOT_ENABLED' and result['microphone'] == 'NOT_USED'
            and result['confidence'] == 'SYNTHETIC_0_95' and result['voice_evidence'] == 'SYNTHETIC_EXACT_VOICE_OS'
            and result['temporary_pack_removed'] is True, 'joined scope changed')
    rows = result['cases']
    require(isinstance(rows, list) and len(rows) == 3, 'three joined cases required')
    for row, phase in zip(rows, ('speech16', 'followup48', 'quiet')):
        require(set(row) == {'case', 'recognized', 'metadata', 'normalized_samples', 'reply_submitted', 'completed',
                             'transcript_sha256', 'context_messages', 'inference_worker_verified', 'llm_starts'}, 'unexpected case fields')
        require(row['case'] == phase and row['inference_worker_verified'] is True, 'joined case order/worker changed')
        for key in ('recognized', 'metadata', 'normalized_samples', 'context_messages', 'llm_starts'):
            require(type(row[key]) is int and 0 <= row[key] <= 80000, 'invalid counters')
        positive = phase != 'quiet'
        require(row['recognized'] == int(positive) and row['llm_starts'] == int(positive) and row['metadata'] == 1 and row['normalized_samples'] == (29184 if positive else 80000), 'capture accounting changed')
        require(row['reply_submitted'] is positive and row['completed'] is positive
                and row['context_messages'] == (2 if phase == 'speech16' else 4), 'reply/context changed')
        digest = row['transcript_sha256']
        require(isinstance(digest, str) and (len(digest) == 64 and all(c in '0123456789abcdef' for c in digest) if positive else digest == ''), 'transcript hash changed')
    require(rows[0]['transcript_sha256'] == rows[1]['transcript_sha256'], 'fixture recognition diverged')


if __name__ == '__main__':
    main()
