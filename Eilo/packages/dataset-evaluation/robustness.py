"""Paired clean/noisy ASR evidence with reproducible PCM verification; no quality gate."""
import argparse
import hashlib
import html
import json
from functools import lru_cache
from pathlib import Path
from audio import pcm_bytes, read_wav
from baseline import bind
from benchmark import PHYSICAL_GATES, aggregate, validate_manifest
from manifests import canonical_digest, require, safe_path
from noise import NOISE_RECIPE, mix

SNRS = (20, 10, 0)
METRICS = ('wer', 'cer', 'command_accuracy', 'command_balanced_accuracy', 'command_target_accuracy')


def verify_pairs(clean, clean_root, pool, pool_root, noisy, noisy_root):
    for manifest, root in ((clean, clean_root), (pool, pool_root), (noisy, noisy_root)):
        validate_manifest(manifest, root)
    require(clean['kind'] == pool['kind'] == noisy['kind'], 'evidence kinds differ')
    require(pool['dataset'] in ('musan', 'synthetic'), 'MUSAN source pool required')
    require(all(x['task'] == 'vad' and x['vad'] == [] for x in pool['cases']), 'noise-category pool required')
    require(all(x['task'] in ('asr', 'commands') for x in clean['cases']), 'speech references required')
    require(noisy['recipe'] == NOISE_RECIPE, 'mixing recipe changed')
    require(noisy['parent_manifest_sha256'] == canonical_digest(clean), 'clean parent changed')
    require(noisy['noise_manifest_sha256'] == canonical_digest(pool), 'noise pool changed')
    for field in ('dataset', 'release', 'rate'):
        require(clean[field] == noisy[field], 'corpus identity changed')
    require(type(noisy['mix_seed']) is int, 'integer seed required')
    require(len(noisy['cases']) == len(clean['cases']) * len(SNRS), 'incomplete paired SNR suite')
    source = {x['id']: x for x in clean['cases']}
    seen = set()
    @lru_cache(maxsize=2)
    def audio(root, path):
        return read_wav(safe_path(root, path))
    for case in noisy['cases']:
        parent = source.get(case['parent_id'])
        require(parent is not None, 'unknown parent ID')
        snr = case['mix']['target_snr_db']
        require(type(snr) in (int, float) and snr in SNRS, 'unexpected SNR')
        pair = (parent['id'], snr)
        require(pair not in seen, 'duplicate parent/SNR pair')
        seen.add(pair)
        seed = noisy['mix_seed']
        index = int(hashlib.sha256((parent['id'] + ':' + str(seed)).encode()).hexdigest()[:16], 16) % len(pool['cases'])
        selected = pool['cases'][index]
        require(case['noise_id'] == selected['id'], 'noise selection changed')
        samples, recipe = mix(audio(clean_root, parent['path']), audio(pool_root, selected['path']), snr, seed)
        require(case['mix'] == recipe, 'mixing evidence changed')
        require(case['pcm_sha256'] == hashlib.sha256(pcm_bytes(samples)).hexdigest(), 'mixed PCM not reproducible')
        identity = canonical_digest({'clean': parent['sha256'], 'noise': selected['sha256'], 'mix': recipe})[:24]
        require(case['id'] == identity, 'variant identity changed')
        require(case['slice'] == f"{parent['slice']}/snr{snr:g}", 'slice changed')
        for field in ('samples', 'split', 'task', 'reference', 'command'):
            require(case.get(field) == parent.get(field), 'paired reference changed: ' + field)
    require(seen == {(x['id'], snr) for x in clean['cases'] for snr in SNRS}, 'missing paired variant')


