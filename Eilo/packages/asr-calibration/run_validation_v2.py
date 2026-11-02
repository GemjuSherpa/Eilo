"""Run the frozen S05 validation cohort once with committed development mappings."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import wave

import run_development_v2 as common
from audit_v2 import HERE, SOURCES
from evaluate_validation_v2 import (FREEZE_PURPOSE, MAPPING_FREEZE_PATH, canonical_digest,
                                    load_frozen_cohort, validate_freeze_metadata,
                                    validate_private_mappings, verify_freeze_commit)
from freeze_selection_v2 import PHASES, SELECTION_FREEZE_PATH, load_private_selection
from manifests import canonical_digest, safe_path

LOCAL = common.LOCAL
PACKAGES = common.PACKAGES
REPOSITORY = common.REPOSITORY
RUNNER_PATH = HERE / 'run_validation_v2.py'
PRIVATE_ATTEMPTS_PATH = LOCAL / 'asr-calibration-audit-v2/validation-attempts-v2.json'
PRIVATE_START_PATH = LOCAL / 'asr-calibration-audit-v2/validation-started-v2.json'
PRIVATE_RUN_RECEIPT_PATH = LOCAL / 'asr-calibration-audit-v2/validation-execution-v2.json'
PRIVATE_MAPPING_PATH = LOCAL / 'asr-calibration-audit-v2/private-mappings-v2.json'
PUBLIC_FREEZE_RELATIVE = 'Eilo/packages/asr-calibration/selection-freeze-v2.json'
RUNNER_RELATIVE = 'Eilo/packages/asr-calibration/run_validation_v2.py'
MAPPING_FREEZE_RELATIVE = 'Eilo/packages/asr-calibration/mapping-freeze-v2.json'


def need(condition, message='invalid validation-run evidence'):
    common.need(condition, message)


def load_validation_cases(selection_path, selection_freeze):
    inventory, manifests, decoder_kind, decoder_hash = load_private_selection(selection_path)
    freeze = json.loads(Path(selection_freeze).read_text(encoding='utf-8'))
    need(freeze.get('purpose') == 'S05_VC_TURN_10_SELECTION_FREEZE'
         and freeze.get('phase_manifest_sha256') == {
             phase: inventory['phases'][phase]['manifest_sha256'] for phase in PHASES
         }, 'public selection freeze does not match the local cohort')
    need(freeze.get('decoder') == {'kind': decoder_kind, 'sha256': decoder_hash},
         'public decoder pin differs from local phase manifests')
    manifest = manifests['validation']
    need(len(manifest['cases']) == 200 and all(case.get('task') == 'asr'
         and case.get('split') == 'validation' for case in manifest['cases']),
         'only the frozen 200-case validation cohort is allowed')
    return inventory, manifest


def build_validation_attempt_document(case_ids, rows_by_case):
    need(type(case_ids) is list and len(case_ids) == 200
         and len(set(case_ids)) == 200 and len(rows_by_case) == 200,
         'validation attempt inventory must contain 200 unique cases')
    source_rows = []
    for source in SOURCES:
        attempts = [rows_by_case[index][source] for index in range(200)]
        need([row['case_id'] for row in attempts] == case_ids,
             'validation attempts are not in manifest order')
        source_rows.append({'source': source, 'attempts': attempts})
    return {'schema_version': 1, 'stage': 'VALIDATION', 'case_ids': case_ids,
            'sources': source_rows}


def load_mapping_freeze(mapping_freeze, mapping_freeze_commit):
    need(Path(mapping_freeze).resolve() == MAPPING_FREEZE_PATH.resolve(),
         'mapping freeze must use the reviewed repository path')
    frozen, freeze_sha = verify_freeze_commit(mapping_freeze, mapping_freeze_commit)
    validate_freeze_metadata(frozen)
    private = json.loads(PRIVATE_MAPPING_PATH.read_text(encoding='utf-8'))
    validate_private_mappings(private)
    need(frozen.get('purpose') == FREEZE_PURPOSE
         and frozen['mapping_sha256'] == {
             source: canonical_digest(private['models'][source])
             for source in SOURCES
         }, 'private mappings do not match the committed development freeze')
    return frozen, freeze_sha


def run_validation(selection_path, selection_freeze, selection_freeze_commit,
                   mapping_freeze, mapping_freeze_commit, runner_commit,
                   model_directory, udid):
    selection_path = Path(selection_path).resolve()
    selection_freeze = Path(selection_freeze).resolve()
    need(selection_path.is_relative_to(LOCAL.resolve())
         and selection_freeze == SELECTION_FREEZE_PATH.resolve(),
         'selection inputs must use the reviewed private and public locations')
    inventory, manifest = load_validation_cases(selection_path, selection_freeze)
    selection_sha = common.verify_committed_blob(selection_freeze_commit,
                                                  PUBLIC_FREEZE_RELATIVE, selection_freeze)
    frozen, mapping_sha = load_mapping_freeze(mapping_freeze, mapping_freeze_commit)
    runner_sha = common.verify_committed_blob(runner_commit, RUNNER_RELATIVE, RUNNER_PATH)
    model, model_pins = common.verify_asr_stack(model_directory)
    need(common.booted_simulator(udid), 'the requested iOS simulator must already be booted and available')
    need(not PRIVATE_ATTEMPTS_PATH.exists() and not PRIVATE_START_PATH.exists()
         and not PRIVATE_RUN_RECEIPT_PATH.exists(),
         'preserve existing validation attempts; this stage runs only once')

    marker = {
        'schema_version': 1,
        'purpose': 'S05_VC_TURN_10_PRIVATE_VALIDATION_EXECUTION',
        'stage': 'VALIDATION',
        'state': 'STARTED',
        'selection_freeze_commit': selection_freeze_commit,
        'selection_freeze_sha256': selection_sha,
        'mapping_freeze_commit': mapping_freeze_commit,
        'mapping_freeze_sha256': mapping_sha,
        'validation_manifest_sha256': inventory['phases']['validation']['manifest_sha256'],
        'runner_commit': runner_commit,
        'runner_sha256': runner_sha,
        'decoder_sha256': json.loads(selection_freeze.read_text(encoding='utf-8'))['decoder']['sha256'],
        'simulator_udid_sha256': hashlib.sha256(udid.encode('utf-8')).hexdigest(),
        **model_pins,
    }
    common.exclusive_json(PRIVATE_START_PATH, marker)

    rows_by_case = []
    errors = 0
    with tempfile.TemporaryDirectory(prefix='eilo-s05-validation-') as folder:
        audio_path = Path(folder) / 'input.f32'
        for case in manifest['cases']:
            case_id = case['id']
            try:
                source_audio = safe_path(selection_path.parent / 'validation', case['path'])
                with wave.open(str(source_audio), 'rb') as stream:
                    need((stream.getframerate(), stream.getnchannels(), stream.getsampwidth(),
                          stream.getnframes()) == (16000, 1, 2, case['samples']),
                         'frozen validation WAV metadata changed')
                    pcm = stream.readframes(stream.getnframes())
                audio_path.write_bytes(common.pcm16_to_float32(pcm))
                result = subprocess.run(
                    ['xcrun', 'simctl', 'spawn', udid, str(common.LOCAL_BINARY), str(model),
                     str(audio_path)], capture_output=True, text=True, timeout=240, check=False)
                if result.returncode != 0:
                    raise ValueError('native score unavailable')
                response_lines = [line for line in result.stdout.splitlines()
                                  if line.startswith('{')]
                need(len(response_lines) == 1, 'native response missing')
                rows_by_case.append(common.rows_from_response(case_id,
                                                              json.loads(response_lines[0])))
            except Exception:
                errors += 1
                rows_by_case.append(common.unavailable_rows(case_id))

    attempts = build_validation_attempt_document([case['id'] for case in manifest['cases']],
                                                  rows_by_case)
    common.exclusive_json(PRIVATE_ATTEMPTS_PATH, attempts)
    marker.update({'state': 'COMPLETE', 'collector_errors': errors,
                   'attempts_sha256': common.sha256(PRIVATE_ATTEMPTS_PATH),
                   'validation_manifest_sha256': inventory['phases']['validation']['manifest_sha256']})
    common.exclusive_json(PRIVATE_RUN_RECEIPT_PATH, marker)
    available = {source: sum(row['status'] == 'AVAILABLE'
                             for row in attempts['sources'][index]['attempts'])
                 for index, source in enumerate(SOURCES)}
    print(json.dumps({'stage': 'VALIDATION', 'attempted': 200, 'collector_errors': errors,
                      'available_per_source': available,
                      'private_attempts_sha256': common.sha256(PRIVATE_ATTEMPTS_PATH),
                      'mapping_freeze_sha256': mapping_sha,
                      'inference': 'VALIDATION_ONLY'}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection-private', type=Path, required=True)
    parser.add_argument('--selection-freeze', type=Path, required=True)
    parser.add_argument('--selection-freeze-commit', required=True)
    parser.add_argument('--mapping-freeze', type=Path, required=True)
    parser.add_argument('--mapping-freeze-commit', required=True)
    parser.add_argument('--runner-commit', required=True)
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--udid', required=True)
    args = parser.parse_args()
    run_validation(args.selection_private, args.selection_freeze,
                   args.selection_freeze_commit, args.mapping_freeze,
                   args.mapping_freeze_commit, args.runner_commit,
                   args.model_dir, args.udid)


if __name__ == '__main__':
    main()
