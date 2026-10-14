"""Bounded offline adapter runner and corpus-bound ASR/VAD/command scoring."""
import argparse
import hashlib
import wave
from collections import Counter
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import unicodedata
from audio import RATE, read_wav, pcm_bytes
from manifests import canonical_digest, require, safe_path, sha256, validate_receipt

PHYSICAL_GATES = ('capture', 'interruption', 'endurance', 'standby', 'screen_off', 'device_latency')


def normalize(text):
    require(isinstance(text, str) and len(text.encode()) <= 4096, 'invalid transcript')
    return ' '.join(''.join(c if c.isalnum() or c.isspace() else ' '
                            for c in unicodedata.normalize('NFKC', text).casefold()).split())


def distance(left, right):
    previous = list(range(len(right) + 1))
    for i, x in enumerate(left, 1):
        current = [i]
        for j, y in enumerate(right, 1):
            current.append(min(previous[j] + 1, current[-1] + 1, previous[j - 1] + (x != y)))
        previous = current
    return previous[-1]


def number(value, minimum=0):
    require(type(value) in (int, float) and math.isfinite(value) and value >= minimum,
            'invalid finite nonnegative number')
    return value


def intervals(value, duration):
    require(isinstance(value, list) and len(value) <= 3000, 'invalid VAD intervals')
    end = 0
    for pair in value:
        require(isinstance(pair, list) and len(pair) == 2, 'invalid interval')
        start, stop = map(number, pair)
        require(end <= start < stop <= duration, 'overlap/unsorted/out-of-bounds VAD interval')
        end = stop
    return value


def vad_counts(reference, predicted, duration):
    intervals(reference, duration)
    intervals(predicted, duration)
    counts = Counter(tp=0, fp=0, fn=0, tn=0)
    # 20ms frame midpoints; the last partial frame counts once.
    for i in range(math.ceil(duration * 50)):
        at = min((i + 0.5) / 50, duration - 1e-9)
        truth = any(a <= at < b for a, b in reference)
        found = any(a <= at < b for a, b in predicted)
        counts['tp' if truth and found else 'fn' if truth else 'fp' if found else 'tn'] += 1
    return dict(counts)


def validate_manifest(manifest, root):
    require(manifest['schema_version'] == 1 and manifest['rate'] == RATE, 'invalid corpus schema/rate')
    require(manifest['kind'] in ('public_corpus', 'synthetic'), 'unknown evidence kind')
    require(0 < len(manifest['cases']) <= 10000, 'invalid corpus count')
    if manifest['kind'] == 'public_corpus':
        validate_receipt(manifest['receipt'])
        require(manifest['receipt']['dataset'] == manifest['dataset']
                and manifest['receipt']['version'] == manifest['release'], 'corpus receipt mismatch')
        require(canonical_digest(manifest['receipt']) == manifest['receipt_sha256'], 'receipt changed')
    ids = set()
    for case in manifest['cases']:
        require(re.fullmatch('[0-9a-f]{24}', case['id']) and case['id'] not in ids, 'invalid/duplicate ID')
        ids.add(case['id'])
        require(case['task'] in ('asr', 'vad', 'commands'), 'invalid task')
        require(case['split'] in ('test', 'validation'), 'training sample prohibited')
        path = safe_path(root, case['path'])
        require(sha256(path) == case['sha256'], 'frozen audio changed')
        require(type(case['samples']) is int and 0 < case['samples'] <= RATE * 30, 'invalid sample count')
        with wave.open(str(path), 'rb') as stream:
            require((stream.getnchannels(), stream.getsampwidth(), stream.getframerate())
                    == (1, 2, RATE), 'corpus WAV must already be normalized')
        samples = read_wav(path)
        require(len(samples) == case['samples'], 'sample count changed')
        if 'pcm_sha256' in case:
            require(hashlib.sha256(pcm_bytes(samples)).hexdigest() == case['pcm_sha256'], 'PCM changed')
        require(isinstance(case['slice'], str) and 0 < len(case['slice']) <= 120, 'invalid slice')
        if case['task'] in ('asr', 'commands'):
            require(normalize(case['reference']), 'empty ASR reference')
        if case['task'] == 'vad':
            intervals(case['vad'], case['samples'] / RATE)
    return manifest


