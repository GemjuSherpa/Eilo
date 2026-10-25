"""Evaluate frozen fresh curator dev/test cohorts, without fitting or enabling confidence."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
import time
import wave

from shared import HERE, CORPUS, SDK, need, read, sha, source_pins, protocol, canonical_digest, safe_path, validate_manifest, score_response, summarize, SOURCES, unique
sys.path.insert(0, str(SDK))
from overlay import generate

REMOTE = '/data/local/tmp/eilo-fresh-split'


def verify_cohorts(root, prior_path):
    policy = protocol()
    evidence = read(root / 'selection.json')
    need(evidence['source_pins'] == source_pins())
    prior = read(prior_path)
    validate_manifest(prior, prior_path.parent)
    need(evidence['prior_manifest_sha256'] == canonical_digest(prior))
    need(evidence['protocol_sha256'] == sha(HERE / 'protocol.json'))
    seen = {key: {c[key] for c in prior['cases']} for key in ('speaker', 'source_sha256', 'pcm_sha256')}
    from shared import normalize
    texts = {normalize(c['reference']) for c in prior['cases']}
    manifests = {}
    for split, partition, count in (('dev', 'validation', policy['development_count']), ('test', 'test', policy['test_count'])):
        m = read(root / split / 'manifest.json')
        validate_manifest(m, root / split)
        need(m['receipt'] == prior['receipt'] and m['dataset'] == 'common_voice')
        need(len(m['cases']) == count and all(c['split'] == partition and c['task'] == 'asr' for c in m['cases']))
        need(evidence['partitions'][split]['manifest_sha256'] == canonical_digest(m))
        from collections import Counter
        counts = Counter(c['speaker'] for c in m['cases'])
        need(max(counts.values()) <= policy['max_clips_per_speaker'])
        need(evidence['partitions'][split]['cases'] == count and evidence['partitions'][split]['speakers'] == len(counts))
        for key in seen:
            values = {c[key] for c in m['cases']}
            need(not values & seen[key])
            if key != 'speaker':
                need(len(values) == count)
            seen[key].update(values)
        normalized = {normalize(c['reference']) for c in m['cases']}
        need(len(normalized) == count and not normalized & texts)
        texts.update(normalized)
        manifests[split] = m
    return evidence, manifests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cohorts', 'prior', 'source', 'cache', 'build', 'ndk', 'android-sdk', 'cmake', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--serial', choices=['emulator-5554'], required=True)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.resolve())
    need(not args.build.exists() and not args.output.exists())
    evidence, manifests = verify_cohorts(args.cohorts, args.prior)
    pins = source_pins()
    provenance = read(HERE.parent / 'asr-runtime/provenance.json')
    model = args.cache / provenance['model']['directory']
    for item in provenance['model']['files']:
        path = model / item['file']
        need(path.is_file() and path.stat().st_size == item['bytes'] and sha(path) == item['local_sha256'])
    ort = args.cache / 'android-0.1.5/jni/arm64-v8a/libonnxruntime.so'
    need(sha(ort) == '86e85022fc539963177e478c8e9a8a8219bc3b0d7515bf5297a62986dbc45e7a')
    need(args.ndk.name == '27.1.12297006')
    args.build.mkdir(parents=True)
    overlay = generate(args.source, args.build / 'overlay')
    need(overlay == read(SDK / 'overlay-expected.json'))
    commands = [[str(args.cmake), '-S', str(CORPUS), '-B', str(args.build),
        '-DCMAKE_TOOLCHAIN_FILE=' + str(args.ndk / 'build/cmake/android.toolchain.cmake'), '-DANDROID_ABI=arm64-v8a', '-DANDROID_PLATFORM=android-26',
        '-DSOURCE_ROOT=' + str(args.source), '-DORT_LIBRARY=' + str(ort), '-DOVERLAY=' + str(args.build / 'overlay'), '-DSCORE_HEADERS=' + str(SDK)],
        [str(args.cmake), '--build', str(args.build), '-j', '2']]
    with (args.build / 'build.log').open('x') as log:
        for command in commands:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
    need(sum(p.stat().st_size for p in args.build.rglob('*') if p.is_file()) < 5 * 1024**3)
    adb = args.android_sdk / 'platform-tools/adb'
    def run(*command, check=True):
        return subprocess.run([str(adb), '-s', args.serial, *command], capture_output=True, text=True, check=check, timeout=180)
    need(run('shell', 'getprop', 'ro.kernel.qemu').stdout.strip() == '1')
    need(run('shell', 'getprop', 'ro.product.cpu.abi').stdout.strip() == 'arm64-v8a')
    need(run('shell', 'getprop', 'ro.build.version.sdk').stdout.strip() == '35')
    need(run('shell', 'test', '-e', REMOTE, check=False).returncode == 1)
    binary = args.build / 'corpus-score-probe'
    cxx = args.ndk / 'toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/lib/aarch64-linux-android/libc++_shared.so'
    need(sha(cxx) == read(CORPUS / 'corpus-results.json')['provenance']['cxx_sha256'])
    rows, reports = {}, {}
    run('shell', 'mkdir', REMOTE)
    try:
        for path in (binary, ort, cxx, model):
            run('push', str(path), REMOTE + '/')
        run('shell', 'chmod', '700', REMOTE + '/corpus-score-probe')
        for split, manifest in manifests.items():
            rows[split] = []
            for case in manifest['cases']:
                path = safe_path(args.cohorts / split, case['path'])
                need(sha(path) == case['sha256'])
                with wave.open(str(path), 'rb') as audio:
                    need((audio.getframerate(), audio.getnchannels(), audio.getsampwidth(), audio.getnframes()) == (16000, 1, 2, case['samples']))
                    values = struct.unpack('<' + 'h' * case['samples'], audio.readframes(case['samples']))
                temp = args.build / 'input.f32'
                temp.write_bytes(struct.pack('<' + 'f' * len(values), *(x / 32768 for x in values)))
                run('push', str(temp), REMOTE + '/input.f32')
                start = time.monotonic()
                response = run('shell', f'LD_LIBRARY_PATH={REMOTE} timeout 120 {REMOTE}/corpus-score-probe {REMOTE}/{model.name} {REMOTE}/input.f32', check=False)
                seconds = time.monotonic() - start
                if response.returncode:
                    result = dict(schema_version=1, paths=[dict(source=s, status='UNAVAILABLE', reason='COLLECTOR_ERROR') for s in SOURCES])
                else:
                    lines = [line for line in response.stdout.splitlines() if line.startswith('{')]
                    need(len(lines) == 1 and len(lines[0].encode()) <= 32768)
                    # Strict duplicate/nonfinite checking without ever persisting the hypothesis.
                    def reject(_):
                        raise ValueError('invalid native JSON')
                    result = json.loads(lines[0], object_pairs_hook=unique, parse_constant=reject)
                rows[split].append(score_response(case, result, seconds))
                del result, response
                (args.build / 'progress-private.json').write_text(json.dumps(rows, indent=2, allow_nan=False) + '\n')
                print(split, 'case', len(rows[split]), 'of', len(manifest['cases']), flush=True)
            sources = summarize(rows[split])
            for source in sources:
                source['scope'] = 'CURATOR_DEV_DIAGNOSTIC_ONLY' if split == 'dev' else 'CURATOR_TEST_DIAGNOSTIC_ONLY'
            reports[split] = dict(partition='CURATOR_DEV' if split == 'dev' else 'CURATOR_TEST', cases_total=len(rows[split]), sources=sources,
                                  private_counts_sha256=canonical_digest(rows[split]))
        rejected = []
        for name, raw in [('empty', b''), ('unaligned', b'x'), ('nan', struct.pack('<f', float('nan'))), ('out_of_range', struct.pack('<f', 2))]:
            (args.build / 'input.f32').write_bytes(raw)
            run('push', str(args.build / 'input.f32'), REMOTE + '/input.f32')
            result = run('shell', f'LD_LIBRARY_PATH={REMOTE} timeout 120 {REMOTE}/corpus-score-probe {REMOTE}/{model.name} {REMOTE}/input.f32', check=False)
            need(result.returncode != 0 and '{' not in result.stdout)
            rejected.append(name)
    finally:
        run('shell', 'rm', '-rf', REMOTE)
        (args.build / 'input.f32').unlink(missing_ok=True)
    need(pins == source_pins())
    report = dict(schema_version=1, purpose=protocol()['purpose'], selection=evidence, source_pins=pins,
        model_bundle_sha256=canonical_digest(provenance['model']), ort_sha256=sha(ort), runtime_sha256=sha(binary),
        cxx_sha256=sha(cxx), overlay_pins=overlay, partitions=reports, rejected_inputs=rejected,
        threshold_fitting='NOT_PERFORMED', model_training_overlap='UNKNOWN', native_calibration='NOT_ESTABLISHED',
        threshold_authorization='NOT_GRANTED', production='NOT_ENABLED', physical='NOT_RUN')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
        output.write(json.dumps(report, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
