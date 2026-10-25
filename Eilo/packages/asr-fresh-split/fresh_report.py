"""Closed aggregate-only fresh dev/test diagnostics; never an acceptance authority."""
import argparse
import html
import json
from pathlib import Path
from shared import HERE, CORPUS, SDK, need, sha, read, protocol, source_pins, canonical_digest, corpus_report, SOURCES, REASONS


def validate_selection(e):
    need(type(e) is dict and set(e) == {'schema_version', 'purpose', 'protocol_sha256', 'prior_manifest_sha256',
         'receipt_sha256', 'source_pins', 'partitions', 'prior_speaker_overlap', 'prior_utterance_overlap',
         'cross_speaker_overlap', 'cross_utterance_overlap', 'model_training_overlap', 'physical', 'production'})
    need(type(e['schema_version']) is int and e['schema_version'] == 1 and e['purpose'] == protocol()['purpose'])
    need(e['protocol_sha256'] == sha(HERE / 'protocol.json') and e['source_pins'] == source_pins())
    baseline = read(CORPUS / 'corpus-results.json')
    need(e['prior_manifest_sha256'] == baseline['provenance']['manifest_sha256'])
    corpus_report.digest(e['receipt_sha256'])
    for key in ('prior_speaker_overlap', 'prior_utterance_overlap', 'cross_speaker_overlap', 'cross_utterance_overlap'):
        need(type(e[key]) is int and e[key] == 0)
    need(e['model_training_overlap'] == 'UNKNOWN' and e['physical'] == 'NOT_RUN' and e['production'] == 'NOT_ENABLED')
    need(type(e['partitions']) is dict and set(e['partitions']) == {'dev', 'test'})
    manifests = {e['prior_manifest_sha256']}
    for split in ('dev', 'test'):
        p = e['partitions'][split]
        need(type(p) is dict and set(p) == {'cases', 'speakers', 'manifest_sha256'})
        need(type(p['cases']) is int and p['cases'] == 30)
        need(type(p['speakers']) is int and 15 <= p['speakers'] <= 30)
        corpus_report.digest(p['manifest_sha256'])
        need(p['manifest_sha256'] not in manifests)
        manifests.add(p['manifest_sha256'])


def validate(r):
    need(type(r) is dict and set(r) == {'schema_version', 'purpose', 'selection', 'source_pins', 'model_bundle_sha256',
         'ort_sha256', 'runtime_sha256', 'cxx_sha256', 'overlay_pins', 'partitions', 'rejected_inputs', 'threshold_fitting',
         'model_training_overlap', 'native_calibration', 'threshold_authorization', 'production', 'physical'})
    need(type(r['schema_version']) is int and r['schema_version'] == 1 and r['purpose'] == protocol()['purpose'])
    validate_selection(r['selection'])
    need(r['source_pins'] == source_pins())
    model = read(HERE.parent / 'asr-runtime/provenance.json')
    need(r['model_bundle_sha256'] == canonical_digest(model['model']))
    need(r['ort_sha256'] == '86e85022fc539963177e478c8e9a8a8219bc3b0d7515bf5297a62986dbc45e7a')
    for key in ('runtime_sha256', 'cxx_sha256'):
        corpus_report.digest(r[key])
    need(r['cxx_sha256'] == read(CORPUS / 'corpus-results.json')['provenance']['cxx_sha256'])
    need(r['overlay_pins'] == read(SDK / 'overlay-expected.json'))
    need(r['rejected_inputs'] == ['empty', 'unaligned', 'nan', 'out_of_range'])
    need(r['threshold_fitting'] == 'NOT_PERFORMED' and r['model_training_overlap'] == 'UNKNOWN')
    need(r['native_calibration'] == 'NOT_ESTABLISHED' and r['threshold_authorization'] == 'NOT_GRANTED')
    need(r['production'] == 'NOT_ENABLED' and r['physical'] == 'NOT_RUN')
    need(type(r['partitions']) is dict and set(r['partitions']) == {'dev', 'test'})
    summary = []
    for split in ('dev', 'test'):
        p = r['partitions'][split]
        need(type(p) is dict and set(p) == {'partition', 'cases_total', 'sources', 'private_counts_sha256'})
        need(p['partition'] == ('CURATOR_DEV' if split == 'dev' else 'CURATOR_TEST'))
        need(type(p['cases_total']) is int and p['cases_total'] == 30)
        corpus_report.digest(p['private_counts_sha256'])
        need(type(p['sources']) is list and len(p['sources']) == 2)
        need([s['source'] for s in p['sources']] == list(SOURCES))
        for source in p['sources']:
            need(type(source) is dict and set(source) == {'source', 'status', 'scope', 'unavailable_reasons', 'origin_case_counts', 'metrics'})
            need(source['scope'] == p['partition'] + '_DIAGNOSTIC_ONLY')
            m = corpus_report.validate_metrics(source['metrics'], 30)
            need(source['status'] == ('NO_AVAILABLE_SCORES' if not m['available'] else 'INCOMPLETE_SCORES' if m['unavailable'] else 'DIAGNOSTIC_ONLY'))
            reasons = source['unavailable_reasons']
            need(type(reasons) is dict and set(reasons) <= REASONS)
            need(all(type(n) is int and 0 < n <= 30 for n in reasons.values()) and sum(reasons.values()) == m['unavailable'])
            origins = source['origin_case_counts']
            need(type(origins) is dict and set(origins) <= {'greedy', 'verification', 'redecode'})
            need(all(type(n) is int and 0 <= n <= m['available'] for n in origins.values()))
            if source['source'] == SOURCES[0]:
                need(origins.get('greedy', 0) == m['available'] and not origins.get('verification', 0) and not origins.get('redecode', 0))
            else:
                need(origins.get('verification', 0) + origins.get('redecode', 0) >= m['available'])
            summary.append(dict(partition=p['partition'], source=source['source'], available=m['available'],
                correct=m['correct'], wer_available=m['wer_available'], brier_available=m['brier_score'],
                accepted_0_85=m['policy_0_85_diagnostic']['accepted'], errors_0_85=m['policy_0_85_diagnostic']['errors']))
    return summary


def export(r, output):
    rows = validate(r)
    need(not output.exists())
    output.mkdir(parents=True)
    (output / 'summary.json').write_text(json.dumps(r, indent=2, allow_nan=False) + '\n')
    keys = list(rows[0])
    table = '<tr>' + ''.join('<th>' + html.escape(k) + '</th>' for k in keys) + '</tr>'
    for row in rows:
        table += '<tr>' + ''.join('<td>' + html.escape(str(row[k])) + '</td>' for k in keys) + '</tr>'
    (output / 'summary.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Fresh split diagnostics</title>'
        '<h1>Fresh curator development/test diagnostics</h1><p>Fresh relative to the prior evaluation, with no shared speakers or normalized utterances. '
        'Two clips per speaker maximum; clips may be correlated. Model training overlap UNKNOWN. '
        'No fitting, calibration, production confidence authorization or physical test.</p>'
        '<p>Error metrics are conditional on available scores. Coverage uses all 30 cases per partition. '
        'The 0.85 threshold was fixed before selection and is descriptive.</p><table border="1">' + table + '</table></html>\n')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=HERE / 'results.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    data = read(args.report)
    print(json.dumps(validate(data), indent=2))
    if args.output:
        export(data, args.output)
