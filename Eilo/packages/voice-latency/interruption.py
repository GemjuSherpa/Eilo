#!/usr/bin/env python3
"""Acoustic interruption evidence. Reviewed declarations are not device proof."""
import argparse
import json
from pathlib import Path
import wave
from measure import HERE, audio_info, digest, hash_value, keys, label, quantile, require

PLAN = HERE / 'tests/interruption-plan.json'


def summarize(report, corpus_root=None):
    keys(report, ['schema', 'task', 'configurations'])
    require(type(report['schema']) is int and report['schema'] == 1 and report['task'] == 'VC-VERIFY-03', 'wrong interruption schema')
    rows = report['configurations']
    require(isinstance(rows, list) and 0 < len(rows) <= 24, 'configuration records required')
    output, ids = [], set()
    for row in rows:
        require(isinstance(row, dict) and label(row.get('id')) and row['id'] not in ids, 'duplicate/invalid configuration')
        ids.add(row['id'])
        require(row.get('platform') in ('iOS', 'Android'), 'invalid platform')
        if row.get('status') == 'NOT_RUN':
            keys(row, ['id', 'platform', 'status', 'reason', 'samples', 'noise_controls'])
            require(label(row['reason']) and row['samples'] == [] and row['noise_controls'] == [], 'unrun evidence cannot contain results')
            output.append({'id': row['id'], 'platform': row['platform'], 'status': 'NOT_RUN', 'p95_ms': None, 'target': 'NOT_RUN'})
            continue
        keys(row, ['id', 'platform', 'status', 'configuration', 'plan_sha256', 'samples', 'noise_controls'])
        require(row['status'] == 'ANNOTATED' and row['plan_sha256'] == digest(PLAN), 'exact frozen interruption plan required')
        config = row['configuration']
        keys(config, ['hardware_kind', 'hardware_model', 'os_build', 'route', 'model_sha256', 'runtime_revision', 'voice_id', 'native_pipeline_verified', 'offline_verified', 'input_corpus_sha256', 'corpus_frozen_before_collection'])
        require(config['hardware_kind'] == 'physical' and config['native_pipeline_verified'] is True and config['offline_verified'] is True and config['corpus_frozen_before_collection'] is True, 'physical native offline evidence required')
        for field in ['hardware_model', 'os_build', 'route', 'runtime_revision', 'voice_id']:
            require(label(config[field]), 'exact configuration required')
        require(hash_value(config['model_sha256']) and hash_value(config['input_corpus_sha256']), 'model/corpus hashes required')
        require(corpus_root is not None, 'independent local recordings required')
        root = Path(corpus_root).resolve(strict=True)
        plan = json.loads(PLAN.read_text())
        require(isinstance(row['samples'], list) and len(row['samples']) == 100 and isinstance(row['noise_controls'], list) and len(row['noise_controls']) == 20, 'all interruption and noise attempts required')
        latencies, misses, resumption, hashes = [], 0, 0, set()
        for expected, sample in zip(plan['schedule'], row['samples']):
            keys(sample, ['id', 'clause_position', 'outcome', 'recording', 'annotation'])
            require(sample['id'] == expected['id'] and sample['clause_position'] == expected['clause_position'], 'frozen attempt mismatch')
            require(sample['outcome'] in ('STOPPED', 'MISSED', 'CANCELLED'), 'invalid interruption outcome')
            rate, frames = audio_info(root, sample['recording'])
            h = sample['recording']['sha256']
            require(h not in hashes, 'recording reused'); hashes.add(h)
            a = sample['annotation']
            keys(a, ['method', 'reviewer', 'intelligible_user_onset_frame', 'last_old_audio_frame', 'old_audio_resumed', 'old_audio_observed_before_onset', 'observation_end_frame'])
            require(a['method'] == 'independent_same_recording_acoustic_frames' and a['reviewer'] == 'Gemju Sherpa', 'SDK stop is not audible stop')
            onset, end, last = a['intelligible_user_onset_frame'], a['observation_end_frame'], a['last_old_audio_frame']
            require(type(onset) is int and type(end) is int and 0 < onset < end < frames and end - onset >= rate, 'at least one second post-onset observation required')
            require(a['old_audio_observed_before_onset'] is True and type(a['old_audio_resumed']) is bool, 'old playback overlap and resumption annotation required')
            resumption += int(a['old_audio_resumed'])
            if sample['outcome'] == 'STOPPED':
                require(type(last) is int and onset <= last < end, 'invalid last old audible frame')
                latencies.append((last - onset) * 1000 / rate)
            else:
                require(last is None, 'miss/cancellation cannot have stop timing'); misses += 1
        false_triggers = 0
        for expected, sample in zip(plan['noise_controls'], row['noise_controls']):
            keys(sample, ['id', 'outcome', 'recording', 'reviewer'])
            require(sample['id'] == expected['id'] and sample['reviewer'] == 'Gemju Sherpa' and sample['outcome'] in ('IGNORED', 'FALSE_TRIGGER'), 'noise control annotation required')
            audio_info(root, sample['recording']); h = sample['recording']['sha256']
            require(h not in hashes, 'recording reused'); hashes.add(h)
            false_triggers += int(sample['outcome'] == 'FALSE_TRIGGER')
        p95 = quantile(latencies, .95)
        output.append({'id': row['id'], 'platform': row['platform'], 'status': 'ANNOTATED', 'attempted': 100, 'stopped': len(latencies), 'missed_or_cancelled': misses, 'resumptions': resumption, 'noise_attempted': 20, 'false_triggers': false_triggers, 'p95_ms': p95, 'distribution_scope': 'observed stops only; misses/resumptions/noise failures prevent passing', 'target': 'PASS' if p95 is not None and p95 <= 300 and not (misses or resumption or false_triggers) else 'FAIL'})
    require({r['platform'] for r in rows} == {'iOS', 'Android'}, 'both platforms need explicit evidence')
    return {'schema': 1, 'task': 'VC-VERIFY-03', 'physical_acceptance': 'REVIEW_REQUIRED', 'configurations': output}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('report', type=Path, nargs='?', default=HERE / 'tests/physical-interruption.json')
    p.add_argument('--corpus-root', type=Path)
    args = p.parse_args()
    try:
        print(json.dumps(summarize(json.loads(args.report.read_text()), args.corpus_root), indent=2, allow_nan=False))
    except (OSError, ValueError, TypeError, KeyError, wave.Error):
        raise SystemExit('Interruption evidence rejected; inspect local schema, recordings and acoustic annotations.') from None


if __name__ == '__main__':
    main()
