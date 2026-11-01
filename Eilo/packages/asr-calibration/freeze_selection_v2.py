"""Write the public hash-only record for the frozen private S05 cohort."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from audit_v2 import HERE, PROTOCOL
from select_audit_v2 import pins as selection_pins

sys.path.insert(0, str(HERE.parent / 'asr-fresh-split'))
from shared import canonical_digest

sys.path.insert(0, str(HERE.parent / 'dataset-evaluation'))
from benchmark import validate_manifest

SELECTION_PURPOSE = 'PRIVATE_FROZEN_CONFIDENCE_AUDIT_COHORT'
FREEZE_PURPOSE = 'S05_VC_TURN_10_SELECTION_FREEZE'
SELECTION_FREEZE_PATH = HERE / 'selection-freeze-v2.json'
PHASES = ('development', 'validation', 'audit')
HEX64 = re.compile(r'[0-9a-f]{64}')


def need(condition, message='invalid S05 selection freeze'):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_private_selection(selection_path):
    selection_path = Path(selection_path)
    inventory = json.loads(selection_path.read_text(encoding='utf-8'))
    need(type(inventory) is dict and inventory.get('purpose') == SELECTION_PURPOSE)
    need(type(inventory.get('schema_version')) is int and inventory['schema_version'] == 1)
    need(inventory.get('protocol_sha256') == sha256(PROTOCOL), 'selection protocol changed')
    need(inventory.get('source_pins') == selection_pins(), 'selection/preprocessing code pins changed')
    need(type(inventory.get('excluded_prior_cases')) is int
         and inventory['excluded_prior_cases'] == 120
         and all(type(inventory.get(name)) is int and inventory[name] == 0 for name in (
             'cross_phase_id_overlap', 'cross_phase_text_overlap',
             'prior_id_text_source_pcm_overlap'))
         and inventory.get('frozen_before_inference') is True
         and inventory.get('inference') == 'NOT_RUN',
         'cohort state is not frozen before inference')
    need(inventory.get('model_training_overlap') == 'UNKNOWN'
         and inventory.get('native_calibration') == 'NOT_ESTABLISHED'
         and inventory.get('threshold_authorization') == 'NOT_GRANTED'
         and inventory.get('production') == 'NOT_ENABLED'
         and inventory.get('physical') == 'NOT_RUN', 'cohort gates changed')
    for key in ('archive_sha256', 'receipt_sha256', 'protocol_sha256'):
        need(type(inventory.get(key)) is str and HEX64.fullmatch(inventory[key]),
             f'invalid {key}')
    previous = inventory.get('prior_manifest_sha256')
    need(type(previous) is list and len(previous) == 4
         and all(type(value) is str and HEX64.fullmatch(value) for value in previous),
         'prior manifest inventory changed')
    phases = inventory.get('phases')
    need(type(phases) is dict and set(phases) == set(PHASES), 'three frozen phases required')

    manifests = {}
    for phase in PHASES:
        entry = phases[phase]
        need(type(entry) is dict and entry.get('cases') == 200
             and type(entry.get('manifest_sha256')) is str
             and HEX64.fullmatch(entry['manifest_sha256']), f'{phase} inventory changed')
        manifest_path = selection_path.parent / phase / 'manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        validate_manifest(manifest, manifest_path.parent)
        need(canonical_digest(manifest) == entry['manifest_sha256'],
             f'{phase} private manifest differs from its selection freeze')
        need(manifest.get('dataset') == 'common_voice'
             and manifest.get('release') == '26.0-2026-06-12-en-AU-MDC-2026-07-20'
             and manifest.get('receipt_sha256') == inventory['receipt_sha256']
             and len(manifest.get('cases', [])) == 200,
             f'{phase} manifest release or receipt changed')
        expected_split = 'validation' if phase == 'validation' else 'test'
        need(all(case.get('split') == expected_split and case.get('task') == 'asr'
                 for case in manifest['cases']), f'{phase} manifest split changed')
        manifests[phase] = manifest

    decoder_kinds = {manifest.get('decoder_kind') for manifest in manifests.values()}
    decoder_hashes = {manifest.get('decoder_sha256') for manifest in manifests.values()}
    recipes = {manifest.get('recipe') for manifest in manifests.values()}
    rates = {manifest.get('rate') for manifest in manifests.values()}
    need(len(decoder_kinds) == len(decoder_hashes) == len(recipes) == len(rates) == 1,
         'phase preprocessing/decoder pins differ')
    decoder_kind, decoder_hash = next(iter(decoder_kinds)), next(iter(decoder_hashes))
    need(decoder_kind in ('afconvert', 'ffmpeg') and type(decoder_hash) is str
         and HEX64.fullmatch(decoder_hash), 'invalid pinned decoder')
    need(next(iter(recipes)) == 'pcm16-mono-area-downsample-linear-upsample-v1'
         and next(iter(rates)) == 16000, 'audio preprocessing recipe changed')
    return inventory, manifests, decoder_kind, decoder_hash


def public_freeze(selection_path):
    inventory, manifests, decoder_kind, decoder_hash = load_private_selection(selection_path)
    return {
        'schema_version': 1,
        'purpose': FREEZE_PURPOSE,
        'protocol_sha256': inventory['protocol_sha256'],
        'selection_code_pins': inventory['source_pins'],
        'freeze_reporter_sha256': sha256(HERE / 'freeze_selection_v2.py'),
        'archive_sha256': inventory['archive_sha256'],
        'receipt_sha256': inventory['receipt_sha256'],
        'prior_manifest_sha256': inventory['prior_manifest_sha256'],
        'excluded_prior_cases': inventory['excluded_prior_cases'],
        'phase_manifest_sha256': {
            phase: inventory['phases'][phase]['manifest_sha256'] for phase in PHASES
        },
        'cases_per_phase': 200,
        'audio': {
            'recipe': next(iter(manifests.values()))['recipe'],
            'sample_rate_hz': next(iter(manifests.values()))['rate'],
            'channels': 1,
            'sample_format': 'PCM16',
        },
        'decoder': {'kind': decoder_kind, 'sha256': decoder_hash},
        'cross_phase_id_overlap': inventory['cross_phase_id_overlap'],
        'cross_phase_text_overlap': inventory['cross_phase_text_overlap'],
        'model_training_overlap': inventory['model_training_overlap'],
        'frozen_before_inference': True,
        'inference': 'NOT_RUN',
        'software_audit_qualification': 'NOT_ESTABLISHED',
        'native_calibration': 'NOT_ESTABLISHED',
        'threshold_authorization': 'NOT_GRANTED',
        'production': 'NOT_ENABLED',
        'physical': 'NOT_RUN',
        'release': 'HOLD',
        'persistent_memory': 'DISABLED',
    }


def write_public_freeze(selection_path, output_path):
    output_path = Path(output_path)
    need(output_path.resolve() == SELECTION_FREEZE_PATH.resolve(),
         'public selection freeze must use the reviewed repository path')
    value = public_freeze(selection_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection-private', type=Path, required=True,
                        help='ignored local selection inventory and phase manifests')
    parser.add_argument('--output', type=Path, required=True,
                        help='new public hash-only file at selection-freeze-v2.json')
    args = parser.parse_args()
    value = write_public_freeze(args.selection_private, args.output)
    print(json.dumps({
        'purpose': value['purpose'],
        'phase_manifest_sha256': value['phase_manifest_sha256'],
        'decoder': value['decoder'],
        'frozen_before_inference': value['frozen_before_inference'],
        'inference': value['inference'],
    }, indent=2))


if __name__ == '__main__':
    main()
