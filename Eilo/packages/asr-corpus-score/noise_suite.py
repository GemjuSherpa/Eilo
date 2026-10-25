"""Bounded paired noise diagnostics using existing approved frozen corpus caches."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from report import validate
from run_android import read_json, sha
from diagnostics import need
from manifests import canonical_digest, safe_path
from benchmark import validate_manifest
from audio import read_wav
from noise import mix, NOISE_RECIPE

HERE = Path(__file__).resolve().parent
SNRS = (20, 10, 0)


def validate_pairing(clean, noisy, noise):
    """Require one variant per parent/SNR, and exact unchanged evaluation labels."""
    need(clean['kind'] == noisy['kind'] == noise['kind'] == 'public_corpus')
    need(clean['dataset'] == noisy['dataset'] == 'common_voice' and noise['dataset'] == 'musan')
    need(noisy['parent_manifest_sha256'] == canonical_digest(clean))
    need(noisy['noise_manifest_sha256'] == canonical_digest(noise))
    need(noisy['recipe'] == NOISE_RECIPE and type(noisy['mix_seed']) is int)
    need(noisy['receipt'] == clean['receipt'] and noisy['release'] == clean['release'])
    parents = {c['id']: c for c in clean['cases']}
    noises = {c['id']: c for c in noise['cases']}
    need(1 <= len(parents) <= 30 and len(parents) == len(clean['cases']))
    need(all(c['task'] == 'asr' and c['split'] == 'test' for c in parents.values()))
    need(all(c['task'] == 'vad' and c['vad'] == [] for c in noises.values()))
    seen = set()
    groups = {snr: [] for snr in SNRS}
    for case in noisy['cases']:
        need(case['parent_id'] in parents and case['noise_id'] in noises)
        parent = parents[case['parent_id']]
        snr = case['mix']['target_snr_db']
        need(type(snr) is int and snr in SNRS)
        pair = (case['parent_id'], snr)
        need(pair not in seen)
        seen.add(pair)
        for field in ('reference', 'speaker', 'task', 'samples', 'split', 'source_sha256'):
            need(case[field] == parent[field])
        need(case['slice'] == parent['slice'] + '/snr' + str(snr))
        need(case['mix']['seed'] == noisy['mix_seed'])
        groups[snr].append(case)
    need(len(seen) == len(parents) * len(SNRS))
    return groups


def verify_audio(clean, clean_root, noisy, noisy_root, noise, noise_root):
    for manifest, root in ((clean, clean_root), (noisy, noisy_root), (noise, noise_root)):
        validate_manifest(manifest, root)
    groups = validate_pairing(clean, noisy, noise)
    parents = {c['id']: c for c in clean['cases']}
    noises = {c['id']: c for c in noise['cases']}
    for case in noisy['cases']:
        parent, bed = parents[case['parent_id']], noises[case['noise_id']]
        expected, recipe = mix(read_wav(safe_path(clean_root, parent['path'])),
                               read_wav(safe_path(noise_root, bed['path'])),
                               case['mix']['target_snr_db'], noisy['mix_seed'])
        need(recipe == case['mix'])
        need(expected == read_wav(safe_path(noisy_root, case['path'])))
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('clean', 'noisy', 'noise', 'source', 'cache', 'build', 'ndk', 'android-sdk', 'cmake', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--serial', choices=['emulator-5554'], required=True)
    args = parser.parse_args()
    need(not args.build.exists() and not args.output.exists())
    clean, noisy, noise = (read_json(p) for p in (args.clean, args.noisy, args.noise))
    groups = verify_audio(clean, args.clean.parent, noisy, args.noisy.parent, noise, args.noise.parent)
    pins = {name: sha(HERE / name) for name in ('noise_suite.py', 'run_android.py', 'diagnostics.py', 'main.cpp')}
    args.build.mkdir(parents=True)
    args.output.mkdir(parents=True)
    for snr, cases in groups.items():
        subset = copy.deepcopy(noisy)
        subset['cases'] = cases
        # In the ignored source cache so safe_path still enforces the original audio root.
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', prefix='.score-subset-', dir=args.noisy.parent, delete=False) as file:
            manifest_path = Path(file.name)
            json.dump(subset, file, allow_nan=False)
        try:
            command = [sys.executable, str(HERE / 'run_android.py')]
            for name in ('source', 'cache', 'ndk', 'android_sdk', 'cmake', 'serial'):
                command += ['--' + name.replace('_', '-'), str(getattr(args, name))]
            command += ['--manifest', str(manifest_path), '--build', str(args.build / ('snr' + str(snr))),
                        '--output', str(args.output / ('snr' + str(snr) + '.json'))]
            subprocess.run(command, check=True, timeout=7200)
            validate(read_json(args.output / ('snr' + str(snr) + '.json')))
        finally:
            manifest_path.unlink(missing_ok=True)
    need(pins == {name: sha(HERE / name) for name in pins})
    receipt = dict(schema_version=1, purpose='PAIRED_NOISE_SCORE_DIAGNOSTIC',
                   clean_manifest_sha256=canonical_digest(clean), noisy_manifest_sha256=canonical_digest(noisy),
                   noise_manifest_sha256=canonical_digest(noise), source_pins=pins,
                   parents=len(clean['cases']), variants=len(noisy['cases']), snrs=list(SNRS),
                   pairing='SAME_PARENTS_CORRELATED_NOT_INDEPENDENT', threshold_fitting='NOT_PERFORMED',
                   physical='NOT_RUN', production='NOT_ENABLED',
                   reports={str(snr): sha(args.output / ('snr' + str(snr) + '.json')) for snr in SNRS})
    (args.output / 'suite.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
