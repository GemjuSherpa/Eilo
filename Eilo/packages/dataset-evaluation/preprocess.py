"""Freeze a bounded held-out index of approved local corpus files."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from audio import RATE, RECIPE, decode_mp3, read_wav, write_wav
from manifests import canonical_digest, require, safe_path, sha256

COMMANDS = {'yes', 'no', 'up', 'down', 'left', 'right', 'on', 'off', 'stop', 'go'}


def opaque(text):
    return hashlib.sha256(text.encode()).hexdigest()


def candidates(dataset, root, split):
    root = Path(root)
    require(split in ('test', 'validation'), 'evaluation must be held out')
    if dataset == 'common_voice':
        name = 'test.tsv' if split == 'test' else 'dev.tsv'
        with safe_path(root, name).open(newline='', encoding='utf-8') as stream:
            for row in csv.DictReader(stream, delimiter='\t'):
                require(row.get('sentence') and row.get('client_id'), 'missing CV reference/speaker')
                yield {'path': 'clips/' + row['path'], 'reference': row['sentence'],
                       'speaker': opaque(row['client_id']), 'task': 'asr'}
    elif dataset == 'speech_commands':
        name = 'testing_list.txt' if split == 'test' else 'validation_list.txt'
        for path in safe_path(root, name).read_text().splitlines():
            if not path:
                continue
            label = Path(path).parts[0]
            require(len(Path(path).parts) == 2, 'invalid command path')
            yield {'path': path, 'reference': label, 'command': label if label in COMMANDS else 'unknown',
                   'speaker': opaque(Path(path).name.split('_nohash_')[0]), 'task': 'commands'}
    elif dataset == 'musan':
        # Noise-only negatives; speech/music have no time-aligned speech annotations.
        for path in sorted((root / 'noise').rglob('*.wav')):
            yield {'path': path.relative_to(root).as_posix(), 'task': 'vad', 'vad': [],
                   'speaker': opaque(path.relative_to(root).as_posix()), 'slice': 'noise_only'}
    else:
        raise ValueError('unknown corpus')


def freeze(dataset, root, output, release, receipt, split='test', limit=100, seed=0,
           decoder=None, decoder_sha256=None):
    require(type(limit) is int and 1 <= limit <= 10000, 'invalid sample limit')
    require(type(seed) is int, 'invalid seed')
    require(release != 'UNSELECTED' and receipt['version'] == release and receipt['dataset'] == dataset,
            'release/receipt mismatch')
    require(receipt['permission'].startswith('APPROVED_BY_USER'), 'corpus-use approval required')
    require(receipt['checksum_status'] in ('LOCAL_OBSERVED', 'PUBLISHER_VERIFIED'), 'receipt required')
    require(not Path(output).exists(), 'output already exists; preserve frozen corpus')
    rows = sorted(candidates(dataset, root, split), key=lambda x: opaque(str(seed) + ':' + x['path']))
    require(rows, 'empty held-out corpus')
    seen = set()
    selected = []
    for row in rows:
        require(row['path'] not in seen, 'duplicate sample path')
        seen.add(row['path'])
        if len(selected) < limit:
            selected.append(row)
    Path(output).mkdir(parents=True)
    cases = []
    for row in selected:
        source = safe_path(root, row['path'])
        sample_id = opaque(dataset + ':' + release + ':' + row['path'])[:24]
        if source.suffix.lower() == '.mp3':
            require(decoder and decoder_sha256, 'approved pinned MP3 decoder required')
            samples = decode_mp3(source, decoder, decoder_sha256)
        else:
            samples = read_wav(source, max_seconds=600 if dataset == 'musan' else 30)
        if dataset == 'musan':
            samples = samples[:RATE * 30]
        normalized = Path(output) / (sample_id + '.wav')
        pcm_sha = write_wav(normalized, samples)
        case = {k: v for k, v in row.items() if k != 'path'}
        case.update({'id': sample_id, 'path': normalized.name, 'source_sha256': sha256(source),
                     'sha256': sha256(normalized), 'pcm_sha256': pcm_sha, 'samples': len(samples),
                     'split': split, 'slice': row.get('slice', dataset)})
        cases.append(case)
    manifest = {'schema_version': 1, 'dataset': dataset, 'release': release,
                'receipt': receipt, 'receipt_sha256': canonical_digest(receipt),
                'recipe': RECIPE, 'decoder_sha256': decoder_sha256, 'rate': RATE, 'seed': seed,
                'kind': 'public_corpus', 'cases': cases}
    (Path(output) / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True, choices=['common_voice', 'musan', 'speech_commands'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--split', choices=['test', 'validation'], default='test')
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--decoder', type=Path)
    parser.add_argument('--decoder-sha256')
    args = parser.parse_args()
    record = json.loads(args.receipt.read_text())
    manifest = freeze(args.dataset, args.root, args.output, record['version'], record,
                      args.split, args.limit, args.seed, args.decoder, args.decoder_sha256)
    print(f"Frozen {len(manifest['cases'])} held-out clips; no physical evidence.")


if __name__ == '__main__':
    main()