def provenance(value):
    require(value['kind'] in ('native', 'external', 'synthetic'), 'invalid adapter kind')
    require(isinstance(value['name'], str) and 0 < len(value['name']) <= 120, 'adapter name required')
    for key in ('binary_sha256', 'model_sha256', 'config_sha256'):
        require(re.fullmatch('[0-9a-f]{64}', value[key]), 'adapter/model/config hash required')
    return value


def predictions(manifest, value):
    require(value['schema_version'] == 1, 'invalid predictions version')
    require(value['manifest_sha256'] == canonical_digest(manifest), 'predictions belong to another corpus')
    provenance(value['adapter'])
    require(len(value['cases']) == len(manifest['cases']), 'missing/extra predictions')
    result = {}
    for case in value['cases']:
        require(case['id'] not in result, 'duplicate predictions')
        number(case['seconds'])
        result[case['id']] = case
    require(set(result) == {x['id'] for x in manifest['cases']}, 'prediction ID mismatch')
    return result


def score_case(case, prediction):
    audio_seconds = case['samples'] / RATE
    result = {'id': case['id'], 'slice': case['slice'], 'task': case['task'],
              'audio_seconds': audio_seconds, 'seconds': number(prediction['seconds'])}
    if case['task'] in ('asr', 'commands'):
        reference = normalize(case['reference'])
        hypothesis = normalize(prediction['transcript'])
        result.update({'word_errors': distance(reference.split(), hypothesis.split()),
                       'reference_words': len(reference.split()),
                       'character_errors': distance(reference, hypothesis),
                       'reference_characters': len(reference)})
        if case['task'] == 'commands':
            require(prediction['command'] in {'yes', 'no', 'up', 'down', 'left', 'right', 'on', 'off',
                                             'stop', 'go', 'unknown', 'silence'}, 'invalid command label')
            result.update({'correct': int(case['command'] == prediction['command']),
                           'confusion': [case['command'], prediction['command']]})
    else:
        result['vad'] = vad_counts(case['vad'], prediction['vad'], audio_seconds)
    return result


def aggregate(cases):
    result = {'count': len(cases)}
    asr = [x for x in cases if 'word_errors' in x]
    if asr:
        for field in ('word_errors', 'reference_words', 'character_errors', 'reference_characters'):
            result[field] = sum(x[field] for x in asr)
        result['wer'] = result['word_errors'] / result['reference_words']
        result['cer'] = result['character_errors'] / result['reference_characters']
    commands = [x for x in cases if 'correct' in x]
    if commands:
        result['command_accuracy'] = sum(x['correct'] for x in commands) / len(commands)
        result['confusion'] = dict(sorted(Counter(' -> '.join(x['confusion']) for x in commands).items()))
        by_label = {label: [x for x in commands if x['confusion'][0] == label]
                    for label in sorted({x['confusion'][0] for x in commands})}
        result['command_accuracy_by_label'] = {label: sum(x['correct'] for x in items) / len(items)
                                               for label, items in by_label.items()}
        result['command_balanced_accuracy'] = sum(result['command_accuracy_by_label'].values()) / len(by_label)
        targets = [x for x in commands if x['confusion'][0] not in ('unknown', 'silence')]
        result['command_target_count'] = len(targets)
        result['command_target_accuracy'] = sum(x['correct'] for x in targets) / len(targets) if targets else None
    vad = [x for x in cases if 'vad' in x]
    if vad:
        totals = {key: sum(x['vad'][key] for x in vad) for key in ('tp', 'fp', 'fn', 'tn')}
        result['vad'] = totals
        result['vad_f1'] = 2 * totals['tp'] / (2 * totals['tp'] + totals['fp'] + totals['fn']) if totals['tp'] + totals['fp'] + totals['fn'] else None
        result['vad_false_positive_rate'] = totals['fp'] / (totals['fp'] + totals['tn']) if totals['fp'] + totals['tn'] else None
        result['vad_miss_rate'] = totals['fn'] / (totals['tp'] + totals['fn']) if totals['tp'] + totals['fn'] else None
    if cases:
        result['rtf'] = sum(x['seconds'] for x in cases) / sum(x['audio_seconds'] for x in cases)
    return result


