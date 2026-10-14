#!/usr/bin/env python3
"""Eight-hour standby accounting. No capture/keepalive or automatic revival."""
import argparse
import json
from pathlib import Path
from measure import HERE, digest, hash_value, keys, label, require
from endurance import configuration, number, resources
from screen_off import background

PLAN = HERE / 'tests/standby-plan.json'


def summarize(report):
    keys(report, ['schema', 'task', 'configurations'])
    require(type(report['schema']) is int and report['schema'] == 1 and report['task'] == 'VC-GATE-03', 'wrong standby schema')
    rows = report['configurations']; require(isinstance(rows, list) and 0 < len(rows) <= 24, 'configuration records required')
    ids, result = set(), []
    schedule = json.loads(PLAN.read_text())['directed_wakes']
    for row in rows:
        require(isinstance(row, dict) and label(row.get('id')) and row['id'] not in ids, 'duplicate/invalid ID'); ids.add(row['id'])
        require(row.get('platform') in ['iOS', 'Android'], 'invalid platform')
        if row.get('status') in ['NOT_RUN', 'INCOMPLETE']:
            keys(row, ['id', 'platform', 'status', 'reason', 'observed_seconds'])
            require(label(row['reason']), 'reason required')
            require(row['observed_seconds'] is None if row['status'] == 'NOT_RUN' else number(row['observed_seconds'], 0, 28799.999), 'inconsistent duration')
            result.append({'id': row['id'], 'platform': row['platform'], 'status': row['status'], 'target': 'NOT_RUN' if row['status'] == 'NOT_RUN' else 'FAIL', 'metrics': None}); continue
        keys(row, ['id', 'platform', 'status', 'plan_sha256', 'configuration', 'background_evidence', 'ambient_corpus_sha256', 'resources', 'directed_wakes', 'false_activations', 'activation_count', 'no_automatic_revival_observed', 'reviewer'])
        require(row['status'] == 'ANNOTATED' and row['plan_sha256'] == digest(PLAN), 'frozen eight-hour plan required')
        config = row['configuration']; configuration(config); background(row['background_evidence'])
        require(hash_value(row['ambient_corpus_sha256']) and row['reviewer'] == 'Gemju Sherpa', 'reviewed frozen ambient evidence required')
        rate = resources(row['resources'], 480, screen_off=True)
        require(config['peak_rss_bytes'] >= max(r['rss_bytes'] for r in row['resources']), 'peak RSS below samples')
        wakes = row['directed_wakes']; require(isinstance(wakes, list) and len(wakes) == 100, 'all 100 scheduled wakes required')
        detected = 0
        for expected, event in zip(schedule, wakes):
            keys(event, ['id', 'scheduled_seconds', 'observed_seconds', 'detected'])
            require(event['id'] == expected['id'] and type(event['scheduled_seconds']) is int and event['scheduled_seconds'] == expected['seconds'], 'wake schedule mismatch')
            require(number(event['observed_seconds'], expected['seconds'] - 5, expected['seconds'] + 5) and type(event['detected']) is bool, 'actual wake observation required')
            detected += int(event['detected'])
        false = row['false_activations']; require(isinstance(false, list) and len(false) <= 10000, 'false activation observations required')
        previous = -1
        for event in false:
            keys(event, ['elapsed_seconds'])
            require(number(event['elapsed_seconds'], 0, 28800) and event['elapsed_seconds'] > previous, 'false activation clock/order mismatch')
            previous = event['elapsed_seconds']
        require(type(row['activation_count']) is int and row['activation_count'] == detected + len(false), 'unaccounted or duplicate activation')
        require(type(row['no_automatic_revival_observed']) is bool, 'revival observation required')
        available = all(r['capture_available'] for r in row['resources']) and config['capture_continuity_verified']
        passed = detected >= 95 and len(false) <= 1 and rate <= 2 and available and row['no_automatic_revival_observed'] and not config['crashed'] and not config['thermal_shutdown'] and config['peak_rss_bytes'] < 2_500_000_000 and config['pack_bytes'] < 2_000_000_000
        result.append({'id': row['id'], 'platform': row['platform'], 'status': 'ANNOTATED', 'metrics': {'hours': 8, 'directed_attempts': 100, 'detected': detected, 'missed': 100 - detected, 'recall_percent': detected, 'false_activations': len(false), 'battery_points_per_hour': rate, 'continuous_availability_verified': available, 'peak_rss_bytes': config['peak_rss_bytes'], 'thermal_states_observed': sorted({r['thermal_state'] for r in row['resources']}), 'target': 'PASS' if passed else 'FAIL'}})
    require({r['platform'] for r in rows} == {'iOS', 'Android'}, 'both platforms require evidence')
    return {'schema': 1, 'task': 'VC-GATE-03', 'physical_acceptance': 'REVIEW_REQUIRED', 'configurations': result}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('report', type=Path, nargs='?', default=HERE / 'tests/physical-standby.json'); a = p.parse_args()
    try: print(json.dumps(summarize(json.loads(a.report.read_text())), indent=2, allow_nan=False))
    except (OSError, ValueError, TypeError, KeyError): raise SystemExit('Standby evidence rejected; check complete eight-hour trace and wake accounting.') from None


if __name__ == '__main__': main()
