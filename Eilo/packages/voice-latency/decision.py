#!/usr/bin/env python3
"""Check a pending feasibility report, never grant scope/release approval."""
import argparse
import json
from pathlib import Path
from measure import HERE, digest, hash_value, keys, label, local_file, require

REQUIRED = ['VC-GATE-01', 'VC-GATE-02', 'VC-GATE-03', 'VC-VERIFY-02', 'VC-VERIFY-03', 'VC-TURN-09', 'VC-TURN-10', 'VC-LLM-06', 'VC-VOICE-06']
EILO = HERE.parents[1]


def validate(report, artifact_root=EILO):
    keys(report, ['schema', 'task', 'review_state', 'recommendation', 'supported_configurations', 'persistent_memory_allowed', 'platforms', 'policy_observations'])
    require(type(report['schema']) is int and report['schema'] == 1 and report['task'] == 'VC-GATE-04', 'wrong decision schema')
    require(report['review_state'] == 'PENDING_GEMJU_SHERPA' and report['recommendation'] == 'HOLD_PENDING_PHYSICAL_EVIDENCE' and report['supported_configurations'] == [] and report['persistent_memory_allowed'] is False, 'pending report cannot approve support or memory')
    require(isinstance(report['platforms'], list) and all(isinstance(r, dict) for r in report['platforms']) and [r.get('platform') for r in report['platforms']] == ['iOS', 'Android'], 'both platform matrices required')
    root = Path(artifact_root).resolve(strict=True)
    for row in report['platforms']:
        keys(row, ['platform', 'configuration_id', 'gates'])
        require(label(row['configuration_id']) and isinstance(row['gates'], list) and all(isinstance(g, dict) for g in row['gates']) and [g.get('task') for g in row['gates']] == REQUIRED, 'all nine dependencies required in stable order')
        for gate in row['gates']:
            keys(gate, ['task', 'physical_status', 'evidence_kind', 'artifact', 'sha256', 'blocker'])
            require(gate['physical_status'] in ['NOT_RUN', 'BLOCKED', 'FAIL'] and gate['evidence_kind'] in ['unrun', 'policy_observation', 'physical'], 'no inferred physical pass in pending report')
            require(gate['physical_status'] != 'NOT_RUN' or gate['evidence_kind'] == 'unrun', 'unrun status must remain unrun evidence')
            require(gate['physical_status'] != 'FAIL' or gate['evidence_kind'] == 'physical', 'source-policy denial is not a failed physical trial')
            require(label(gate['blocker']) or (isinstance(gate['blocker'], str) and 0 < len(gate['blocker']) <= 512), 'explicit blocker required')
            require(hash_value(gate['sha256']) and digest(local_file(root, gate['artifact'])) == gate['sha256'], 'stale/missing dependency evidence')
    observations = report['policy_observations']
    require(isinstance(observations, list) and 0 < len(observations) <= 16, 'policy observations required')
    for item in observations:
        keys(item, ['artifact', 'sha256', 'observation'])
        require(label(item['observation']) or (isinstance(item['observation'], str) and 0 < len(item['observation']) <= 512), 'bounded policy observation required')
        require(hash_value(item['sha256']) and digest(local_file(root, item['artifact'])) == item['sha256'], 'policy source revision changed')
    return {'task': 'VC-GATE-04', 'report_structure': 'VALID', 'physical_acceptance': 'NOT_ESTABLISHED', 'recommendation': report['recommendation'], 'decision': 'PENDING_GEMJU_SHERPA', 'supported_configurations': [], 'persistent_memory_allowed': False}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('report', type=Path, nargs='?', default=EILO / 'docs/sprints/S08_FEASIBILITY_DECISION.json'); a = p.parse_args()
    try: print(json.dumps(validate(json.loads(a.report.read_text())), indent=2))
    except (OSError, ValueError, TypeError, KeyError): raise SystemExit('Decision report rejected; cannot infer approval from missing or stale evidence.') from None


if __name__ == '__main__': main()
