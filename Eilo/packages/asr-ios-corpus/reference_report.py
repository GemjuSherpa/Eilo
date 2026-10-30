"""Validate and export aggregate-only, previously exposed iOS ASR diagnostics."""
import argparse
import hashlib
import html
import importlib.util
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PACKAGES = HERE.parent
CORPUS = PACKAGES / 'asr-corpus-score'
DATASET = PACKAGES / 'dataset-evaluation'
sys.path[:0] = [str(CORPUS), str(DATASET)]
from diagnostics import SOURCES, REASONS, need
from replay import pins as replay_pins

_spec = importlib.util.spec_from_file_location('ios_corpus_legacy_report', CORPUS / 'report.py')
_legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_legacy)
validate_metrics = _legacy.validate_metrics

GROUPS = {'exposed_original': 30, 'exposed_development': 30,
          'exposed_prior_test': 30, 'exposed_audit_test': 30,
          'snr_20': 30, 'snr_10': 30, 'snr_0': 30}
FLAGS = {
    'data_status': 'PREVIOUSLY_EXPOSED_NOT_HELD_OUT', 'calibrator_refit': 'NOT_PERFORMED',
    'threshold_fitting': 'NOT_PERFORMED', 'calibration': 'NOT_ESTABLISHED',
    'threshold': 'NOT_GRANTED', 'calibration_transfer': 'NOT_AUTHORIZED',
    'training_overlap': 'UNKNOWN', 'physical': 'NOT_RUN', 'production': 'NOT_ENABLED',
    'microphone': 'NOT_OPENED', 'speech': 'NOT_STARTED', 'llm': 'NOT_RUN',
    'release': 'HOLD', 'persistent_memory': 'DISABLED', 'vad': 'BYPASSED',
    'end_to_end_false_activation': 'NOT_MEASURED',
    'negative_labels': 'MUSAN_WEAK_LABELS_SYNTHETIC_NO_SPEECH_ONLY',
    'noise_pairing': 'SAME_30_EXPOSED_AUDIT_PARENTS_CORRELATED',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique(pairs):
    value = {}
    for key, item in pairs:
        need(key not in value)
        value[key] = item
    return value


def read(path):
    need(path.stat().st_size <= 2 * 1024 * 1024)
    def reject(_): raise ValueError('nonfinite aggregate value')
    return json.loads(path.read_text(), object_pairs_hook=unique, parse_constant=reject)


def validate(result, protocol_path=None):
    need(type(result) is dict and type(result.get('schema_version')) is int and result['schema_version'] == 1)
    need(result.get('purpose') == 'IOS_EXPOSED_REFERENCE_NOISE_DIAGNOSTIC')
    required = {'schema_version', 'purpose', 'protocol_commit', 'source_pins', 'protocol_sha256',
        'runtime_object_sha256', 'model_provenance_sha256', 'binary_sha256', 'private_counts_sha256',
        'smoke', 'relocation', 'clean', 'noise', 'negative', 'collector_errors', 'rejected_inputs', *FLAGS}
    need(set(result) == required)
    for key, value in FLAGS.items(): need(result[key] == value)
    need(type(result['protocol_commit']) is str and len(result['protocol_commit']) == 40
         and all(c in '0123456789abcdef' for c in result['protocol_commit']))
    for key in ('protocol_sha256', 'runtime_object_sha256', 'model_provenance_sha256', 'binary_sha256', 'private_counts_sha256'):
        value = result[key]
        need(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value))
    need(result['smoke'] == 'TWO_AVAILABLE_SCORE_PATHS')
    need(result['relocation'] == 'ORIGINAL_BINARY_ABSENT_NO_CUSTOM_DYNAMIC_DEPENDENCY_OR_RPATH')
    need(type(result['source_pins']) is list and result['source_pins'])
    for pin in result['source_pins']:
        need(type(pin) is dict and set(pin) == {'path', 'sha256'} and type(pin['path']) is str)
        need(type(pin['sha256']) is str and len(pin['sha256']) == 64 and all(c in '0123456789abcdef' for c in pin['sha256']))
    need(len({pin['path'] for pin in result['source_pins']}) == len(result['source_pins']))
    need(result['source_pins'] == replay_pins())
    for pin in result['source_pins']:
        path = (PACKAGES / pin['path']).resolve()
        need(path.is_relative_to(PACKAGES.resolve()) and path.is_file() and sha(path) == pin['sha256'])
    if protocol_path is not None:
        protocol = read(protocol_path)
        need(result['protocol_sha256'] == sha(protocol_path))
        need(protocol['purpose'] == result['purpose'] and protocol['runtime'] == 'APPROVED_VENDOR_PRELINKED_ORT_1_23_2')
        need(protocol['manifests'] and result['data_status'] == protocol['data_status'])
        need(protocol['diagnostic_cutoff'] == 0.85)

    clean = result['clean']; noise = result['noise']
    need(type(clean) is list and [r.get('group') for r in clean] == list(GROUPS)[:4])
    need(type(noise) is list and [r.get('group') for r in noise] == ['snr_20', 'snr_10', 'snr_0'])
    rows = []
    for bucket in clean + noise:
        group = bucket['group']; reports = bucket.get('reports')
        need(set(bucket) == {'group', 'reports'} and type(reports) is list and len(reports) == 2)
        need([r.get('source') for r in reports] == list(SOURCES))
        total = GROUPS[group]
        for report in reports:
            need(set(report) == {'source', 'status', 'scope', 'unavailable_reasons', 'origin_case_counts', 'metrics'})
            need(report['scope'] == 'PREVIOUSLY_EXPOSED_DIAGNOSTIC_ONLY')
            m = validate_metrics(report['metrics'], total)
            reasons = report['unavailable_reasons']
            need(type(reasons) is dict and set(reasons) <= REASONS and sum(reasons.values()) == m['unavailable'])
            need(all(type(v) is int and 0 < v <= total for v in reasons.values()))
            origins = report['origin_case_counts']
            need(type(origins) is dict and set(origins) <= {'greedy', 'verification', 'redecode'})
            need(all(type(v) is int and 0 <= v <= m['available'] for v in origins.values()))
            need(sum(origins.values()) >= m['available'])
            expected = ('NO_AVAILABLE_SCORES' if not m['available'] else
                        'INCOMPLETE_SCORES' if m['unavailable'] else 'DIAGNOSTIC_ONLY')
            need(report['status'] == expected)
            p = m['policy_0_85_diagnostic']
            rows.append(dict(group=group, source=report['source'], cases=total, available=m['available'],
                unavailable=m['unavailable'], exact_matches=m['correct'], wer_available=m['wer_available'],
                accepted_0_85=p['accepted'], errors_0_85=p['errors'],
                unavailable_reasons=reasons))

    negative = result['negative']
    need(type(negative) is list and len(negative) == 6)
    need([(r.get('group'), r.get('source')) for r in negative] ==
         [(g, s) for g in ('musan_weak_noise', 'digital_silence', 'uniform_noise') for s in SOURCES])
    for r in negative:
        need(set(r) == {'group', 'source', 'cases', 'available', 'unavailable', 'unavailable_reasons', 'observed_word_bearing', 'raw_0_85_word_bearing'})
        total = {'musan_weak_noise': 12, 'digital_silence': 3, 'uniform_noise': 3}[r['group']]
        need(r['cases'] == total and r['available'] + r['unavailable'] == total)
        need(all(type(r[k]) is int and 0 <= r[k] <= total for k in ('available', 'unavailable', 'observed_word_bearing', 'raw_0_85_word_bearing')))
        need(r['raw_0_85_word_bearing'] <= r['observed_word_bearing'] <= r['available'])
        reasons = r['unavailable_reasons']; need(type(reasons) is dict and set(reasons) <= REASONS)
        need(all(type(v) is int and 0 < v <= total for v in reasons.values()) and sum(reasons.values()) == r['unavailable'])
    observed_collector_errors = sum(report['unavailable_reasons'].get('COLLECTOR_ERROR', 0)
        for bucket in clean + noise for report in bucket['reports']) + sum(
        r['unavailable_reasons'].get('COLLECTOR_ERROR', 0) for r in negative)
    need(type(result['collector_errors']) is int and result['collector_errors'] == observed_collector_errors)
    need(result['rejected_inputs'] == ['empty', 'unaligned', 'nan', 'out_of_range'])
    return dict(status='DIAGNOSTIC_ONLY', clean_and_noise_rows=len(rows), negative_groups=len(negative),
        available_scores_by_source={source: sum(r['available'] for r in rows if r['source'] == source) for source in SOURCES},
        collector_errors=result['collector_errors'], native_calibration='NOT_ESTABLISHED',
        threshold_authorization='NOT_GRANTED', physical='NOT_RUN', release='HOLD')


