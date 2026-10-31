"""Frozen software-audit criteria; this module never fits or activates ASR confidence."""
import argparse
import json
import math
from pathlib import Path
from statistics import NormalDist

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / 'audit-v2-protocol.json'
SOURCES = ('GREEDY_PREBIAS_MEAN_V1', 'SELF_DRAFT_PREBIAS_MEAN_V1')


def need(condition, message='invalid confidence-audit evidence'):
    if not condition:
        raise ValueError(message)


def protocol():
    value = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    need(value['sources'] == list(SOURCES))
    need(value['validation_rule']['attempts_per_source'] == 200)
    return value


def wilson_lower(successes, trials, confidence=0.95):
    """Two-sided Wilson score interval's lower endpoint, without continuity correction."""
    need(type(successes) is int and type(trials) is int and 0 <= successes <= trials and trials > 0)
    need(type(confidence) in (int, float) and math.isfinite(confidence) and 0 < confidence < 1)
    z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    p = successes / trials
    z2 = z * z
    denominator = 1 + z2 / trials
    center = p + z2 / (2 * trials)
    radius = z * math.sqrt(p * (1 - p) / trials + z2 / (4 * trials * trials))
    return (center - radius) / denominator


def evaluate_source(source, attempted, unavailable, accepted, accepted_correct):
    """Apply the frozen validation rule; all attempt failures stay in coverage's denominator."""
    need(source in SOURCES)
    values = (attempted, unavailable, accepted, accepted_correct)
    need(all(type(value) is int for value in values))
    need(0 <= attempted <= 200 and 0 <= unavailable <= attempted)
    need(0 <= accepted <= attempted - unavailable and 0 <= accepted_correct <= accepted)
    if attempted != 200:
        return {
            'source': source,
            'status': 'INCOMPLETE',
            'attempted': attempted,
            'unavailable': unavailable,
            'accepted': accepted,
            'accepted_correct': accepted_correct,
            'coverage': accepted / 200,
            'wilson_lower_95': wilson_lower(accepted_correct, accepted) if accepted else None,
            'passes': False,
        }
    coverage = accepted / attempted
    lower = wilson_lower(accepted_correct, accepted) if accepted else None
    passes = coverage >= 0.30 and lower is not None and lower >= 0.85
    return {
        'source': source,
        'status': 'PASS' if passes else 'FAIL',
        'attempted': attempted,
        'unavailable': unavailable,
        'accepted': accepted,
        'accepted_correct': accepted_correct,
        'coverage': coverage,
        'wilson_lower_95': lower,
        'passes': passes,
    }


def validate_counts(value):
    need(type(value) is dict and set(value) == {'schema_version', 'stage', 'sources'})
    need(type(value['schema_version']) is int and value['schema_version'] == 1)
    # This protocol revision only has a validation-count evaluator. The sealed audit
    # remains inaccessible until a later runner verifies the passing validation
    # artifact and committed mapping hashes before inference.
    need(value['stage'] == 'VALIDATION', 'sealed audit execution is not implemented; keep it closed')
    sources = value['sources']
    need(type(sources) is list and len(sources) == len(SOURCES))
    need(all(type(row) is dict for row in sources))
    need([row.get('source') for row in sources] == list(SOURCES))
    need(all(type(row) is dict and set(row) == {
        'source', 'attempted', 'unavailable', 'accepted', 'accepted_correct'
    } for row in sources))
    result = [evaluate_source(row['source'], row['attempted'], row['unavailable'],
                              row['accepted'], row['accepted_correct']) for row in sources]
    return {
        'schema_version': 1,
        'stage': value['stage'],
        'sources': result,
        'overall': 'PASS' if all(row['passes'] for row in result) else 'NOT_QUALIFIED',
        'software_audit_qualification': 'NOT_ESTABLISHED',
        'native_calibration': 'NOT_ESTABLISHED',
        'threshold_authorization': 'NOT_GRANTED',
        'production': 'NOT_ENABLED',
        'physical': 'NOT_RUN',
        'release': 'HOLD',
        'persistent_memory': 'DISABLED',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--counts', type=Path, required=True,
                        help='local aggregate counts only; never include audio, IDs, text or scores')
    args = parser.parse_args()
    value = json.loads(args.counts.read_text(encoding='utf-8'))
    print(json.dumps(validate_counts(value), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
