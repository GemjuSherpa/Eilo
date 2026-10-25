"""Freeze fresh bounded curator dev/test cohorts from the approved local archive."""
import argparse
from collections import Counter
import csv
import io
from pathlib import Path, PurePosixPath
import tarfile
import json

from shared import DATA, HERE, need, sha, read, protocol, source_pins, canonical_digest, verify_receipt, opaque, normalize
from extract_subset import member_path, read_member
from preprocess import freeze
from benchmark import validate_manifest


def choose(tables, prior, policy):
    need(set(tables) == {'train', 'dev', 'test'})
    speaker_sets = {}
    for split, rows in tables.items():
        need(rows and len(rows) <= 100000)
        need(all(type(r) is dict and all(type(r.get(k)) is str and r[k] for k in ('client_id', 'sentence', 'path')) for r in rows))
        need(len({r['path'] for r in rows}) == len(rows))
        need(all(PurePosixPath(r['path']).name == r['path'] and r['path'].endswith('.mp3') and '\\' not in r['path'] for r in rows))
        speaker_sets[split] = {opaque(r['client_id']) for r in rows}
    need(not speaker_sets['dev'] & speaker_sets['test'])
    need(not speaker_sets['train'] & (speaker_sets['dev'] | speaker_sets['test']))
    prior_speakers = {c['speaker'] for c in prior['cases']}
    prior_text = {normalize(c['reference']) for c in prior['cases']}
    need(prior_speakers and prior_text and all(c['split'] == 'test' for c in prior['cases']))
    blocked_speakers, blocked_text = set(prior_speakers), set(prior_text)
    selected = {}
    for split, count in (('dev', policy['development_count']), ('test', policy['test_count'])):
        rows = sorted(tables[split], key=lambda r: opaque(str(policy['seed']) + ':' + split + ':' + r['path']))
        used = Counter()
        chosen = []
        for round_number in range(1, policy['max_clips_per_speaker'] + 1):
            for row in rows:
                speaker, text = opaque(row['client_id']), normalize(row['sentence'])
                if len(chosen) == count:
                    break
                if speaker in blocked_speakers or text in blocked_text or used[speaker] >= round_number:
                    continue
                need(text)
                chosen.append(row)
                used[speaker] += 1
                blocked_text.add(text)
        need(len(chosen) == count)
        selected[split] = chosen
        blocked_speakers.update(used)
    return selected


def prepare(archive_path, receipt, prior_path, output, decoder):
    policy = protocol()
    need(not output.exists())
    verify_receipt(receipt, archive_path)
    need(receipt['dataset'] == 'common_voice' and receipt['permission'].startswith('APPROVED_BY_USER'))
    prior = read(prior_path)
    validate_manifest(prior, prior_path.parent)
    need(prior['receipt'] == receipt and prior['dataset'] == 'common_voice')
    pins = source_pins()
    tables, names, prefix = {}, set(), None
    with tarfile.open(archive_path, 'r|*') as archive:
        for member in archive:
            name = member_path(member)
            need(name not in names)
            names.add(name)
            basename = PurePosixPath(name).name
            if member.isfile() and basename in ('train.tsv', 'dev.tsv', 'test.tsv'):
                split = basename[:-4]
                parent = str(PurePosixPath(name).parent)
                need(split not in tables and (prefix is None or prefix == parent))
                prefix = parent
                tables[split] = list(csv.DictReader(io.StringIO(read_member(archive, member).decode('utf-8')), delimiter='\t'))
    selected = choose(tables, prior, policy)
    prefix = '' if prefix == '.' else prefix + '/'
    wanted = {prefix + 'clips/' + r['path'] for rows in selected.values() for r in rows}
    need(wanted <= names and len(wanted) == 60)
    output.mkdir(parents=True)
    raw = output / 'selected-private'
    raw.mkdir()
    with tarfile.open(archive_path, 'r|*') as archive:
        for member in archive:
            name = member_path(member)
            if name in wanted:
                target = raw / 'clips' / PurePosixPath(name).name
                target.parent.mkdir(exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(read_member(archive, member))
    for split, rows in selected.items():
        with (raw / (split + '.tsv')).open('x', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=('client_id', 'sentence', 'path'), delimiter='\t', extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        freeze('common_voice', raw, output / split, receipt['version'], receipt,
               'validation' if split == 'dev' else 'test', len(rows), policy['seed'],
               decoder, prior['decoder_sha256'], 'afconvert')
    need(pins == source_pins())
    manifests = {split: read(output / split / 'manifest.json') for split in ('dev', 'test')}
    evidence = dict(schema_version=1, purpose=policy['purpose'], protocol_sha256=sha(HERE / 'protocol.json'),
        prior_manifest_sha256=canonical_digest(prior), receipt_sha256=canonical_digest(receipt),
        source_pins=pins, partitions={split: dict(cases=len(m['cases']), speakers=len({c['speaker'] for c in m['cases']}),
            manifest_sha256=canonical_digest(m)) for split, m in manifests.items()},
        prior_speaker_overlap=0, prior_utterance_overlap=0, cross_speaker_overlap=0, cross_utterance_overlap=0,
        model_training_overlap='UNKNOWN', physical='NOT_RUN', production='NOT_ENABLED')
    (output / 'selection.json').write_text(json.dumps(evidence, indent=2) + '\n')
    from evaluate import verify_cohorts
    verify_cohorts(output, prior_path)
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('archive', 'receipt', 'prior', 'output', 'decoder'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    prepare(args.archive, read(args.receipt), args.prior, args.output, args.decoder)
    print('Fresh bounded dev/test cohorts frozen locally; no content exported.')
