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
from check_installer import verify, verified_asr, verify_fixture, sha256, require, run


def framework_module():
    spec = importlib.util.spec_from_file_location('joined_framework', HERE.parent / 'asr-runtime/framework.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def source_pins():
    from check_capture_evidence import source_paths
    paths = {HERE.parents[1] / p for p in source_paths(HERE.parents[1])}
    paths.update([HERE / 'check_framework_capture.py', HERE / 'tests/ios_framework_capture.swift',
                  HERE.parent / 'wake-runtime/ios-provenance.json', HERE.parent / 'asr-runtime/framework-results.json'])
    f = framework_module()
    paths.update(HERE.parent / p for p in f.pins())
    return [dict(path=str(p.relative_to(HERE.parent)), sha256=sha256(p)) for p in sorted(paths)]



def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('asr-cache', 'vad-cache', 'vad-model', 'llm-cache', 'llm-model', 'framework', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--udid', required=True)
    a = p.parse_args()
    asr, vad, model, llm, gguf, output = [x.resolve() for x in
        (a.asr_cache, a.vad_cache, a.vad_model, a.llm_cache, a.llm_model, a.output)]
    before = source_pins()
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
    framework = framework_module()
    entries = framework.xcframework_entries(a.framework.resolve())
    expected = framework.read(HERE.parent / 'asr-runtime/framework-results.json')
    require(all(entries[k][1] == expected['frameworks'][k] for k in entries), 'framework differs from reviewed build')
    require(expected['source_pins'] == framework.pins(), 'framework source provenance changed')
    obj, libraries = framework.build_llm(llm, llm.parent / 'model-build/venv/bin/cmake', output)
    for library in libraries:
        names = {line.split()[-1] for line in run(['xcrun', 'nm', '-u', library]).splitlines() if line.strip()}
        require(not names & {'_socket', '_connect', '_sendto', '_getaddrinfo', '_curl_easy_perform'}, 'unexpected network dependency')
    sdk = run(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path']).strip()
    llm_here = HERE.parent / 'llm-runtime'
    for name in ('eilo_vad.cc', 'eilo_vad_onnx.cc'):
        run(['xcrun', 'clang++', '-target', 'arm64-apple-ios18.0-simulator', '-isysroot', sdk,
             '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', HERE.parent / 'vad-runtime/include',
             '-I', vad / 'ios/onnxruntime.xcframework/ios-arm64/onnxruntime.framework/Headers',
             '-c', HERE.parent / 'vad-runtime' / name, '-o', output / (Path(name).stem + '.o')])
    original = output / 'original/FrameworkCapture.app'
    (original / 'Frameworks').mkdir(parents=True)
    shutil.copytree(entries['iphonesimulator'][0], original / 'Frameworks/CEiloAsr.framework')
    binary = original / 'FrameworkCapture'
    sources = sorted((HERE.parent / 'native-test-seam/Sources/NativeTestSeam').glob('*.swift'))
    run(['xcrun', 'swiftc', '-swift-version', '5', '-warnings-as-errors', '-parse-as-library', '-target',
         'arm64-apple-ios18.0-simulator', '-sdk', sdk, '-D', 'DEBUG', '-D', 'EILO_VAD_EVALUATION',
         '-D', 'EILO_ASR_EVALUATION', '-D', 'EILO_LLM_EVALUATION', '-I', HERE.parent / 'vad-runtime/include',
         '-F', original / 'Frameworks', '-I', llm_here / 'include', *sources,
         HERE / 'tests/ios_framework_capture.swift', output / 'eilo_vad.o', output / 'eilo_vad_onnx.o', obj,
         *libraries, '-framework', 'CEiloAsr', '-Xlinker', '-rpath', '-Xlinker', '@executable_path/Frameworks',
         '-F', vad / 'ios/onnxruntime.xcframework/ios-arm64_x86_64-simulator', '-framework', 'onnxruntime',
         '-framework', 'CoreML', '-framework', 'Accelerate', '-framework', 'Foundation', '-framework', 'CryptoKit',
         '-framework', 'AVFoundation', '-lc++', '-o', binary])
    relocated = output / 'relocated/FrameworkCapture.app'; relocated.parent.mkdir()
    original.rename(relocated); require(not original.exists(), 'original must be absent')
    binary = relocated / 'FrameworkCapture'
    rpaths = framework.client_metadata(run(['xcrun', 'otool', '-L', binary]), run(['xcrun', 'otool', '-l', binary]))
    require(framework.inspect_bundle(relocated / 'Frameworks/CEiloAsr.framework', 'iphonesimulator') == entries['iphonesimulator'][1], 'embedded framework changed')
    with tempfile.TemporaryDirectory(prefix='eilo-framework-capture-') as folder:
        stage = Path(folder)
        pins = [dict(id='asr-' + str(i), filename=r['file'], source=str(asr_model / r['file']),
                     sha256=r['local_sha256'], bytes=r['bytes']) for i, r in enumerate(record['model']['files'])]
        pins.append(dict(id='vad', filename='silero.onnx', source=str(model), sha256=sha256(model), bytes=model.stat().st_size))
        pins.append(dict(id='llm', filename='model.gguf', source=str(gguf), sha256=provenance['model']['sha256'], bytes=gguf.stat().st_size))
        manifest = stage / 'pins.json'; manifest.write_text(json.dumps(pins))
        audio = stage / 'synthetic.f32'; audio.write_bytes(raw)
        executed = subprocess.run(list(map(str, ['xcrun', 'simctl', 'spawn', a.udid, binary, manifest, audio])),
                                  capture_output=True, text=True, timeout=660)
        (output / 'evaluation.log').write_text(executed.stdout + executed.stderr)
        require(executed.returncode == 0, 'joined evaluation failed; inspect ignored evaluation log')
        lines = [s.removeprefix('EILO_CAPTURE_RESULT\t') for s in executed.stdout.splitlines() if s.startswith('EILO_CAPTURE_RESULT\t')]
        require(len(lines) == 1, 'one aggregate report required'); result = json.loads(lines[0])
    validate(result)
    verify(vad, model); verified_asr(asr)
    require(sha256(gguf) == provenance['model']['sha256'], 'LLM model changed during execution')
    require(before == source_pins(), 'sources changed during execution')
    result.update(schema_version=1, fixture_sha256=fixture['sha256'], vad_model_sha256=sha256(model),
                  llm_model_sha256=provenance['model']['sha256'], binary_sha256=sha256(binary),
                  source_sha256=sha256(HERE / 'tests/ios_framework_capture.swift'), source_pins=before,
                  framework=entries['iphonesimulator'][1], client_rpaths=rpaths, sdk_speech_gain=0,
                  relocation='EXECUTED_WITH_ORIGINAL_CLIENT_DIRECTORY_ABSENT',
                  llm_libraries=[dict(file=str(x.relative_to(output)), sha256=sha256(x)) for x in libraries])
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Signed VAD/ASR capture -> local reply -> SDK speech PASS; synthetic simulator, physical NOT_RUN.')


def validate(result):
    require(isinstance(result, dict) and set(result) == {'scope', 'physical', 'production', 'microphone', 'confidence',
        'voice_evidence', 'cases', 'temporary_pack_removed'}, 'unexpected joined report fields')
    require(result['scope'] == 'IOS_SIMULATOR_FRAMEWORK_CAPTURE_REPLY' and result['physical'] == 'NOT_RUN'
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
