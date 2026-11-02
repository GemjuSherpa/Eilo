"""Run the frozen S05 development cohort once through the pinned iOS simulator scorer."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import wave

from audit_v2 import HERE, SOURCES
from freeze_selection_v2 import PHASES, SELECTION_FREEZE_PATH, load_private_selection

EILO = HERE.parents[1]
PACKAGES = EILO / 'packages'
LOCAL = EILO / '.local'
REPOSITORY = EILO.parent
RUNNER_PATH = HERE / 'run_development_v2.py'
PRIVATE_ATTEMPTS_PATH = LOCAL / 'asr-calibration-audit-v2/development-attempts-v2.json'
PRIVATE_START_PATH = LOCAL / 'asr-calibration-audit-v2/development-started-v2.json'
PRIVATE_RUN_RECEIPT_PATH = LOCAL / 'asr-calibration-audit-v2/development-execution-v2.json'
LOCAL_BINARY = LOCAL / 'asr-ios-corpus/run-v1/relocated/ios-corpus-score'
LOCAL_RUNTIME_OBJECT = LOCAL / 'asr-ios-corpus/run-v1/prelinked_objects.o'
PUBLIC_BINARY_RECORD = PACKAGES / 'asr-ios-corpus/ios-reference-results.json'
PUBLIC_FREEZE_RELATIVE = 'Eilo/packages/asr-calibration/selection-freeze-v2.json'
RUNNER_RELATIVE = 'Eilo/packages/asr-calibration/run_development_v2.py'
sys.path.insert(0, str(PACKAGES / 'asr-runtime'))
import framework
sys.path.insert(0, str(PACKAGES / 'asr-corpus-score'))
import diagnostics
sys.path.insert(0, str(PACKAGES / 'dataset-evaluation'))
from manifests import safe_path


def need(condition, message='invalid development-run evidence'):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_committed_blob(commit, relative, path):
    need(type(commit) is str and re.fullmatch(r'[0-9a-f]{40}', commit),
         'full reviewed commit is required')
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=REPOSITORY,
                   check=True, capture_output=True)
    committed = subprocess.check_output(['git', 'show', f'{commit}:{relative}'], cwd=REPOSITORY)
    need(committed == Path(path).read_bytes(), f'{relative} differs from its committed blob')
    return hashlib.sha256(committed).hexdigest()


def verify_asr_stack(asr_cache):
    asr_cache = Path(asr_cache).resolve()
    need(asr_cache.is_relative_to(LOCAL.resolve()), 'ASR cache must be inside ignored local storage')
    model, provenance = framework.verify_asr(asr_cache)
    record = json.loads(PUBLIC_BINARY_RECORD.read_text(encoding='utf-8'))
    need(record.get('purpose') == 'IOS_EXPOSED_REFERENCE_NOISE_DIAGNOSTIC'
         and record.get('physical') == 'NOT_RUN' and record.get('production') == 'NOT_ENABLED',
         'reviewed iOS reference scorer record changed')
    need(LOCAL_BINARY.is_file() and not LOCAL_BINARY.is_symlink()
         and sha256(LOCAL_BINARY) == record['binary_sha256'],
         'local iOS simulator scorer differs from the reviewed binary hash')
    need(LOCAL_RUNTIME_OBJECT.is_file() and not LOCAL_RUNTIME_OBJECT.is_symlink()
         and sha256(LOCAL_RUNTIME_OBJECT) == record['runtime_object_sha256'],
         'local iOS runtime object differs from the reviewed runtime hash')
    provenance_path = PACKAGES / 'asr-runtime/provenance.json'
    need(sha256(provenance_path) == record['model_provenance_sha256'],
         'reviewed model provenance changed')
    for pin in record['source_pins']:
        path = PACKAGES / pin['path']
        need(path.is_file() and sha256(path) == pin['sha256'],
             'reviewed iOS scorer source pins changed')
    return model, {
        'binary_sha256': record['binary_sha256'],
        'runtime_object_sha256': record['runtime_object_sha256'],
        'model_provenance_sha256': record['model_provenance_sha256'],
        'model_provenance_schema_sha256': sha256(provenance_path),
        'model_directory': str(model.relative_to(LOCAL.resolve())),
        'model_files': len(provenance['model']['files']),
    }


def load_development_cases(selection_path, selection_freeze):
    inventory, manifests, decoder_kind, decoder_hash = load_private_selection(selection_path)
    freeze = json.loads(Path(selection_freeze).read_text(encoding='utf-8'))
    need(freeze.get('purpose') == 'S05_VC_TURN_10_SELECTION_FREEZE'
         and freeze.get('phase_manifest_sha256') == {
             phase: inventory['phases'][phase]['manifest_sha256'] for phase in PHASES
         }, 'public selection freeze does not match the local cohort')
    need(freeze.get('decoder') == {'kind': decoder_kind, 'sha256': decoder_hash},
         'public decoder pin differs from local phase manifests')
    manifest = manifests['development']
    need(len(manifest['cases']) == 200 and all(case.get('task') == 'asr'
         and case.get('split') == 'test' for case in manifest['cases']),
         'only the frozen 200-case development cohort is allowed')
    return inventory, manifest


def pcm16_to_float32(pcm, sample_rate=16000, channels=1):
    need(type(pcm) is bytes and len(pcm) > 0 and len(pcm) % 2 == 0
         and sample_rate == 16000 and channels == 1,
         'development audio must be nonempty mono PCM16 at 16 kHz')
    values = struct.unpack('<' + 'h' * (len(pcm) // 2), pcm)
    return struct.pack('<' + 'f' * len(values), *(sample / 32768.0 for sample in values))


def unavailable_rows(case_id):
    return {source: {'case_id': case_id, 'status': 'UNAVAILABLE'} for source in SOURCES}


def rows_from_response(case_id, response):
    paths = diagnostics.validate_response(response)
    rows = {}
    for path in paths:
        source = path['source']
        if path['status'] == 'UNAVAILABLE':
            rows[source] = {'case_id': case_id, 'status': 'UNAVAILABLE'}
        else:
            rows[source] = {'case_id': case_id, 'status': 'AVAILABLE',
                            'score': path['confidence'], 'hypothesis': path['transcript']}
    need(list(rows) == list(SOURCES), 'native response source order changed')
    return rows


def build_attempt_document(case_ids, rows_by_case):
    need(type(case_ids) is list and len(case_ids) == 200
         and len(set(case_ids)) == 200 and len(rows_by_case) == 200,
         'development attempt inventory must contain 200 unique cases')
    sources = []
    for source in SOURCES:
        attempts = [rows_by_case[index][source] for index in range(200)]
        need([row['case_id'] for row in attempts] == case_ids,
             'development attempts are not in manifest order')
        sources.append({'source': source, 'attempts': attempts})
    return {'schema_version': 1, 'stage': 'DEVELOPMENT', 'case_ids': case_ids,
            'sources': sources}


def exclusive_json(path, value, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def booted_simulator(udid):
    result = subprocess.run(['xcrun', 'simctl', 'list', 'devices', 'booted', '--json'],
                            capture_output=True, text=True, timeout=60, check=True)
    devices = json.loads(result.stdout).get('devices', {})
    return any(device.get('udid') == udid and device.get('state') == 'Booted'
               and device.get('isAvailable') for group in devices.values() for device in group)


def run_development(selection_path, selection_freeze, selection_freeze_commit,
                    runner_commit, asr_cache, udid):
    selection_path = Path(selection_path).resolve()
    selection_freeze = Path(selection_freeze).resolve()
    need(selection_path.is_relative_to(LOCAL.resolve())
         and selection_freeze == SELECTION_FREEZE_PATH.resolve(),
         'selection inputs must use the reviewed private and public locations')
    inventory, manifest = load_development_cases(selection_path, selection_freeze)
    public_freeze_sha = verify_committed_blob(selection_freeze_commit, PUBLIC_FREEZE_RELATIVE,
                                               selection_freeze)
    runner_sha = verify_committed_blob(runner_commit, RUNNER_RELATIVE, RUNNER_PATH)
    model, model_pins = verify_asr_stack(asr_cache)
    need(booted_simulator(udid), 'the requested iOS simulator must already be booted and available')
    need(not PRIVATE_ATTEMPTS_PATH.exists() and not PRIVATE_START_PATH.exists()
         and not PRIVATE_RUN_RECEIPT_PATH.exists(),
         'preserve existing development attempts; this stage runs only once')

    marker = {
        'schema_version': 1,
        'purpose': 'S05_VC_TURN_10_PRIVATE_DEVELOPMENT_EXECUTION',
        'stage': 'DEVELOPMENT',
        'state': 'STARTED',
        'selection_freeze_commit': selection_freeze_commit,
        'selection_freeze_sha256': public_freeze_sha,
        'development_manifest_sha256': inventory['phases']['development']['manifest_sha256'],
        'runner_commit': runner_commit,
        'runner_sha256': runner_sha,
        'decoder_sha256': json.loads(selection_freeze.read_text(encoding='utf-8'))['decoder']['sha256'],
        'simulator_udid_sha256': hashlib.sha256(udid.encode('utf-8')).hexdigest(),
        **model_pins,
    }
    exclusive_json(PRIVATE_START_PATH, marker)

    rows_by_case = []
    errors = 0
    with tempfile.TemporaryDirectory(prefix='eilo-s05-development-') as folder:
        audio_path = Path(folder) / 'input.f32'
        for case in manifest['cases']:
            case_id = case['id']
            try:
                source_audio = safe_path(selection_path.parent / 'development', case['path'])
                with wave.open(str(source_audio), 'rb') as stream:
                    need((stream.getframerate(), stream.getnchannels(), stream.getsampwidth(),
                          stream.getnframes()) == (16000, 1, 2, case['samples']),
                         'frozen development WAV metadata changed')
                    pcm = stream.readframes(stream.getnframes())
                audio_path.write_bytes(pcm16_to_float32(pcm))
                result = subprocess.run(
                    ['xcrun', 'simctl', 'spawn', udid, str(LOCAL_BINARY), str(model),
                     str(audio_path)], capture_output=True, text=True, timeout=240, check=False)
                if result.returncode != 0:
                    raise ValueError('native score unavailable')
                response_lines = [line for line in result.stdout.splitlines()
                                  if line.startswith('{')]
                need(len(response_lines) == 1, 'native response missing')
                rows_by_case.append(rows_from_response(case_id, json.loads(response_lines[0])))
            except Exception:
                errors += 1
                rows_by_case.append(unavailable_rows(case_id))

    attempts = build_attempt_document([case['id'] for case in manifest['cases']], rows_by_case)
    exclusive_json(PRIVATE_ATTEMPTS_PATH, attempts)
    marker.update({'state': 'COMPLETE', 'collector_errors': errors,
                   'attempts_sha256': sha256(PRIVATE_ATTEMPTS_PATH),
                   'development_manifest_sha256': inventory['phases']['development']['manifest_sha256']})
    exclusive_json(PRIVATE_RUN_RECEIPT_PATH, marker)
    available = {source: sum(row['status'] == 'AVAILABLE'
                             for row in attempts['sources'][index]['attempts'])
                 for index, source in enumerate(SOURCES)}
    print(json.dumps({'stage': 'DEVELOPMENT', 'attempted': 200, 'collector_errors': errors,
                      'available_per_source': available, 'private_attempts_sha256': sha256(PRIVATE_ATTEMPTS_PATH),
                      'inference': 'DEVELOPMENT_ONLY'}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection-private', type=Path, required=True)
    parser.add_argument('--selection-freeze', type=Path, required=True)
    parser.add_argument('--selection-freeze-commit', required=True,
                        help='full commit containing the exact public selection freeze')
    parser.add_argument('--runner-commit', required=True,
                        help='full commit containing this exact runner source')
    parser.add_argument('--asr-cache', type=Path, required=True,
                        help='already-approved local Moonshine runtime/model cache')
    parser.add_argument('--udid', required=True,
                        help='already-booted iOS simulator UDID')
    args = parser.parse_args()
    run_development(args.selection_private, args.selection_freeze,
                    args.selection_freeze_commit, args.runner_commit,
                    args.asr_cache, args.udid)


if __name__ == '__main__':
    main()
