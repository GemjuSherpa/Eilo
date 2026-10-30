"""Freeze the private 600-utterance confidence-audit cohort from approved local data."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
EILO = HERE.parents[1]
PACKAGES = EILO / 'packages'
sys.path.insert(0, str(PACKAGES / 'dataset-evaluation'))
from benchmark import normalize, validate_manifest
from extract_subset import member_path, read_member
from manifests import canonical_digest, require, sha256, verify_receipt
from preprocess import freeze, opaque


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def select_rows(rows, prior_speakers, prior_texts, seed=20261030):
    """Return deterministic phase rows while keeping IDs/texts disjoint globally."""
    require(type(seed) is int and seed == 20261030, 'protocol seed changed')
    require(type(rows) is list and rows, 'empty train table')
    prior_texts = {normalize(text) for text in prior_texts}
    seen_paths = set()
    candidates = []
    for row in rows:
        require(type(row) is dict and all(type(row.get(key)) is str and row[key]
                                         for key in ('client_id', 'sentence', 'path')),
                'invalid Common Voice row')
        path = PurePosixPath(row['path'])
        require(not path.is_absolute() and len(path.parts) == 1 and path.suffix == '.mp3'
                and '\\' not in row['path'], 'unsafe clip path')
        require(row['path'] not in seen_paths, 'duplicate clip path')
        seen_paths.add(row['path'])
        speaker = opaque(row['client_id'])
        text = normalize(row['sentence'])
        if speaker in prior_speakers or not text or text in prior_texts:
            continue
        candidates.append((digest(f'{seed}:train:{row["path"]}'), row, speaker, text))
    candidates.sort(key=lambda item: (item[0], item[1]['path']))
    speakers, texts = set(prior_speakers), set(prior_texts)
    selected = []
    for _, row, speaker, text in candidates:
        if speaker in speakers or text in texts:
            continue
        selected.append(row)
        speakers.add(speaker)
        texts.add(text)
        if len(selected) == 600:
            break
    require(len(selected) == 600, 'fewer than 600 disjoint eligible cases; protocol must not be weakened')
    return {
        'development': selected[:200],
        'validation': selected[200:400],
        'audit': selected[400:600],
    }


def prior_exclusions(paths, receipt):
    require(len(paths) == 4, 'all four prior evaluated Common Voice manifests are required')
    speakers, texts, source_hashes, pcm_hashes = set(), set(), set(), set()
    manifests = []
    total = 0
    for path in paths:
        manifest = json.loads(Path(path).read_text(encoding='utf-8'))
        validate_manifest(manifest, Path(path).parent)
        require(manifest['dataset'] == 'common_voice' and manifest['receipt'] == receipt,
                'prior manifest is not from the approved Common Voice release')
        for case in manifest['cases']:
            require(case['task'] == 'asr', 'non-ASR exclusion manifest')
            speakers.add(case['speaker'])
            texts.add(normalize(case['reference']))
            source_hashes.add(case['source_sha256'])
            pcm_hashes.add(case['pcm_sha256'])
            total += 1
        manifests.append(canonical_digest(manifest))
    require(total == 120, 'prior evaluated cohort inventory changed; review required')
    return speakers, texts, source_hashes, pcm_hashes, manifests


def pins():
    files = [HERE / name for name in ('audit-v2-protocol.json', 'audit_v2.py', 'select_audit_v2.py')]
    files += [PACKAGES / 'dataset-evaluation' / name for name in
              ('audio.py', 'benchmark.py', 'extract_subset.py', 'manifests.py', 'preprocess.py')]
    return {str(path.relative_to(EILO)): sha256(path) for path in files}


def prepare(archive, receipt_path, prior_paths, decoder, output=None):
    archive, receipt_path, decoder = map(Path, (archive, receipt_path, decoder))
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    verify_receipt(receipt, archive)
    require(receipt['dataset'] == 'common_voice' and receipt['version'] ==
            '26.0-2026-06-12-en-AU-MDC-2026-07-20', 'approved Common Voice release changed')
    require(receipt['permission'].startswith('APPROVED_BY_USER_'), 'dataset approval missing')
    from manifests import sha256 as file_sha256
    decoder_hash = file_sha256(decoder)
    prior_speakers, prior_texts, prior_sources, prior_pcm, prior_hashes = prior_exclusions(prior_paths, receipt)

    archive_names = set()
    tables = {}
    prefix = None
    with tarfile.open(archive, 'r:') as source:
        for member in source.getmembers():
            name = member_path(member)
            require(name not in archive_names, 'duplicate archive member')
            archive_names.add(name)
            if member.isfile() and PurePosixPath(name).name in ('train.tsv', 'dev.tsv', 'test.tsv'):
                split = PurePosixPath(name).name[:-4]
                parent = str(PurePosixPath(name).parent)
                require(split not in tables and (prefix is None or prefix == parent),
                        'Common Voice table layout changed')
                prefix = parent
                tables[split] = list(csv.DictReader(io.StringIO(read_member(source, member).decode('utf-8')),
                                                   delimiter='\t'))
    require(set(tables) == {'train', 'dev', 'test'}, 'official split metadata incomplete')
    official_ids = {split: {opaque(row['client_id']) for row in rows} for split, rows in tables.items()}
    require(not (official_ids['train'] & official_ids['dev'] or
                 official_ids['train'] & official_ids['test'] or
                 official_ids['dev'] & official_ids['test']), 'official Common Voice IDs overlap')
    selected = select_rows(tables['train'], prior_speakers, prior_texts)

    output = Path(output) if output else EILO / '.local' / 'asr-calibration-audit-v2'
    require(not output.exists() and not output.is_symlink(), 'preserve existing audit cohort')
    output.parent.mkdir(parents=True, exist_ok=True)
    before = pins()
    with tempfile.TemporaryDirectory(prefix='confidence-audit-v2-', dir=output.parent) as scratch:
        root = Path(scratch)
        source_prefix = '' if prefix == '.' else prefix + '/'
        wanted = {source_prefix + 'clips/' + row['path'] for group in selected.values() for row in group}
        require(len(wanted) == 600 and wanted <= archive_names, 'selected clip inventory incomplete')
        raw_roots = {}
        for phase, rows in selected.items():
            raw = root / 'private-source' / phase
            (raw / 'clips').mkdir(parents=True)
            tsv = 'dev.tsv' if phase == 'validation' else 'test.tsv'
            with (raw / tsv).open('x', newline='', encoding='utf-8') as stream:
                writer = csv.DictWriter(stream, fieldnames=('client_id', 'sentence', 'path'),
                                        delimiter='\t', extrasaction='ignore')
                writer.writeheader()
                writer.writerows(rows)
            raw_roots[phase] = raw
        with tarfile.open(archive, 'r:') as source:
            for member in source.getmembers():
                name = member_path(member)
                if name not in wanted:
                    continue
                raw_relative = name.removeprefix(source_prefix + 'clips/')
                phase = next(key for key, rows in selected.items()
                             if any(row['path'] == raw_relative for row in rows))
                destination = raw_roots[phase] / 'clips' / raw_relative
                with destination.open('xb') as stream:
                    stream.write(read_member(source, member))
        manifests = {}
        for phase, raw in raw_roots.items():
            split = 'validation' if phase == 'validation' else 'test'
            manifest = freeze('common_voice', raw, root / phase, receipt['version'], receipt,
                              split, 200, 20261030, decoder, decoder_hash, 'afconvert')
            manifests[phase] = manifest
        # Reject exact prior-source or deterministic-PCM repeats even if metadata differs.
        seen_sources, seen_pcm, seen_speakers, seen_texts = set(prior_sources), set(prior_pcm), set(prior_speakers), set(prior_texts)
        for phase in ('development', 'validation', 'audit'):
            manifest = manifests[phase]
            phase_speakers, phase_texts = set(), set()
            for case in manifest['cases']:
                require(case['source_sha256'] not in seen_sources and case['pcm_sha256'] not in seen_pcm,
                        'selected audio overlaps previously evaluated bytes')
                require(case['speaker'] not in seen_speakers and normalize(case['reference']) not in seen_texts,
                        'selected phase overlaps an earlier speaker ID or normalized utterance')
                seen_sources.add(case['source_sha256']); seen_pcm.add(case['pcm_sha256'])
                seen_speakers.add(case['speaker']); seen_texts.add(normalize(case['reference']))
                phase_speakers.add(case['speaker']); phase_texts.add(normalize(case['reference']))
            require(len(phase_speakers) == len(phase_texts) == 200, 'phase independence failed')
        inventory = {
            'schema_version': 1,
            'purpose': 'PRIVATE_FROZEN_CONFIDENCE_AUDIT_COHORT',
            'protocol_sha256': sha256(HERE / 'audit-v2-protocol.json'),
            'source_pins': before,
            'archive_sha256': receipt['sha256'],
            'receipt_sha256': canonical_digest(receipt),
            'prior_manifest_sha256': prior_hashes,
            'excluded_prior_cases': 120,
            'phases': {phase: {
                'cases': len(manifest['cases']),
                'manifest_sha256': canonical_digest(manifest),
                'provided_client_ids': len({case['speaker'] for case in manifest['cases']}),
                'normalized_utterances': len({normalize(case['reference']) for case in manifest['cases']}),
            } for phase, manifest in manifests.items()},
            'cross_phase_id_overlap': 0,
            'cross_phase_text_overlap': 0,
            'prior_id_text_source_pcm_overlap': 0,
            'model_training_overlap': 'UNKNOWN',
            'frozen_before_inference': True,
            'inference': 'NOT_RUN',
            'native_calibration': 'NOT_ESTABLISHED',
            'threshold_authorization': 'NOT_GRANTED',
            'production': 'NOT_ENABLED',
            'physical': 'NOT_RUN',
        }
        (root / 'selection-private.json').write_text(json.dumps(inventory, indent=2, sort_keys=True) + '\n')
        require(before == pins(), 'selection code or preprocessing changed during freeze')
        os.replace(root, output)
    return inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--prior-manifest', action='append', type=Path, required=True,
                        help='repeat exactly four times, one for each previously evaluated cohort')
    parser.add_argument('--decoder', type=Path, required=True,
                        help='existing system afconvert binary; no installation or download')
    args = parser.parse_args()
    result = prepare(args.archive, args.receipt, args.prior_manifest, args.decoder)
    print(json.dumps({
        'purpose': result['purpose'],
        'phases': {key: {'cases': row['cases'], 'manifest_sha256': row['manifest_sha256']}
                   for key, row in result['phases'].items()},
        'frozen_before_inference': result['frozen_before_inference'],
        'inference': result['inference'],
    }, indent=2))


if __name__ == '__main__':
    main()
