#!/usr/bin/env python3
"""Screen-off endurance accounting; never enables a background capability."""
import argparse
import json
from pathlib import Path
import wave
from measure import HERE, digest, hash_value, keys, label, require
from endurance import measured, number

PLAN = HERE / 'tests/screen-off-plan.json'


def background(evidence):
    keys(evidence, ['consent_verified', 'permitted_execution_verified', 'generic_locked_policy_review', 'no_keepalive_workaround', 'policy_revision', 'lifecycle_trace_sha256'])
    require(evidence['consent_verified'] is True and evidence['permitted_execution_verified'] is True and evidence['no_keepalive_workaround'] is True and evidence['generic_locked_policy_review'] == 'APPROVED_FOR_GENERIC_AUDIO', 'reviewed permitted generic background execution required')
    require(label(evidence['policy_revision']) and hash_value(evidence['lifecycle_trace_sha256']), 'exact policy and lifecycle trace required')


def summarize(report, corpus_root=None):
    keys(report, ['schema', 'task', 'configurations'])
    require(type(report['schema']) is int and report['schema'] == 1 and report['task'] == 'VC-GATE-02', 'wrong screen-off schema')
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
        keys(row, ['id', 'platform', 'status', 'plan_sha256', 'configuration', 'resources', 'turns', 'background_evidence'])
        require(row['status'] == 'ANNOTATED' and row['plan_sha256'] == digest(PLAN), 'frozen screen-off plan required')
        background(row['background_evidence'])
        result.append({'id': row['id'], 'platform': row['platform'], 'status': 'ANNOTATED', 'metrics': measured(row, corpus_root, screen_off=True)})
    require({r['platform'] for r in rows} == {'iOS', 'Android'}, 'both platforms require evidence')
    return {'schema': 1, 'task': 'VC-GATE-02', 'physical_acceptance': 'REVIEW_REQUIRED', 'configurations': result}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('report', type=Path, nargs='?', default=HERE / 'tests/physical-screen-off.json'); p.add_argument('--corpus-root', type=Path); a = p.parse_args()
    try: print(json.dumps(summarize(json.loads(a.report.read_text()), a.corpus_root), indent=2, allow_nan=False))
    except (OSError, ValueError, TypeError, KeyError, wave.Error): raise SystemExit('Screen-off evidence rejected; check permission/policy and physical acoustic/resource evidence.') from None


if __name__ == '__main__': main()
