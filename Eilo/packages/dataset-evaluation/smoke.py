"""Synthetic scoring/reporting CI smoke; no real speech/model/downloads."""
import argparse
import json
import math
from pathlib import Path
import tempfile
from audio import RATE, write_wav
from benchmark import report, validate_manifest
from manifests import canonical_digest, sha256
from noise import compare, mix
from reporting import export


def smoke(output):
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        clean = [int(12000 * math.sin(i * 0.1)) for i in range(RATE)]
        samples, mixing = mix(clean, [1000, -1000, 250, -250, 500], 10, 17)
        path = root / 'tone.wav'
        pcm_sha = write_wav(path, samples)
        case = {'id': 'a' * 24, 'task': 'asr', 'reference': 'synthetic token', 'samples': RATE,
                'slice': 'synthetic/snr10', 'split': 'test', 'path': path.name,
                'sha256': sha256(path), 'pcm_sha256': pcm_sha, 'mix': mixing}
        manifest = {'schema_version': 1, 'rate': RATE, 'kind': 'synthetic', 'dataset': 'synthetic',
                    'release': '1', 'cases': [case]}
        validate_manifest(manifest, root)
        value = {'schema_version': 1, 'manifest_sha256': canonical_digest(manifest),
                 'adapter': {'kind': 'synthetic', 'name': 'CI fixed scoring fixture (no recognition)',
                             'binary_sha256': sha256(__file__), 'model_sha256': '0' * 64,
                             'config_sha256': canonical_digest({'fixture': 'v1'})},
                 'cases': [{'id': case['id'], 'transcript': 'synthetic token', 'seconds': 0}]}
        measured = report(manifest, value)
        export(measured, output)
        export(report(manifest), Path(output) / 'not-run')
        regression = compare(measured, measured, {'wer': 0})
        (Path(output) / 'regression.json').write_text(json.dumps(regression, indent=2) + '\n')
        return measured


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    smoke(parser.parse_args().output)
    print('Synthetic smoke PASS; no public-corpus or physical recognition result.')