def report(manifest, value=None):
    base = {'schema_version': 1, 'manifest_sha256': canonical_digest(manifest),
            'dataset': manifest['dataset'], 'release': manifest['release'], 'kind': manifest['kind'],
            'physical_gates': {x: 'NOT_RUN' for x in PHYSICAL_GATES},
            'production_readiness': 'NOT_ENABLED', 'normalization': 'nfkc-casefold-alnum-v1',
            'scoring': 'micro-WER-CER-frame20ms-VAD-v1'}
    if value is None:
        return {**base, 'status': 'NOT_RUN', 'reason': 'No evaluated adapter predictions',
                'cases': [], 'metrics': {'count': 0}, 'slices': {}}
    mapping = predictions(manifest, value)
    require(manifest['kind'] == 'synthetic' or value['adapter']['kind'] != 'synthetic',
            'synthetic adapter cannot establish public corpus results')
    cases = [score_case(case, mapping[case['id']]) for case in manifest['cases']]
    slices = {name: aggregate([x for x in cases if x['slice'] == name])
              for name in sorted({x['slice'] for x in cases})}
    return {**base, 'status': 'MEASURED', 'adapter': value['adapter'], 'cases': cases,
            'metrics': aggregate(cases), 'slices': slices}


def run_adapter(manifest, root, executable, metadata, timeout=120):
    validate_manifest(manifest, root)
    provenance(metadata)
    require(metadata['binary_sha256'] == sha256(executable), 'adapter binary checksum changed')
    outputs = []
    for case in manifest['cases']:
        with tempfile.TemporaryDirectory() as temp:
            request, response = Path(temp) / 'request.json', Path(temp) / 'response.json'
            request.write_text(json.dumps({'schema_version': 1, 'id': case['id'], 'task': case['task'],
                                           'audio': str(safe_path(root, case['path'])), 'rate': RATE}))
            start = time.monotonic()
            # Explicit local adapter contract: executable request.json response.json.
            # Runner never passes truth labels/transcripts to the adapter.
            environment = os.environ.copy()
            environment['EILO_DATA_ADAPTER_CONFIG_SHA256'] = metadata['config_sha256']
            environment['EILO_DATA_ADAPTER_MODEL_SHA256'] = metadata['model_sha256']
            subprocess.run([str(Path(executable).resolve()), str(request), str(response)],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=timeout, env=environment)
            elapsed = time.monotonic() - start
            require(response.stat().st_size <= 65536, 'unbounded adapter response')
            output = json.loads(response.read_text())
            require(output['id'] == case['id'], 'adapter returned wrong ID')
            output['seconds'] = elapsed
            score_case(case, output)
            outputs.append(output)
    return {'schema_version': 1, 'manifest_sha256': canonical_digest(manifest),
            'adapter': metadata, 'cases': outputs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--predictions', type=Path)
    parser.add_argument('--adapter', type=Path)
    parser.add_argument('--adapter-metadata', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = validate_manifest(json.loads(args.manifest.read_text()), args.manifest.parent)
    require(not (args.adapter and args.predictions), 'choose adapter or predictions')
    value = json.loads(args.predictions.read_text()) if args.predictions else None
    if args.adapter:
        require(args.adapter_metadata, 'adapter metadata required')
        value = run_adapter(manifest, args.manifest.parent, args.adapter,
                            json.loads(args.adapter_metadata.read_text()))
    args.output.write_text(json.dumps(report(manifest, value), indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
