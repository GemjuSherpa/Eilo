"""Privacy-reduced JSON/HTML summaries; no remote resources or transcript export."""
import argparse
import html
import json
from pathlib import Path
from benchmark import PHYSICAL_GATES
from noise import validate_report
from manifests import require


def export(value, directory):
    require(value['schema_version'] == 1, 'unsupported report schema')
    require(value['physical_gates'] == {x: 'NOT_RUN' for x in PHYSICAL_GATES}, 'physical gates altered')
    require(value['production_readiness'] == 'NOT_ENABLED', 'production gate altered')
    require(value['status'] in ('MEASURED', 'NOT_RUN'), 'unsupported report status')
    if value['status'] == 'MEASURED':
        validate_report(value)
    else:
        require(value['cases'] == [] and value['metrics'] == {'count': 0} and value['slices'] == {},
                'NOT_RUN cannot contain measured results')
    summary = {key: value[key] for key in ('schema_version', 'status', 'manifest_sha256', 'dataset',
               'release', 'kind', 'physical_gates', 'production_readiness', 'normalization', 'scoring')}
    metric_keys = {'count', 'word_errors', 'reference_words', 'character_errors', 'reference_characters',
                   'wer', 'cer', 'command_accuracy', 'command_balanced_accuracy',
                   'command_accuracy_by_label', 'command_target_count', 'command_target_accuracy', 'confusion', 'vad', 'vad_f1', 'vad_miss_rate',
                   'vad_false_positive_rate', 'rtf'}
    summary['metrics'] = {k: v for k, v in value['metrics'].items() if k in metric_keys}
    summary['slices'] = {name: {k: v for k, v in metrics.items() if k in metric_keys}
                         for name, metrics in value['slices'].items()}
    if 'adapter' in value:
        summary['adapter'] = {key: value['adapter'][key] for key in
                              ('name', 'kind', 'binary_sha256', 'model_sha256', 'config_sha256')}
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    data = json.dumps(summary, indent=2, sort_keys=True, allow_nan=False)
    (directory / 'summary.json').write_text(data + '\n')
    rows = ''.join('<tr><th>' + html.escape(key) + '</th><td>' + html.escape(str(item)) + '</td></tr>'
                   for key, item in summary['metrics'].items())
    document = '<!doctype html><html lang="en"><meta charset="utf-8">' \
        '<meta name="viewport" content="width=device-width,initial-scale=1">' \
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">' \
        '<title>Offline corpus evaluation</title><style>body{font:16px system-ui;max-width:960px;' \
        'margin:2rem auto;padding:1rem;color:#172335;background:#fff}table{border-collapse:collapse}' \
        'th,td{text-align:left;padding:.5rem;border:1px solid #ccc}pre{white-space:pre-wrap;' \
        'overflow-wrap:anywhere}</style><h1>Offline corpus evaluation</h1>' \
        '<p>Status: <strong>' + html.escape(value['status']) + '</strong>. Evidence: ' + \
        html.escape(value['kind']) + '.</p><p>All physical-device gates: NOT_RUN. ' \
        'Production readiness: NOT_ENABLED. Desktop results require review.</p>' \
        '<table><caption>Aggregate metrics</caption>' + rows + '</table><h2>Provenance and slices</h2><pre>' + \
        html.escape(data) + '</pre></html>'
    (directory / 'summary.html').write_text(document)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    export(json.loads(args.report.read_text()), args.output)


if __name__ == '__main__':
    main()
