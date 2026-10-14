#!/usr/bin/env python3
"""Physical foreground evidence accounting; no experiment is started here."""
import argparse
import json
import math
from pathlib import Path
import wave
from measure import HERE, audio_info, digest, hash_value, keys, label, quantile, require

PLAN = HERE / 'tests/foreground-plan.json'


def number(value, low, high):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def configuration(config):
    keys(config, ['hardware_kind', 'hardware_model', 'os_build', 'route', 'runtime_revision', 'model_sha256', 'voice_id', 'workload_frozen_before_collection', 'native_pipeline_verified', 'offline_verified', 'resource_trace_sha256', 'peak_rss_bytes', 'pack_bytes', 'thermal_shutdown', 'crashed', 'capture_continuity_verified', 'resource_measurement_method'])
    require(config['hardware_kind'] == 'physical', 'physical evidence required')
    for name in ['hardware_model', 'os_build', 'route', 'runtime_revision', 'voice_id']:
        require(label(config[name]), 'exact configuration required')
    require(hash_value(config['model_sha256']) and hash_value(config['resource_trace_sha256']), 'model/resource trace hashes required')
    for name in ['workload_frozen_before_collection', 'native_pipeline_verified', 'offline_verified']:
        require(config[name] is True, 'frozen/native/offline declarations required')
    for name in ['peak_rss_bytes', 'pack_bytes']:
        require(type(config[name]) is int and 0 < config[name] <= 16_000_000_000, 'invalid resource measurement')
    require(config['resource_measurement_method'] == 'native_process_peak_rss_and_battery_trace', 'native resource method required')
    for name in ['thermal_shutdown', 'crashed', 'capture_continuity_verified']:
        require(type(config[name]) is bool, 'lifecycle result required')


def resources(rows, minutes, screen_off=False):
    require(isinstance(rows, list) and len(rows) == minutes + 1, 'complete minute-by-minute resources required')
    previous = -1
    for minute, row in enumerate(rows):
        keys(row, ['minute', 'elapsed_seconds', 'battery_percent', 'charging', 'rss_bytes', 'thermal_state', 'screen_off', 'capture_available'])
        require(type(row['minute']) is int and row['minute'] == minute and number(row['elapsed_seconds'], max(0, minute * 60 - 5), minute * 60 + 5) and row['elapsed_seconds'] > previous, 'resource clock/order mismatch')
        previous = row['elapsed_seconds']
        require(number(row['battery_percent'], 0, 100) and row['charging'] is False, 'physical uncharged battery measurements required')
        require(type(row['rss_bytes']) is int and 0 < row['rss_bytes'] <= 16_000_000_000, 'invalid native RSS')
        require(row['thermal_state'] in ['nominal', 'fair', 'serious', 'critical'], 'unknown thermal state')
        require(row['screen_off'] is screen_off and type(row['capture_available']) is bool, 'screen/capture observation required')
    require(rows[0]['elapsed_seconds'] == 0 and rows[-1]['elapsed_seconds'] >= minutes * 60, 'full duration required')
    require(all(a['battery_percent'] >= b['battery_percent'] for a, b in zip(rows, rows[1:])), 'battery increase invalidates discharge trial')
    return (rows[0]['battery_percent'] - rows[-1]['battery_percent']) / (minutes / 60)


