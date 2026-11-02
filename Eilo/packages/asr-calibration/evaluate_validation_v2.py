"""Score private S05 validation attempts against committed development mappings."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from audit_v2 import HERE, PROTOCOL, SOURCES, protocol, validate_counts

sys.path.insert(0, str(HERE.parent / 'asr-fresh-split'))
from shared import canonical_digest

sys.path.insert(0, str(HERE.parent / 'dataset-evaluation'))
from benchmark import normalize, validate_manifest

sys.path.insert(0, str(HERE))
from calibrate import check_model, fit as fit_pava, predict

FREEZE_PURPOSE = 'S05_VC_TURN_10_CONFIDENCE_MAPPING_FREEZE'
PRIVATE_PURPOSE = 'S05_VC_TURN_10_PRIVATE_DEVELOPMENT_MAPPINGS'
MAPPED_CUTOFF = protocol()['mapped_cutoff']
MAPPING_FREEZE_PATH = HERE / 'mapping-freeze-v2.json'
PRIVATE_MAPPING_PATH = HERE.parents[1] / '.local/asr-calibration-audit-v2/private-mappings-v2.json'
MAPPING_KINDS = {'schema_version', 'purpose', 'protocol_sha256',
                 'development_attempts_per_source', 'models'}
FREEZE_KINDS = {'schema_version', 'purpose', 'protocol_sha256',
                'development_attempts_per_source', 'mapping_sha256', 'source_pins',
                'frozen_before_validation', 'model_training_overlap'}
ATTEMPT_KINDS = {'case_id', 'status', 'score', 'hypothesis'}


def need(condition, message='invalid validation evidence'):
    if not condition:
        raise ValueError(message)


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_pins():
    paths = (PROTOCOL, HERE / 'audit_v2.py', HERE / 'calibrate.py',
             HERE / 'evaluate_validation_v2.py', HERE.parent / 'asr-fresh-split/shared.py',
             HERE.parent / 'dataset-evaluation/benchmark.py')
    return {str(path.relative_to(HERE.parents[1])): file_sha256(path) for path in paths}


def check_models(models):
    need(type(models) is dict and list(models) == list(SOURCES),
         'development mappings must contain the two frozen sources in protocol order')
    for source in SOURCES:
        check_model(models[source])


def validate_private_mappings(private):
    need(type(private) is dict and set(private) == MAPPING_KINDS)
    need(type(private['schema_version']) is int and private['schema_version'] == 1
         and private['purpose'] == PRIVATE_PURPOSE)
    need(private['protocol_sha256'] == file_sha256(PROTOCOL))
    need(type(private['development_attempts_per_source']) is int
         and private['development_attempts_per_source'] == 200)
    check_models(private['models'])
    return private


def checked_rows(attempts, stage, expected_cases):
    need(type(attempts) is dict and set(attempts) == {'schema_version', 'stage', 'case_ids', 'sources'})
    need(type(attempts['schema_version']) is int and attempts['schema_version'] == 1
         and attempts['stage'] == stage, f'only the frozen {stage.lower()} stage is supported')
    need(type(expected_cases) is list and len(expected_cases) == 200
         and all(type(case) is dict and type(case.get('id')) is str
                 and type(case.get('reference')) is str and len(case['reference']) <= 4096
                 for case in expected_cases), 'frozen cohort references are required locally')
    case_ids = attempts['case_ids']
    expected_ids = [case['id'] for case in expected_cases]
    need(case_ids == expected_ids, 'attempt rows do not match the frozen cohort manifest order')
    need(all(type(case_id) is str and re.fullmatch(r'[0-9a-f]{24}', case_id)
             for case_id in case_ids) and len(set(case_ids)) == 200,
         'cohort must contain exactly 200 unique frozen case IDs')
    need(type(attempts['sources']) is list and len(attempts['sources']) == len(SOURCES)
         and all(type(row) is dict and set(row) == {'source', 'attempts'}
                 for row in attempts['sources'])
         and [row['source'] for row in attempts['sources']] == list(SOURCES),
         'source inventory/order changed')
    labels = {}
    for source_row, source in zip(attempts['sources'], SOURCES):
        rows = source_row['attempts']
        need(type(rows) is list and len(rows) == 200, 'every source must contain all 200 attempts')
        pairs = []
        for index, row in enumerate(rows):
            need(type(row) is dict and {'case_id', 'status'} <= set(row)
                 and set(row) <= ATTEMPT_KINDS, 'unexpected private attempt fields')
            need(row['case_id'] == case_ids[index], 'attempt order differs from frozen cohort')
            if row['status'] == 'UNAVAILABLE':
                need(set(row) == {'case_id', 'status'},
                     'unavailable scores cannot include a score or hypothesis')
                continue
            need(row['status'] == 'AVAILABLE' and set(row) == ATTEMPT_KINDS,
                 'invalid available attempt')
            need(type(row['score']) in (int, float) and 0 <= row['score'] <= 1,
                 'raw confidence score must be finite and in [0,1]')
            need(type(row['hypothesis']) is str and len(row['hypothesis']) <= 4096,
                 'hypothesis must be a bounded local string')
            exact = normalize(row['hypothesis']) == normalize(expected_cases[index]['reference'])
            pairs.append((row['score'], exact))
        labels[source] = pairs
    return labels


def fit_development(attempts, expected_cases):
    """Fit separate private PAVA models from the frozen development cohort only."""
    pairs = checked_rows(attempts, 'DEVELOPMENT', expected_cases)
    private = {
        'schema_version': 1,
        'purpose': PRIVATE_PURPOSE,
        'protocol_sha256': file_sha256(PROTOCOL),
        'development_attempts_per_source': 200,
        'models': {source: fit_pava(pairs[source]) for source in SOURCES},
    }
    validate_private_mappings(private)
    return private


def freeze_metadata(private, development_attempts, development_cases):
    validate_private_mappings(private)
    derived = fit_development(development_attempts, development_cases)
    need(derived['models'] == private['models'],
         'private mappings were not fit from the frozen development attempts')
    return {
        'schema_version': 1,
        'purpose': FREEZE_PURPOSE,
        'protocol_sha256': file_sha256(PROTOCOL),
        'development_attempts_per_source': 200,
        'mapping_sha256': {source: canonical_digest(private['models'][source])
                           for source in SOURCES},
        'source_pins': source_pins(),
        'frozen_before_validation': True,
        'model_training_overlap': 'UNKNOWN',
    }


def validate_freeze_metadata(value):
    need(type(value) is dict and set(value) == FREEZE_KINDS)
    need(type(value['schema_version']) is int and value['schema_version'] == 1
         and value['purpose'] == FREEZE_PURPOSE)
    need(value['protocol_sha256'] == file_sha256(PROTOCOL))
    need(type(value['development_attempts_per_source']) is int
         and value['development_attempts_per_source'] == 200)
    need(value['frozen_before_validation'] is True and value['model_training_overlap'] == 'UNKNOWN')
    need(value['source_pins'] == source_pins(), 'mapping freeze source pins changed')
    need(type(value['mapping_sha256']) is dict and list(value['mapping_sha256']) == list(SOURCES)
         and all(type(value['mapping_sha256'][source]) is str
                 and re.fullmatch(r'[0-9a-f]{64}', value['mapping_sha256'][source])
                 for source in SOURCES))
    return value


def verify_freeze_commit(freeze_path, commit, repository=None):
    need(type(commit) is str and re.fullmatch(r'[0-9a-f]{40}', commit) is not None,
         'full mapping-freeze commit is required')
    repository = Path(repository or HERE.parents[2]).resolve()
    path = Path(freeze_path).resolve()
    try:
        relative = path.relative_to(repository).as_posix()
    except ValueError as error:
        raise ValueError('mapping freeze must be committed inside this repository') from error
    need(relative == 'Eilo/packages/asr-calibration/mapping-freeze-v2.json',
         'mapping freeze must use the reviewed repository path')
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=repository,
                   check=True, capture_output=True)
    committed = subprocess.check_output(['git', 'show', f'{commit}:{relative}'], cwd=repository)
    need(committed == path.read_bytes(), 'working mapping freeze differs from its committed blob')
    value = json.loads(committed)
    validate_freeze_metadata(value)
    return value, file_sha256(path)


def load_frozen_cohort(selection_path, manifest_path, phase):
    selection = json.loads(Path(selection_path).read_text(encoding='utf-8'))
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    validate_manifest(manifest, manifest_path.parent)
    phase_record = selection.get('phases', {}).get(phase, {}) if type(selection) is dict else {}
    need(type(selection) is dict
         and selection.get('purpose') == 'PRIVATE_FROZEN_CONFIDENCE_AUDIT_COHORT'
         and selection.get('protocol_sha256') == file_sha256(PROTOCOL)
         and phase_record.get('cases') == 200
         and phase_record.get('manifest_sha256') == canonical_digest(manifest),
         f'{phase} manifest is not bound to the frozen private cohort selection')
    need(manifest.get('dataset') == 'common_voice' and len(manifest.get('cases', [])) == 200
         and all(case.get('task') == 'asr' for case in manifest['cases']),
         f'{phase} manifest must contain 200 Common Voice ASR cases')
    if phase == 'validation':
        need(all(case.get('split') == 'validation' for case in manifest['cases']),
             'validation manifest split changed')
    return selection, manifest


def evaluate_validation(attempts, private, frozen, expected_cases, freeze_sha=None,
                        freeze_commit=None, validation_manifest_sha=None):
    """Return aggregate counts only; case IDs, scores and correctness never leave this function."""
    pairs_by_source = checked_rows(attempts, 'VALIDATION', expected_cases)
    validate_private_mappings(private)
    validate_freeze_metadata(frozen)
    need(frozen['purpose'] == FREEZE_PURPOSE
         and frozen['mapping_sha256'] == {
             source: canonical_digest(private['models'][source]) for source in SOURCES
         }, 'private development mappings do not match the committed freeze')

    counts = []
    for source in SOURCES:
        pairs = pairs_by_source[source]
        accepted_pairs = [(score, correct) for score, correct in pairs
                          if predict(private['models'][source], score) >= MAPPED_CUTOFF]
        accepted = len(accepted_pairs)
        correct = sum(int(label) for _, label in accepted_pairs)
        unavailable = 200 - len(pairs)
        counts.append({'source': source, 'attempted': 200, 'unavailable': unavailable,
                       'accepted': accepted, 'accepted_correct': correct})
    count_document = {'schema_version': 1, 'stage': 'VALIDATION', 'sources': counts}
    report = validate_counts(count_document)
    return {
        'schema_version': 1,
        'purpose': 'S05_CONFIDENCE_AUDIT_VALIDATION_AGGREGATE',
        'stage': 'VALIDATION',
        'protocol_sha256': file_sha256(PROTOCOL),
        'validation_manifest_sha256': validation_manifest_sha,
        'mapping_sha256': frozen['mapping_sha256'],
        'mapping_freeze_sha256': freeze_sha,
        'mapping_freeze_commit': freeze_commit,
        'sources': report['sources'],
        'overall': report['overall'],
        'software_audit_qualification': 'NOT_ESTABLISHED',
        'native_calibration': 'NOT_ESTABLISHED',
        'threshold_authorization': 'NOT_GRANTED',
        'production': 'NOT_ENABLED',
        'physical': 'NOT_RUN',
        'release': 'HOLD',
        'persistent_memory': 'DISABLED',
        'sealed_audit': 'CLOSED_UNTIL_BOTH_VALIDATION_SOURCES_PASS',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    fit_parser = commands.add_parser('fit-development', help='fit private mappings from the frozen development cohort')
    fit_parser.add_argument('--attempts', type=Path, required=True,
                            help='local-only per-case development attempts; never commit or upload')
    fit_parser.add_argument('--selection-private', type=Path, required=True)
    fit_parser.add_argument('--development-manifest', type=Path, required=True)
    freeze_parser = commands.add_parser('freeze', help='write the public hash-only mapping freeze')
    freeze_parser.add_argument('--private-mappings', type=Path, required=True,
                               help='local-only development mappings; never commit or upload')
    freeze_parser.add_argument('--attempts', type=Path, required=True,
                               help='local-only development attempts; used to verify mapping lineage')
    freeze_parser.add_argument('--selection-private', type=Path, required=True)
    freeze_parser.add_argument('--development-manifest', type=Path, required=True)
    freeze_parser.add_argument('--output', type=Path, required=True,
                               help='new public hash-only freeze path; existing files are preserved')
    evaluate_parser = commands.add_parser('evaluate', help='score completed private validation attempts')
    evaluate_parser.add_argument('--private-mappings', type=Path, required=True,
                                 help='local-only development mappings; never commit or upload')
    evaluate_parser.add_argument('--attempts', type=Path, required=True,
                                 help='local-only per-case validation rows; never commit or upload')
    evaluate_parser.add_argument('--selection-private', type=Path, required=True,
                                 help='local selection inventory from the frozen cohort')
    evaluate_parser.add_argument('--validation-manifest', type=Path, required=True,
                                 help='local validation manifest for exact case-order binding')
    evaluate_parser.add_argument('--mapping-freeze', type=Path, required=True,
                                 help='public hash-only mapping freeze committed before validation')
    evaluate_parser.add_argument('--freeze-commit', required=True,
                                 help='full commit hash containing the exact mapping-freeze blob')
    args = parser.parse_args()
    if args.command == 'fit-development':
        selection, manifest = load_frozen_cohort(args.selection_private,
                                                  args.development_manifest, 'development')
        attempts = json.loads(args.attempts.read_text(encoding='utf-8'))
        private = fit_development(attempts, manifest['cases'])
        PRIVATE_MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(PRIVATE_MAPPING_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write(json.dumps(private, indent=2, sort_keys=True, allow_nan=False) + '\n')
        print('Private development mappings fit from the frozen 200-case cohort; no holdout touched.')
        return

    if args.command == 'freeze':
        need(args.private_mappings.resolve() == PRIVATE_MAPPING_PATH.resolve(),
             'private mapping file must remain in the ignored local audit cache')
        private = json.loads(args.private_mappings.read_text(encoding='utf-8'))
        _, manifest = load_frozen_cohort(args.selection_private,
                                         args.development_manifest, 'development')
        development_attempts = json.loads(args.attempts.read_text(encoding='utf-8'))
        validate_private_mappings(private)
        need(fit_development(development_attempts, manifest['cases'])['models'] == private['models'],
             'private mappings do not match the frozen development-only fit')
        public = freeze_metadata(private, development_attempts, manifest['cases'])
        need(args.output.resolve() == MAPPING_FREEZE_PATH.resolve(),
             'mapping freeze output must use the reviewed repository path')
        MAPPING_FREEZE_PATH.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(MAPPING_FREEZE_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write(json.dumps(public, indent=2, sort_keys=True, allow_nan=False) + '\n')
        print('Hash-only development mapping freeze written; commit it before validation.')
        return

    need(args.private_mappings.resolve() == PRIVATE_MAPPING_PATH.resolve(),
         'private mapping file must remain in the ignored local audit cache')
    private = json.loads(args.private_mappings.read_text(encoding='utf-8'))
    frozen, frozen_sha = verify_freeze_commit(args.mapping_freeze, args.freeze_commit)
    need(frozen['mapping_sha256'] == {
        source: canonical_digest(private['models'][source]) for source in SOURCES
    }, 'private development mappings differ from the committed freeze')
    _, manifest = load_frozen_cohort(args.selection_private, args.validation_manifest, 'validation')
    attempts = json.loads(args.attempts.read_text(encoding='utf-8'))
    print(json.dumps(evaluate_validation(attempts, private, frozen, manifest['cases'], frozen_sha,
                                         args.freeze_commit, canonical_digest(manifest)),
                     indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