def summarize(clean, clean_root, pool, pool_root, noisy, noisy_root, clean_report, noisy_report):
    verify_pairs(clean, clean_root, pool, pool_root, noisy, noisy_root)
    bind(clean, clean_report)
    bind(noisy, noisy_report)
    require(clean['kind'] == 'synthetic' or clean_report['adapter']['kind'] != 'synthetic',
            'synthetic adapter cannot establish public corpus evidence')
    for field in ('normalization', 'scoring', 'adapter'):
        require(clean_report[field] == noisy_report[field], 'evaluation setting changed: ' + field)
    require(clean_report['scoring'] == 'micro-WER-CER-frame20ms-VAD-v2', 'current scoring required')
    require(clean_report['production_readiness'] == noisy_report['production_readiness'] == 'NOT_ENABLED',
            'production gate changed')
    clean_rows = {x['id']: x for x in clean_report['cases']}
    noisy_rows = {x['id']: x for x in noisy_report['cases']}
    groups = [('all', clean['cases'])] + [('slice:' + name, [x for x in clean['cases'] if x['slice'] == name])
                                          for name in sorted({x['slice'] for x in clean['cases']})]
    comparisons = []
    for name, cases in groups:
        ids = {x['id'] for x in cases}
        baseline = aggregate([clean_rows[x['id']] for x in cases])
        for snr in SNRS:
            rows = [noisy_rows[x['id']] for x in noisy['cases']
                    if x['parent_id'] in ids and x['mix']['target_snr_db'] == snr]
            measured = aggregate(rows)
            delta = {key: measured[key] - baseline[key] for key in METRICS
                     if key in baseline and baseline[key] is not None and measured.get(key) is not None}
            comparisons.append({'group': name, 'snr_db': snr, 'clean': baseline,
                                'noisy': measured, 'absolute_metric_delta': delta})
    return {'schema_version': 1, 'status': 'MEASURED_DIAGNOSTIC', 'kind': clean['kind'],
            'dataset': clean['dataset'], 'release': clean['release'],
            'quality_acceptance': 'NOT_ASSESSED',
            'annotation_caveat': 'MUSAN category pool is not reviewed time-aligned VAD truth',
            'timing_scope': 'Desktop adapter execution includes startup and provenance checks; not device latency',
            'clean_manifest_sha256': canonical_digest(clean), 'noisy_manifest_sha256': canonical_digest(noisy),
            'noise_manifest_sha256': canonical_digest(pool), 'clean_report_sha256': canonical_digest(clean_report),
            'noisy_report_sha256': canonical_digest(noisy_report),
            'adapter': {key: clean_report['adapter'][key] for key in
                        ('name', 'kind', 'binary_sha256', 'model_sha256', 'config_sha256')},
            'recipe': NOISE_RECIPE, 'seed': noisy['mix_seed'], 'comparisons': comparisons,
            'physical_gates': {x: 'NOT_RUN' for x in PHYSICAL_GATES}, 'production_readiness': 'NOT_ENABLED'}


def export(value, output):
    output = Path(output)
    require(not output.exists(), 'refusing to overwrite paired evidence')
    output.mkdir(parents=True)
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
    (output / 'summary.json').write_text(payload + '\n')
    rows = ''
    for row in value['comparisons']:
        if row['group'] != 'all':
            continue
        cells = [row['snr_db'], row['clean']['count']]
        cells += [f"{100 * row[side][metric]:.2f}%" for metric in ('wer', 'cer') for side in ('clean', 'noisy')]
        rows += '<tr>' + ''.join('<td>' + html.escape(str(x)) + '</td>' for x in cells) + '</tr>'
    table = '<table><caption>Paired clips and micro error rates</caption><thead><tr><th>SNR (dB)</th><th>Pairs</th><th>Clean WER</th><th>Noisy WER</th><th>Clean CER</th><th>Noisy CER</th></tr></thead><tbody>' + rows + '</tbody></table>'
    document = '<!doctype html><html lang="en"><meta charset="utf-8">' \
        '<meta name="viewport" content="width=device-width,initial-scale=1">' \
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">' \
        '<title>Paired ASR noise evidence</title><style>body{font:16px system-ui;max-width:960px;margin:2rem auto;padding:1rem}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{border-collapse:collapse}th,td{text-align:left;border:1px solid #ccc;padding:.5rem}</style>' \
        '<h1>Paired ASR noise evidence</h1><p>Measured desktop diagnostic. Quality acceptance NOT_ASSESSED. ' \
        'All physical gates NOT_RUN; production NOT_ENABLED.</p>' + table + '<h2>Provenance and slices</h2><pre>' + html.escape(payload) + '</pre></html>'
    (output / 'summary.html').write_text(document)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('clean', 'noise', 'noisy', 'clean-report', 'noisy-report', 'output'):
        parser.add_argument('--' + field, required=True, type=Path)
    args = parser.parse_args()
    def read(path):
        require(path.stat().st_size <= 20 * 1024 * 1024, 'oversized evidence input')
        return json.loads(path.read_text())
    value = summarize(read(args.clean), args.clean.parent, read(args.noise), args.noise.parent,
                      read(args.noisy), args.noisy.parent, read(args.clean_report), read(args.noisy_report))
    export(value, args.output)
