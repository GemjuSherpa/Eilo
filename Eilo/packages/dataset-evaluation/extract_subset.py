"""Bounded selective extraction of an approved, checksum-verified local archive."""
import argparse
import csv
import io
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
from manifests import require, verify_receipt


def member_path(member):
    path = PurePosixPath(member.name)
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in member.name,
            'unsafe archive path')
    require(member.isfile() or member.isdir(), 'archive links/devices prohibited')
    require(0 <= member.size <= 64 * 1024 * 1024, 'oversized archive member')
    return path.as_posix().removeprefix('./')


def read_member(archive, member):
    require(member.isfile(), 'file required')
    stream = archive.extractfile(member)
    require(stream is not None, 'missing member stream')
    content = stream.read(member.size + 1)
    require(len(content) == member.size, 'truncated archive member')
    return content


def extract(archive_path, receipt, output, limit=100, seed=0):
    require(1 <= limit <= 1000, 'invalid extraction limit')
    require(receipt['permission'].startswith('APPROVED_BY_USER'), 'corpus-use approval required')
    verify_receipt(receipt, archive_path)
    require(receipt['dataset'] in ('speech_commands', 'musan', 'common_voice'), 'unsupported extraction corpus')
    require(not Path(output).exists(), 'preserve existing extraction')
    metadata, names = {}, set()
    with tarfile.open(archive_path, 'r|*') as archive:
        for member in archive:
            name = member_path(member)
            require(name not in names, 'duplicate archive path')
            names.add(name)
            if member.isfile() and (name.endswith(('LICENSE', 'LICENSE.txt', 'README.md', 'README',
                                                  'ANNOTATIONS', 'testing_list.txt', 'validation_list.txt',
                                                  'test.tsv', 'dev.tsv', 'train.tsv', 'stats.md'))):
                metadata[name] = read_member(archive, member)
    if receipt['dataset'] == 'speech_commands':
        require('LICENSE' in metadata and b'Attribution 4.0 International' in metadata['LICENSE'], 'license mismatch')
        require('testing_list.txt' in metadata, 'official test list missing')
        candidates = metadata['testing_list.txt'].decode().splitlines()
    elif receipt['dataset'] == 'common_voice':
        tests = [name for name in metadata if name == 'test.tsv' or name.endswith('/test.tsv')]
        require(len(tests) == 1, 'single official test TSV required')
        prefix = str(PurePosixPath(tests[0]).parent)
        prefix = '' if prefix == '.' else prefix + '/'
        rows = list(csv.DictReader(io.StringIO(metadata[tests[0]].decode('utf-8')), delimiter='\t'))
        require(rows and all(x.get('sentence') and x.get('client_id') and x.get('path') for x in rows),
                'invalid Common Voice test metadata')
        test_speakers = {row['client_id'] for row in rows}
        for split in ('train.tsv', 'dev.tsv'):
            split_name = prefix + split
            require(split_name in metadata, 'speaker-disjoint evidence missing')
            other = csv.DictReader(io.StringIO(metadata[split_name].decode('utf-8')), delimiter='\t')
            require(not test_speakers.intersection(row['client_id'] for row in other),
                    'Common Voice test speakers overlap other split')
        candidates = [prefix + 'clips/' + row['path'] for row in rows]
    else:
        candidates = [x for x in names if x.startswith('musan/noise/free-sound/') and x.endswith('.wav')]
        require('musan/noise/free-sound/LICENSE' in metadata
                and b'All selected recordings were marked as in the Public Domain'
                in metadata['musan/noise/free-sound/LICENSE'], 'reviewed noise inventory missing')
    require(candidates and set(candidates) <= set(names), 'missing corpus candidates')
    selected = set(sorted(candidates, key=lambda x: hashlib.sha256((str(seed) + ':' + x).encode()).hexdigest())[:limit])
    # Validate all names before writing; never use extractall or member permissions.
    output = Path(output)
    output.mkdir(parents=True)
    wanted = selected | set(metadata)
    with tarfile.open(archive_path, 'r|*') as archive:
        for member in archive:
            name = member_path(member)
            if name not in wanted or not member.isfile():
                continue
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(read_member(archive, member))
    if receipt['dataset'] == 'speech_commands':
        # Subset is a local selection of the official held-out list, never a new split.
        (output / 'testing_list.txt').write_text('\n'.join(sorted(selected)) + '\n')
    if receipt['dataset'] == 'common_voice':
        selected_rows = [row for row in rows if prefix + 'clips/' + row['path'] in selected]
        # Preserve every source column locally, but preprocess copies only required evaluation fields.
        with (output / tests[0]).open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter='\t')
            writer.writeheader()
            writer.writerows(selected_rows)
        return output / prefix
    return output / 'musan' if receipt['dataset'] == 'musan' else output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()
    extract(args.archive, json.loads(args.receipt.read_text()), args.output, args.limit, args.seed)
    print('Verified bounded subset extracted locally; no audio uploaded.')