def export(result, output, protocol_path=None):
    summary = validate(result, protocol_path)
    need(not output.exists())
    output.mkdir(parents=True)
    public = dict(schema_version=1, purpose=result['purpose'], status='DIAGNOSTIC_ONLY',
        data_status=result['data_status'], model_training_overlap=result['training_overlap'],
        rows=[{k: v for k, v in row.items() if k != 'unavailable_reasons'} | {'unavailable_reasons': row['unavailable_reasons']} for row in _rows(result)],
        negative=result['negative'],
        controls=dict(calibrator_refit=result['calibrator_refit'], threshold_fitting=result['threshold_fitting'],
            calibration=result['calibration'], threshold=result['threshold'], calibration_transfer=result['calibration_transfer'],
            vad=result['vad'], end_to_end_false_activation=result['end_to_end_false_activation']),
        physical=result['physical'], production=result['production'], release=result['release'],
        persistent_memory=result['persistent_memory'], rejected_inputs=result['rejected_inputs'], collector_errors=result['collector_errors'])
    (output / 'summary.json').write_text(json.dumps(public, indent=2, allow_nan=False) + '\n')
    table = ''.join('<tr>' + ''.join('<td>' + html.escape(str(row[k])) + '</td>' for k in ('group', 'source', 'cases', 'available', 'unavailable', 'exact_matches', 'wer_available', 'accepted_0_85', 'errors_0_85')) + '</tr>' for row in public['rows'])
    page = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>iOS ASR reference diagnostics</title>'
        '<h1>Previously exposed iOS ASR diagnostics</h1><p>All audio partitions were previously exposed. These descriptive results do not establish calibration, authorize a threshold, or qualify a release. Training overlap is UNKNOWN. VAD was bypassed; end-to-end false activation was not measured.</p>'
        '<p>WER is conditional on available scores. Coverage uses all cases. Correlated noise variants reuse the same exposed parents. MUSAN labels are weak; silence and noise are synthetic controls.</p>'
        '<table border="1"><tr><th>Group</th><th>Score path</th><th>Cases</th><th>Available</th><th>Unavailable</th><th>Exact matches</th><th>WER available</th><th>Raw scores ≥0.85</th><th>Errors ≥0.85</th></tr>' + table + '</table>'
        '<p>Physical: NOT RUN. Production: NOT ENABLED. Release: HOLD. Persistent memory: DISABLED.</p></html>\n')
    (output / 'summary.html').write_text(page)
    return summary


def _rows(result):
    return [{**row, 'unavailable_reasons': report['unavailable_reasons']}
        for bucket in result['clean'] + result['noise'] for report in bucket['reports']
        for row in [dict(group=bucket['group'], source=report['source'], cases=report['metrics']['cases_total'],
            available=report['metrics']['available'], unavailable=report['metrics']['unavailable'],
            exact_matches=report['metrics']['correct'], wer_available=report['metrics']['wer_available'],
            accepted_0_85=report['metrics']['policy_0_85_diagnostic']['accepted'],
            errors_0_85=report['metrics']['policy_0_85_diagnostic']['errors'])]]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=HERE / 'ios-reference-results.json')
    parser.add_argument('--protocol', type=Path, default=HERE / 'protocol.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    value = read(args.report)
    print(json.dumps(validate(value, args.protocol), indent=2))
    if args.output: export(value, args.output, args.protocol)