def measured(row, corpus_root, screen_off=False):
    config = row['configuration']; configuration(config)
    battery_rate = resources(row['resources'], 60, screen_off)
    require(config['peak_rss_bytes'] >= max(r['rss_bytes'] for r in row['resources']), 'peak RSS below sampled RSS')
    turns = row['turns']
    require(isinstance(turns, list) and len(turns) == 60, 'all 60 planned turn attempts required')
    require(corpus_root is not None, 'independent acoustic recordings required')
    root = Path(corpus_root).resolve(strict=True)
    latencies, final, failures, hashes = [], [], 0, set()
    for minute, turn in enumerate(turns):
        keys(turn, ['minute', 'scheduled_seconds', 'started_seconds', 'question_index', 'outcome', 'recording', 'annotation'])
        require(type(turn['minute']) is int and turn['minute'] == minute and type(turn['question_index']) is int and turn['question_index'] == minute % 10 and type(turn['scheduled_seconds']) is int and turn['scheduled_seconds'] == minute * 60, 'frozen turn cadence mismatch')
        require(number(turn['started_seconds'], max(0, minute * 60 - 5), minute * 60 + 5), 'observed turn cadence mismatch')
        require(turn['outcome'] in ['REPLY', 'TIMEOUT', 'FAILED', 'CANCELLED'], 'invalid turn result')
        rate, frames = audio_info(root, turn['recording']); h = turn['recording']['sha256']
        require(h not in hashes, 'reused turn recording'); hashes.add(h)
        a = turn['annotation']; keys(a, ['method', 'reviewer', 'user_speech_end_frame', 'first_meaningful_reply_frame', 'filler_excluded'])
        require(a['method'] == 'independent_same_recording_acoustic_frames' and a['reviewer'] == 'Gemju Sherpa' and a['filler_excluded'] is True, 'reviewed meaningful acoustic timing required')
        end, first = a['user_speech_end_frame'], a['first_meaningful_reply_frame']
        require(type(end) is int and 0 <= end < frames, 'invalid end frame')
        if turn['outcome'] == 'REPLY':
            require(type(first) is int and end <= first < frames, 'invalid reply frame')
            latency = (first - end) * 1000 / rate; latencies.append(latency)
            if minute >= 45: final.append(latency)
        else:
            require(first is None, 'failed turn cannot have latency'); failures += 1
            if turn['outcome'] == 'TIMEOUT': require(frames - end >= rate * 30, 'timeout observation too short')
    median, p95 = quantile(final, .5), quantile(final, .95)
    available = all(r['capture_available'] for r in row['resources'])
    passed = len(final) == 15 and not failures and median <= 1500 and p95 <= 3000 and battery_rate <= 15 and config['peak_rss_bytes'] < 2_500_000_000 and config['pack_bytes'] < 2_000_000_000 and not config['crashed'] and not config['thermal_shutdown'] and available and config['capture_continuity_verified']
    return {'attempted': 60, 'replies': len(latencies), 'non_replies': failures, 'final15_replies': len(final), 'final15_median_ms': median, 'final15_p95_ms': p95, 'battery_points_per_hour': battery_rate, 'peak_rss_bytes': config['peak_rss_bytes'], 'thermal_states_observed': sorted({r['thermal_state'] for r in row['resources']}), 'sampled_capture_available': available, 'capture_continuity_verified': config['capture_continuity_verified'], 'target': 'PASS' if passed else 'FAIL'}


def summarize(report, corpus_root=None):
    keys(report, ['schema', 'task', 'configurations'])
    require(type(report['schema']) is int and report['schema'] == 1 and report['task'] == 'VC-GATE-01', 'wrong foreground schema')
    rows = report['configurations']; require(isinstance(rows, list) and 0 < len(rows) <= 24, 'configuration records required')
    ids, result = set(), []
    for row in rows:
        require(isinstance(row, dict) and label(row.get('id')) and row['id'] not in ids, 'duplicate/invalid ID'); ids.add(row['id'])
        require(row.get('platform') in ['iOS', 'Android'], 'invalid platform')
        if row.get('status') in ['NOT_RUN', 'INCOMPLETE']:
            keys(row, ['id', 'platform', 'status', 'reason', 'observed_seconds'])
            require(label(row['reason']), 'reason required')
            require(row['observed_seconds'] is None if row['status'] == 'NOT_RUN' else number(row['observed_seconds'], 0, 3599.999), 'inconsistent duration')
            result.append({'id': row['id'], 'platform': row['platform'], 'status': row['status'], 'target': 'NOT_RUN' if row['status'] == 'NOT_RUN' else 'FAIL', 'metrics': None}); continue
        keys(row, ['id', 'platform', 'status', 'plan_sha256', 'configuration', 'resources', 'turns'])
        require(row['status'] == 'ANNOTATED' and row['plan_sha256'] == digest(PLAN), 'frozen foreground plan required')
        result.append({'id': row['id'], 'platform': row['platform'], 'status': 'ANNOTATED', 'metrics': measured(row, corpus_root)})
    require({r['platform'] for r in rows} == {'iOS', 'Android'}, 'both platforms require evidence')
    return {'schema': 1, 'task': 'VC-GATE-01', 'physical_acceptance': 'REVIEW_REQUIRED', 'configurations': result}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('report', type=Path, nargs='?', default=HERE / 'tests/physical-foreground.json'); p.add_argument('--corpus-root', type=Path); a = p.parse_args()
    try: print(json.dumps(summarize(json.loads(a.report.read_text()), a.corpus_root), indent=2, allow_nan=False))
    except (OSError, ValueError, TypeError, KeyError, wave.Error): raise SystemExit('Foreground evidence rejected; check complete resources and acoustic records.') from None


if __name__ == '__main__': main()
