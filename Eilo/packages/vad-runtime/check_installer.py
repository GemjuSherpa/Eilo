"""Offline signed VAD/ASR installer evaluation with approved cached assets only.
No microphone, production trust, download, package install or physical acceptance.
"""
import argparse
import array
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import wave

from check_native import HERE, run as native_run, verify, sha256, require

def run(args):
    try:
        return native_run(args)
    except subprocess.CalledProcessError as error:
        print((error.stderr or "")[-4000:], file=sys.stderr)
        raise ValueError("native evaluation failed; no acceptance result produced") from None

ASR = HERE.parent / 'asr-runtime'
NAMES = {'adapter.ort', 'cross_kv.ort', 'decoder_kv.ort', 'encoder.ort',
         'frontend.model.ort', 'frontend.weights.ort', 'streaming_config.json', 'tokenizer.bin'}


def verified_asr(cache):
    """Fail before native execution on any archive, extracted artifact or model mismatch."""
    record = json.loads((ASR / 'provenance.json').read_text())
    for platform in ('host', 'ios'):
        group = record[platform]
        require(sha256(cache / group['archive']) == group['publisher_sha256'], 'ASR archive changed')
        for item in group['files']:
            require(sha256(cache / item['path']) == item['sha256'], 'ASR runtime changed')
    files = record['model']['files']
    require(len(files) == 8 and {r['file'] for r in files} == NAMES, 'ASR inventory changed')
    model = cache / record['model']['directory']
    for item in files:
        file = model / item['file']
        require(file.is_file() and not file.is_symlink() and file.stat().st_size == item['bytes']
                and sha256(file) == item['local_sha256'], 'ASR model changed')
    return model, record


def verify_fixture(cache):
    item = next(r for r in json.loads((ASR / 'tests/fixtures.json').read_text())['cases'] if r['id'] == 'question')
    file = cache / 'fixtures' / item['file']
    require(sha256(file) == item['sha256'], 'synthetic fixture changed')
    with wave.open(str(file), 'rb') as wav:
        require((wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()) ==
                (1, 2, 16000, item['samples']), 'synthetic WAV format changed')
        pcm = array.array('h', wav.readframes(wav.getnframes()))
    if sys.byteorder != 'little':
        pcm.byteswap()
    output = array.array('f', (sample / 32768 for sample in pcm))
    if sys.byteorder != 'little':
        output.byteswap()
    return output.tobytes(), item


