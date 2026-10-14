"""Seeded MUSAN noise variants and strict frozen-suite regression comparisons."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from audio import RATE, read_wav, write_wav
from benchmark import PHYSICAL_GATES, aggregate, number, validate_manifest
from manifests import canonical_digest, require, safe_path, sha256

NOISE_RECIPE = 'seeded-loop-rms-snr-joint-headroom-v1'
LOWER = {'wer', 'cer', 'rtf', 'vad_false_positive_rate', 'vad_miss_rate'}
HIGHER = {'command_accuracy', 'command_balanced_accuracy', 'command_target_accuracy', 'vad_f1'}


def rms(samples):
    return math.sqrt(sum(x * x for x in samples) / len(samples))


def mix(clean, noise, snr_db, seed=0):
    require(clean and noise, 'empty mixing input')
    number(snr_db, minimum=-20)
    require(snr_db <= 40 and type(seed) is int, 'invalid mixing settings')
    offset = int(hashlib.sha256(str(seed).encode()).hexdigest()[:16], 16) % len(noise)
    bed = [noise[(offset + i) % len(noise)] for i in range(len(clean))]
    clean_rms, noise_rms = rms(clean), rms(bed)
    require(clean_rms > 0 and noise_rms > 0, 'silent clean/noise cannot define SNR')
    gain = clean_rms / (noise_rms * 10 ** (snr_db / 20))
    sums = [c + n * gain for c, n in zip(clean, bed)]
    headroom = min(1, 32767 / max(abs(x) for x in sums))
    signal = [int(round(x * headroom)) for x in clean]
    added = [int(round(x * gain * headroom)) for x in bed]
    mixed = [max(-32768, min(32767, int(round(x * headroom)))) for x in sums]
    achieved = 20 * math.log10(rms(signal) / rms(added)) if rms(added) else None
    require(achieved is not None and abs(achieved - snr_db) <= 0.5, 'quantized SNR outside tolerance')
    return mixed, {'recipe': NOISE_RECIPE, 'seed': seed, 'offset_samples': offset,
                   'target_snr_db': snr_db, 'achieved_snr_db': achieved,
                   'noise_gain': gain, 'joint_gain': headroom,
                   'peak': max(abs(x) for x in mixed)}


def variants(clean_manifest, clean_root, noise_manifest, noise_root, output, snrs=(20, 10, 0), seed=0):
    validate_manifest(clean_manifest, clean_root)
    validate_manifest(noise_manifest, noise_root)
    require(clean_manifest['kind'] == noise_manifest['kind'], 'do not mix evidence kinds')
    require(noise_manifest['dataset'] in ('musan', 'synthetic'), 'reviewed MUSAN noise corpus required')
    noises = noise_manifest['cases']
    require(all(x['task'] == 'vad' and x['vad'] == [] for x in noises), 'noise-only negatives required')
    require(snrs and len(snrs) <= 10 and len(set(snrs)) == len(snrs), 'invalid SNR suite')
    require(len(clean_manifest['cases']) * len(snrs) <= 10000, 'suite too large')
    require(not Path(output).exists(), 'output already exists')
    Path(output).mkdir(parents=True)
    cases = []
    for case in clean_manifest['cases']:
        require(case['task'] in ('asr', 'commands'), 'speech reference required for noise robustness')
        clean = read_wav(safe_path(clean_root, case['path']))
        index = int(hashlib.sha256((case['id'] + ':' + str(seed)).encode()).hexdigest()[:16], 16) % len(noises)
        selected = noises[index]
        noise = read_wav(safe_path(noise_root, selected['path']))
        for snr in snrs:
            mixed, recipe = mix(clean, noise, snr, seed)
            identity = canonical_digest({'clean': case['sha256'], 'noise': selected['sha256'], 'mix': recipe})[:24]
            target = Path(output) / (identity + '.wav')
            pcm_sha = write_wav(target, mixed)
            record = copy.deepcopy(case)
            record.update({'id': identity, 'path': target.name, 'sha256': sha256(target),
                           'pcm_sha256': pcm_sha, 'parent_id': case['id'], 'noise_id': selected['id'],
                           'mix': recipe, 'slice': f"{case['slice']}/snr{snr:g}"})
            cases.append(record)
    result = {**clean_manifest, 'cases': cases, 'recipe': NOISE_RECIPE,
              'parent_manifest_sha256': canonical_digest(clean_manifest),
              'noise_manifest_sha256': canonical_digest(noise_manifest), 'mix_seed': seed}
    (Path(output) / 'manifest.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result


def validate_report(value):
    require(value['status'] == 'MEASURED' and value['cases'], 'measured nonempty baseline required')
    require(value['physical_gates'] == {x: 'NOT_RUN' for x in PHYSICAL_GATES}, 'physical gates changed')
    require(value['metrics'] == aggregate(value['cases']), 'metrics do not match cases')
    expected = {name: aggregate([x for x in value['cases'] if x['slice'] == name])
                for name in sorted({x['slice'] for x in value['cases']})}
    require(value['slices'] == expected, 'slice metrics do not match cases')
    return value


def compare(baseline, current, tolerances):
    validate_report(baseline)
    validate_report(current)
    for key in ('manifest_sha256', 'kind', 'normalization', 'scoring'):
        require(baseline[key] == current[key], 'incomparable baseline: ' + key)
    require(baseline['adapter']['config_sha256'] == current['adapter']['config_sha256'], 'adapter config changed')
    require(set(tolerances) and set(tolerances) <= LOWER | HIGHER, 'invalid metric tolerances')
    for value in tolerances.values():
        number(value)
    changes = []
    for name, old in {'all': baseline['metrics'], **baseline['slices']}.items():
        new = current['metrics'] if name == 'all' else current['slices'][name]
        for metric, tolerance in tolerances.items():
            require(metric in old and metric in new and old[metric] is not None and new[metric] is not None,
                    'requested metric unavailable: ' + metric)
            delta = new[metric] - old[metric]
            regression = delta > tolerance if metric in LOWER else -delta > tolerance
            changes.append({'slice': name, 'metric': metric, 'before': old[metric], 'after': new[metric],
                            'delta': delta, 'tolerance': tolerance, 'regression': regression})
    return {'schema_version': 1, 'status': 'FAIL' if any(x['regression'] for x in changes) else 'PASS',
            'manifest_sha256': current['manifest_sha256'], 'changes': changes,
            'physical_gates': current['physical_gates']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    mixer = sub.add_parser('mix')
    mixer.add_argument('--clean', type=Path, required=True)
    mixer.add_argument('--noise', type=Path, required=True)
    mixer.add_argument('--snr', type=float, nargs='+', default=[20, 10, 0])
    mixer.add_argument('--seed', type=int, default=0)
    mixer.add_argument('--output', type=Path, required=True)
    regression = sub.add_parser('compare')
    regression.add_argument('--baseline', type=Path, required=True)
    regression.add_argument('--current', type=Path, required=True)
    regression.add_argument('--tolerances', type=Path, required=True)
    regression.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.operation == 'mix':
        variants(json.loads(args.clean.read_text()), args.clean.parent,
                 json.loads(args.noise.read_text()), args.noise.parent, args.output, args.snr, args.seed)
    else:
        result = compare(json.loads(args.baseline.read_text()), json.loads(args.current.read_text()),
                         json.loads(args.tolerances.read_text()))
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        if result['status'] == 'FAIL':
            raise SystemExit(2)


if __name__ == '__main__':
    main()
