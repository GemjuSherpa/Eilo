#!/usr/bin/env python3
"""Summarize reviewed, same-recording acoustic annotations; not a device audit.

No capture, inference, networking or annotation guessing. Only fixed synthetic
questions are permitted. A valid evidence structure is not proof of its claims.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import wave

HERE = Path(__file__).resolve().parent
PLAN_PATH = HERE / 'tests/turn-plan.json'
OUTCOMES = {'REPLY', 'TIMEOUT', 'FAILED', 'CANCELLED'}


def require(value, message):
    if not value:
        raise ValueError(message)


def keys(value, required):
    require(isinstance(value, dict) and set(value) == set(required), 'unexpected evidence fields')


def label(value):
    return isinstance(value, str) and 0 < len(value) <= 128 and value.strip() == value


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def hash_value(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def local_file(root, relative):
    # Resolve evidence only within the explicitly supplied ignored corpus root.
    require(isinstance(relative, str) and relative and '\\' not in relative, 'invalid evidence path')
    path = Path(relative)
    require(not path.is_absolute() and all(p not in ('.', '..') for p in relative.split('/')), 'invalid evidence path')
    target = root
    for part in path.parts:
        target = target / part
        require(not target.is_symlink(), 'symlink evidence is not allowed')
    require(target.is_file() and target.stat().st_size <= 64 * 1024 * 1024, 'missing or oversized evidence file')
    return target


def audio_info(root, record):
    keys(record, ['file', 'sha256'])
    require(hash_value(record['sha256']), 'invalid recording checksum')
    path = local_file(root, record['file'])
    require(digest(path) == record['sha256'], 'recording checksum mismatch')
    with wave.open(str(path), 'rb') as audio:
        require(audio.getcomptype() == 'NONE' and audio.getsampwidth() == 2, 'PCM16 acoustic recording required')
        rate, frames, channels = audio.getframerate(), audio.getnframes(), audio.getnchannels()
        require(8000 <= rate <= 192000 and channels in (1, 2) and 0 < frames <= rate * 180, 'invalid recording dimensions')
        # wave may advertise more frames than its data chunk actually contains.
        remaining = frames
        while remaining:
            count = min(remaining, 65536)
            require(len(audio.readframes(count)) == count * channels * 2, 'truncated recording')
            remaining -= count
    return rate, frames


def quantile(values, fraction):
    return sorted(values)[math.ceil(len(values) * fraction) - 1] if values else None


def stats(values, attempted):
    median, p95 = quantile(values, .5), quantile(values, .95)
    return {
        'attempted': attempted, 'replies': len(values), 'non_replies': attempted - len(values),
        'median_ms': median, 'p95_ms': p95,
        'target': 'PASS' if values and len(values) == attempted and median <= 1500 and p95 <= 3000 else 'FAIL',
        'distribution_scope': 'successful replies only; non-replies prevent target pass',
    }


def summarize(report, corpus_root=None):
    keys(report, ['schema', 'task', 'configurations'])
    require(type(report['schema']) is int and report['schema'] == 1 and report['task'] == 'VC-VERIFY-02', 'wrong evidence schema/task')
    rows = report['configurations']
    require(isinstance(rows, list) and 0 < len(rows) <= 24, 'configuration records required')
    plan_hash = digest(PLAN_PATH)
    schedule = json.loads(PLAN_PATH.read_text())['schedule']
    result, ids = [], set()
    for row in rows:
        require(isinstance(row, dict) and label(row.get('id')) and row['id'] not in ids, 'duplicate/invalid configuration ID')
        ids.add(row['id'])
        require(row.get('platform') in ('iOS', 'Android'), 'invalid platform')
        if row.get('status') == 'NOT_RUN':
            keys(row, ['id', 'platform', 'status', 'reason', 'samples'])
            require(label(row['reason']) or (isinstance(row['reason'], str) and 0 < len(row['reason']) <= 512), 'unrun reason required')
            require(row['samples'] == [], 'unrun record cannot contain samples')
            result.append({'id': row['id'], 'platform': row['platform'], 'status': 'NOT_RUN', 'reason': row['reason'], 'cold': None, 'warm': None, 'overall': None})
            continue
        keys(row, ['id', 'platform', 'status', 'configuration', 'corpus', 'plan_sha256', 'samples'])
        require(row['status'] == 'ANNOTATED' and row['plan_sha256'] == plan_hash, 'annotated evidence requires exact frozen plan')
        config = row['configuration']
        keys(config, ['hardware_kind', 'hardware_model', 'os_build', 'route', 'runtime_revision', 'model_sha256', 'voice_id', 'network_observation', 'airplane_mode', 'wifi_enabled', 'cold_method', 'pipeline'])
        require(config['hardware_kind'] == 'physical', 'simulator is not physical timing evidence')
        for name in ['hardware_model', 'os_build', 'route', 'runtime_revision', 'voice_id']:
            require(label(config[name]), 'exact hardware/OS/route/runtime/voice required')
        require(hash_value(config['model_sha256']), 'model checksum required')
        require(config['airplane_mode'] is True and config['wifi_enabled'] is False and config['network_observation'] == 'NO_TRAFFIC_VERIFIED', 'offline evidence required')
        require(config['cold_method'] == 'fresh_process_models_unloaded' and config['pipeline'] == 'native_microphone_wake_vad_asr_llm_policy_tts', 'full cold/native pipeline evidence required')
        require(corpus_root is not None, 'explicit local corpus directory required')
        root = Path(corpus_root).resolve(strict=True)
        corpus = row['corpus']
        keys(corpus, ['file', 'sha256'])
        manifest_file = local_file(root, corpus['file'])
        require(hash_value(corpus['sha256']) and digest(manifest_file) == corpus['sha256'], 'corpus checksum mismatch')
        manifest = json.loads(manifest_file.read_text())
        keys(manifest, ['schema', 'plan_sha256', 'frozen_before_collection', 'fixtures'])
        require(type(manifest['schema']) is int and manifest['schema'] == 1 and manifest['plan_sha256'] == plan_hash and manifest['frozen_before_collection'] is True, 'prefrozen corpus required')
        fixtures = manifest['fixtures']
        samples = row['samples']
        require(isinstance(fixtures, list) and isinstance(samples, list) and len(fixtures) == len(samples) == 100, 'all 100 planned attempts required, including failures')
        values = {'cold': [], 'warm': []}
        failures = {k: 0 for k in OUTCOMES if k != 'REPLY'}
        recordings = set()
        for planned, fixture, sample in zip(schedule, fixtures, samples):
            keys(fixture, ['id', 'question_index', 'audio'])
            require(fixture['id'] == planned['id'] and type(fixture['question_index']) is int and fixture['question_index'] == planned['question_index'], 'frozen fixture assignment mismatch')
            audio_info(root, fixture['audio'])
            keys(sample, ['id', 'condition', 'outcome', 'recording', 'annotation', 'cold_reset_verified'])
            require(sample['id'] == planned['id'] and sample['condition'] == planned['condition'], 'attempt order/condition mismatch')
            require(sample['outcome'] in OUTCOMES, 'unsupported attempt outcome')
            require(sample['cold_reset_verified'] is (planned['condition'] == 'cold'), 'cold reset evidence inconsistent')
            rate, frames = audio_info(root, sample['recording'])
            recording_id = sample['recording']['sha256']
            require(recording_id not in recordings, 'recording reused across attempts')
            recordings.add(recording_id)
            annotation = sample['annotation']
            keys(annotation, ['method', 'reviewer', 'user_speech_end_frame', 'first_meaningful_reply_frame', 'filler_excluded', 'timeout_observed'])
            require(annotation['method'] == 'independent_same_recording_acoustic_frames' and annotation['reviewer'] == 'Gemju Sherpa', 'SDK callback is not an acoustic annotation')
            end, first = annotation['user_speech_end_frame'], annotation['first_meaningful_reply_frame']
            require(type(end) is int and 0 <= end < frames, 'invalid true speech-end frame')
            require(annotation['filler_excluded'] is True and type(annotation['timeout_observed']) is bool, 'meaningful reply must exclude filler')
            if sample['outcome'] == 'REPLY':
                require(type(first) is int and end <= first < frames and annotation['timeout_observed'] is False, 'invalid meaningful-audio frame')
                values[planned['condition']].append((first - end) * 1000 / rate)
            else:
                require(first is None, 'failed attempt cannot carry reply timing')
                require(annotation['timeout_observed'] is (sample['outcome'] == 'TIMEOUT'), 'inconsistent timeout annotation')
                if sample['outcome'] == 'TIMEOUT':
                    require(frames - end >= rate * 30, 'timeout requires 30 seconds observed after speech end')
                failures[sample['outcome']] += 1
        cold, warm, overall = stats(values['cold'], 20), stats(values['warm'], 80), stats(values['cold'] + values['warm'], 100)
        result.append({'id': row['id'], 'platform': row['platform'], 'status': 'ANNOTATED', 'cold': cold, 'warm': warm, 'overall': overall, 'configuration_target': 'PASS' if all(s['target'] == 'PASS' for s in (cold, warm, overall)) else 'FAIL', 'non_reply_outcomes': failures})
    require({r['platform'] for r in rows} == {'iOS', 'Android'}, 'each platform needs measured or explicit unrun evidence')
    return {'schema': 1, 'task': 'VC-VERIFY-02', 'plan_sha256': plan_hash, 'evidence_structure': 'VALID', 'physical_acceptance': 'REVIEW_REQUIRED', 'configurations': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path, nargs='?', default=HERE / 'tests/physical-turn-latency.json')
    parser.add_argument('--corpus-root', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = summarize(json.loads(args.report.read_text()), args.corpus_root)
        text = json.dumps(result, indent=2, allow_nan=False) + '\n'
        if args.output:
            require(args.output.resolve() != args.report.resolve(), 'cannot overwrite input report')
            args.output.write_text(text)
        else:
            print(text, end='')
    except (OSError, ValueError, TypeError, KeyError, wave.Error):
        raise SystemExit('Latency evidence rejected; check schema, local checksums and acoustic annotations.') from None


if __name__ == '__main__':
    main()