def compile_ios(output, asr_cache, vad_cache):
    sdk = run(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path']).strip()
    target = ['-target', 'arm64-apple-ios18.0-simulator', '-isysroot', sdk]
    moon = asr_cache / 'ios-0.1.5/Moonshine.xcframework/ios-arm64_x86_64-simulator'
    obj = output / 'eilo_asr.o'
    run(['xcrun', 'clang++', *target, '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', ASR / 'include',
         '-I', moon / 'Headers', '-c', ASR / 'eilo_asr.cc', '-o', obj])
    names = {'_eilo_asr_' + name for name in ('create', 'accept', 'text', 'destroy')}
    exports = output / 'asr.exports'
    exports.write_text('\n'.join(sorted(names)) + '\n')
    dynamic = output / 'libeilo_installer_asr.dylib'
    run(['xcrun', 'clang++', *target, '-dynamiclib', obj, moon / 'libmoonshine.a', '-framework', 'Accelerate',
         '-framework', 'Foundation', '-Wl,-twolevel_namespace', '-Wl,-exported_symbols_list,' + str(exports),
         '-Wl,-install_name,@rpath/' + dynamic.name, '-o', dynamic])
    require(set(run(['xcrun', 'nm', '-gUj', dynamic]).splitlines()) == names, 'ASR symbol isolation failed')
    require('TWOLEVEL' in run(['xcrun', 'otool', '-hv', dynamic]), 'ASR namespace isolation failed')
    headers = vad_cache / 'ios/onnxruntime.xcframework/ios-arm64/onnxruntime.framework/Headers'
    objects = []
    for source in ('eilo_vad.cc', 'eilo_vad_onnx.cc'):
        obj = output / (Path(source).stem + '.o')
        run(['xcrun', 'clang++', *target, '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', HERE / 'include',
             '-I', headers, '-c', HERE / source, '-o', obj])
        objects.append(obj)
    framework = vad_cache / 'ios/onnxruntime.xcframework/ios-arm64_x86_64-simulator'
    sources = sorted((HERE.parent / 'native-test-seam/Sources/NativeTestSeam').glob('*.swift'))
    binary = output / 'installer-probe'
    run(['xcrun', 'swiftc', '-parse-as-library', *target[:2], '-sdk', sdk, '-D', 'DEBUG',
         '-D', 'EILO_VAD_EVALUATION', '-D', 'EILO_ASR_EVALUATION', '-I', HERE / 'include', '-I', ASR / 'include',
         *sources, HERE / 'tests/swift_installer_probe.swift', *objects, dynamic,
         '-Xlinker', '-rpath', '-Xlinker', '@executable_path', '-F', framework, '-framework', 'onnxruntime',
         '-framework', 'CoreML', '-framework', 'Accelerate', '-framework', 'Foundation', '-framework', 'CryptoKit',
         '-lc++', '-o', binary])
    return binary, dynamic


PHASES = ('speech16', 'speech48', 'quiet', 'stop-final', 'replace-final', 'idle-stop', 'stale-ticket', 'corrupt-pack')


def validate_result(report, scope):
    require(isinstance(report, dict) and set(report) == {'scope', 'synthetic', 'worker_verified',
            'physical', 'production', 'lab_signing', 'cases'}, 'unexpected native report fields')
    require(report.get('scope') == scope and report.get('synthetic') is True
            and report.get('worker_verified') is True and report.get('physical') == 'NOT_RUN'
            and report.get('production') == 'NOT_ENABLED' and report.get('lab_signing') == 'EPHEMERAL_ES256',
            'native scope or acceptance changed')
    rows = report.get('cases')
    require(isinstance(rows, list) and len(rows) == len(PHASES)
            and all(isinstance(r, dict) for r in rows) and tuple(r.get('case') for r in rows) == PHASES,
            'all installer cases required in order')
    counts = ('vad_opens', 'vad_closes', 'vad_calls', 'asr_opens', 'asr_closes', 'asr_accept_calls',
              'asr_finals', 'recognized', 'metadata', 'source_rate', 'normalized_samples')
    for row in rows:
        require(set(row) == set(counts) | {'case', 'installed', 'transcript_sha256'},
                'unexpected native case fields')
        phase = row['case']
        require(all(type(row.get(k)) is int and 0 <= row[k] <= 480000 for k in counts), 'invalid native counters')
        require(type(row.get('installed')) is bool and row['source_rate'] == (48000 if phase == 'speech48' else 16000),
                'invalid attachment or source rate')
        require(row['vad_opens'] == row['vad_closes'] and row['asr_opens'] == row['asr_closes'], 'unclosed native handles')
        positive = phase in ('speech16', 'speech48')
        denied = phase in ('stale-ticket', 'corrupt-pack')
        require(row['installed'] is not denied, 'stale/corrupt setup accepted or live setup rejected')
        require(row['vad_opens'] == (0 if denied else 1), 'native VAD path not exercised')
        asr = positive or phase in ('stop-final', 'replace-final')
        require(row['asr_opens'] == int(asr) and row['asr_finals'] == int(asr)
                and (row['asr_accept_calls'] > 0 if asr else row['asr_accept_calls'] == 0), 'ASR boundary not exercised')
        require(row['recognized'] == int(positive) and row['metadata'] == int(positive or phase == 'quiet'), 'stale/missing result')
        text = row.get('transcript_sha256')
        require(isinstance(text, str) and (len(text) == 64 and all(c in '0123456789abcdef' for c in text) if positive else text == ''),
                'missing positive transcript or leaked stale transcript')
        require((row['normalized_samples'] > 0 if positive else row['normalized_samples'] == (80000 if phase == 'quiet' else 0)),
                'normalized sample accounting changed')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('asr-cache', 'vad-cache', 'vad-model', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--udid', required=True)
    args = parser.parse_args()
    asr_cache, vad_cache, model, output = [p.resolve() for p in (args.asr_cache, args.vad_cache, args.vad_model, args.output)]
    verify(vad_cache, model)
    asr_model, record = verified_asr(asr_cache)
    raw, fixture = verify_fixture(asr_cache)
    devices = json.loads(run(['xcrun', 'simctl', 'list', 'devices', 'booted', '--json']))
    require(any(d['udid'] == args.udid and d['name'] == 'iPhone 18 Pro' and d['isAvailable']
                for group in devices['devices'].values() for d in group), 'same booted simulator required')
    require(not output.exists(), 'refusing to overwrite evidence')
    output.mkdir(parents=True)
    binary, dynamic = compile_ios(output, asr_cache, vad_cache)
    with tempfile.TemporaryDirectory(prefix='eilo-signed-speech-') as folder:
        stage = Path(folder)
        for source in (binary, dynamic):
            shutil.copy2(source, stage / source.name)
            require(sha256(source) == sha256(stage / source.name), 'staged binary changed')
        pins = []
        for index, item in enumerate(record['model']['files']):
            pins.append({'id': 'asr-' + str(index), 'filename': item['file'], 'source': str(asr_model / item['file']),
                         'sha256': item['local_sha256'], 'bytes': item['bytes']})
        pins.append({'id': 'vad', 'filename': 'silero.onnx', 'source': str(model), 'sha256': sha256(model), 'bytes': model.stat().st_size})
        manifest = stage / 'pins.json'
        manifest.write_text(json.dumps(pins))
        audio = stage / 'synthetic.f32'
        audio.write_bytes(raw)
        result = json.loads(run(['xcrun', 'simctl', 'spawn', args.udid, stage / binary.name, manifest, audio]))
    validate_result(result, "IOS_SIMULATOR_SIGNED_SPEECH_INSTALLER")
    result.update({'schema_version': 1, 'fixture_sha256': fixture['sha256'], 'vad_model_sha256': sha256(model),
                   'asr_model_files': [{'file': row['file'], 'sha256': row['local_sha256']} for row in record['model']['files']],
                   'probe_sha256': sha256(binary), 'asr_wrapper_sha256': sha256(dynamic),
                   'android_execution': 'NOT_RUN', 'physical_gates': 'NOT_RUN'})
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Real signed VAD/ASR installer: iOS simulator eight-case execution PASS; physical NOT_RUN.')


if __name__ == '__main__':
    main()
