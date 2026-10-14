"""Content-addressed regression candidates; review happens through the task PR."""
import argparse
import json
import math
from pathlib import Path
from benchmark import normalize, provenance
from manifests import canonical_digest, require
from noise import compare, validate_report


def bind(manifest, report):
    validate_report(report)
    provenance(report['adapter'])
    require(report['manifest_sha256'] == canonical_digest(manifest), 'manifest changed')
    for key in ('dataset', 'release', 'kind'):
        require(manifest[key] == report[key], 'corpus identity changed')
    expected = {x['id']: x for x in manifest['cases']}
    require(len(expected) == len(manifest['cases']), 'duplicate manifest IDs')
    require(len(report['cases']) == len(expected), 'case count changed')
    require(len({x['id'] for x in report['cases']}) == len(expected), 'duplicate report IDs')
    require({x['id'] for x in report['cases']} == set(expected), 'case IDs changed')
    for case in report['cases']:
        source = expected[case['id']]
        require(case['task'] == source['task'] and case['slice'] == source['slice'], 'case identity changed')
        require(case['audio_seconds'] == source['samples'] / manifest['rate'], 'duration changed')
        if source['task'] in ('asr', 'commands'):
            reference = normalize(source['reference'])
            require(case['reference_words'] == len(reference.split()) and
                    case['reference_characters'] == len(reference), 'reference counts changed')
            for field in ('word_errors', 'character_errors'):
                require(type(case[field]) is int and case[field] >= 0, 'invalid error count')
        if source['task'] == 'commands':
            require(case['confusion'][0] == source['command'], 'command truth changed')
            require(type(case['correct']) is int and case['correct'] ==
                    int(case['confusion'][0] == case['confusion'][1]), 'command result inconsistent')
        if source['task'] == 'vad':
            require(set(case['vad']) == {'tp', 'fp', 'fn', 'tn'}, 'invalid VAD counters')
            require(all(type(x) is int and x >= 0 for x in case['vad'].values()), 'invalid VAD count')
            require(sum(case['vad'].values()) == math.ceil(case['audio_seconds'] / 0.02),
                    'VAD frame total changed')
    return report


def candidate(manifest, baseline, tolerances):
    bind(manifest, baseline)
    compare(baseline, baseline, tolerances)
    return {'schema_version': 1, 'purpose': 'DIAGNOSTIC_REGRESSION',
            'review_status': 'CANDIDATE_FOR_PR_REVIEW',
            'manifest_sha256': canonical_digest(manifest),
            'report_sha256': canonical_digest(baseline),
            'tolerances': tolerances, 'tolerances_sha256': canonical_digest(tolerances),
            'physical_gates': baseline['physical_gates']}


def check(lock, manifest, baseline, current):
    require(lock == candidate(manifest, baseline, lock['tolerances']), 'baseline lock changed')
    bind(manifest, current)
    result = compare(baseline, current, lock['tolerances'])
    return {**result, 'baseline_lock_sha256': canonical_digest(lock),
            'purpose': lock['purpose'], 'review_status': lock['review_status']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('candidate', 'check'))
    for name in ('manifest', 'baseline', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--tolerances', type=Path)
    parser.add_argument('--lock', type=Path)
    parser.add_argument('--current', type=Path)
    args = parser.parse_args()
    def read(path):
        require(path is not None, 'missing operation argument')
        return json.loads(path.read_text())
    manifest, baseline = read(args.manifest), read(args.baseline)
    value = (candidate(manifest, baseline, read(args.tolerances)) if args.operation == 'candidate'
             else check(read(args.lock), manifest, baseline, read(args.current)))
    require(not args.output.exists(), 'refusing to overwrite evidence')
    args.output.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    if value.get('status') == 'FAIL':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
