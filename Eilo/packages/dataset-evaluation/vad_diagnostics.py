"""Execute pinned native VAD on a frozen corpus without claiming annotated accuracy."""
import argparse
import json
from pathlib import Path
import time
from benchmark import PHYSICAL_GATES, validate_manifest
from manifests import canonical_digest, require, safe_path, sha256
from native_vad_adapter import SETTINGS, detect, verified_config
from audio import RATE, read_wav


def run(manifest, root, config_path):
    validate_manifest(manifest, root)
    config = verified_config(config_path)
    slices = {}
    start = time.monotonic()
    for case in manifest['cases']:
        samples = read_wav(safe_path(root, case['path']))
        segments = detect(samples, config)
        entry = slices.setdefault(case['slice'], {'clips': 0, 'audio_seconds': 0,
                                                  'detected_seconds': 0, 'segments': 0})
        entry['clips'] += 1
        entry['audio_seconds'] += len(samples) / RATE
        entry['detected_seconds'] += sum(end - begin for begin, end in segments)
        entry['segments'] += len(segments)
    return {'schema_version': 1, 'status': 'EXECUTED_UNSCORED',
            'reason': 'No reviewed time-aligned annotations; no F1/miss/false-positive claim',
            'manifest_sha256': canonical_digest(manifest), 'dataset': manifest['dataset'],
            'release': manifest['release'], 'config_sha256': sha256(config_path),
            'adapter_sha256': sha256(Path(__file__).with_name('native_vad_adapter.py')),
            'model_sha256': config['model']['sha256'], 'settings': SETTINGS,
            'slices': slices, 'elapsed_seconds': time.monotonic() - start,
            'physical_gates': {x: 'NOT_RUN' for x in PHYSICAL_GATES},
            'production_readiness': 'NOT_ENABLED'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'refusing to overwrite evidence')
    value = run(json.loads(args.manifest.read_text()), args.manifest.parent, args.config)
    args.output.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
