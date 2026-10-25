"""Closed aggregate-only validation and comparison of paired noise diagnostics."""
import argparse
import html
import json
from pathlib import Path
from report import validate, digest, sha, read
from diagnostics import need, SOURCES

HERE = Path(__file__).resolve().parent


def validate_suite(suite, reports, clean):
    need(type(suite) is dict and set(suite) == {'schema_version', 'purpose', 'clean_manifest_sha256',
         'noisy_manifest_sha256', 'noise_manifest_sha256', 'source_pins', 'parents', 'variants', 'snrs',
         'pairing', 'threshold_fitting', 'physical', 'production', 'reports'})
    need(type(suite['schema_version']) is int and suite['schema_version'] == 1)
    need(suite['purpose'] == 'PAIRED_NOISE_SCORE_DIAGNOSTIC' and suite['snrs'] == [20, 10, 0])
    need(type(suite['parents']) is int and 1 <= suite['parents'] <= 30)
    need(type(suite['variants']) is int and suite['variants'] == suite['parents'] * 3)
    need(suite['pairing'] == 'SAME_PARENTS_CORRELATED_NOT_INDEPENDENT')
    need(suite['threshold_fitting'] == 'NOT_PERFORMED' and suite['physical'] == 'NOT_RUN' and suite['production'] == 'NOT_ENABLED')
    for key in ('clean_manifest_sha256', 'noisy_manifest_sha256', 'noise_manifest_sha256'):
        digest(suite[key])
    need(type(suite['source_pins']) is dict and set(suite['source_pins']) == {'noise_suite.py', 'run_android.py', 'diagnostics.py', 'main.cpp'})
    for name, value in suite['source_pins'].items():
        need(value == sha(HERE / name))
    need(type(suite['reports']) is dict and set(suite['reports']) == {'20', '10', '0'})
    need(set(reports) == {'20', '10', '0'})
    validate(clean)
    need(clean['cases_total'] == suite['parents'] and clean['provenance']['manifest_sha256'] == suite['clean_manifest_sha256'])
    manifests = {suite['clean_manifest_sha256']}
    for snr, report in reports.items():
        validate(report)
        digest(suite['reports'][snr])
        need(report['cases_total'] == suite['parents'])
        need(report['provenance']['manifest_sha256'] not in manifests)
        manifests.add(report['provenance']['manifest_sha256'])
        for key in ('model_bundle_sha256', 'model_provenance_sha256', 'ort_sha256', 'cxx_sha256', 'source_pins', 'sdk_pins', 'overlay_pins'):
            need(report['provenance'][key] == clean['provenance'][key])
    return suite


def load(root, clean_path):
    suite = read(root / 'suite.json')
    reports = {str(snr): read(root / ('snr' + str(snr) + '.json')) for snr in (20, 10, 0)}
    validate_suite(suite, reports, read(clean_path))
    for snr in reports:
        need(suite['reports'][snr] == sha(root / ('snr' + snr + '.json')))
    return suite, reports, read(clean_path)


def export(root, clean_path, output):
    suite, reports, clean = load(root, clean_path)
    rows = []
    for label, report in [('clean', clean)] + [(snr + ' dB', reports[snr]) for snr in ('20', '10', '0')]:
        for source in report['sources']:
            metrics = source['metrics']
            rows.append(dict(condition=label, source=source['source'], cases_total=report['cases_total'],
                             available=metrics['available'], wer_available=metrics['wer_available'],
                             brier_available=metrics['brier_score'], ece_available=metrics['ece_10_bins'],
                             accepted_0_85=metrics['policy_0_85_diagnostic']['accepted'],
                             errors_0_85=metrics['policy_0_85_diagnostic']['errors']))
    result = dict(schema_version=1, purpose=suite['purpose'], rows=rows,
                  interpretation='DESCRIPTIVE_CORRELATED_REUSED_TEST_SET_NOT_CALIBRATION',
                  denominators='ERROR_METRICS_CONDITIONAL_ON_AVAILABLE_SCORES_COVERAGE_USES_ALL_CASES',
                  physical='NOT_RUN', production='NOT_ENABLED', threshold_authorization='NOT_GRANTED')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    keys = list(rows[0])
    table = '<tr>' + ''.join('<th>' + html.escape(k) + '</th>' for k in keys) + '</tr>'
    for row in rows:
        table += '<tr>' + ''.join('<td>' + html.escape(str(row[k])) + '</td>' for k in keys) + '</tr>'
    (output / 'summary.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Noise score diagnostics</title>'
        '<h1>Paired noise score diagnostics</h1><p>Descriptive reused test set; correlated variants, no threshold fitting or calibration. '
        'Metrics use available scores; all cases remain in coverage denominators. Physical tests NOT_RUN. Production NOT_ENABLED.</p>'
        '<table border="1">' + table + '</table></html>\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=HERE / 'noise-results')
    parser.add_argument('--clean', type=Path, default=HERE / 'corpus-results.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    export(args.input, args.clean, args.output)
