#!/usr/bin/env python3
"""Opt-in pinned official source download. Default invocation prints the plan only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request


def artifacts(lock):
    if lock['model'] != 'Qwen/Qwen3-0.6B' or not re.fullmatch(r'[0-9a-f]{40}', lock['model_revision']):
        raise ValueError('Unexpected model or revision')
    seen = set()
    for row in lock['source_artifacts']:
        name = row['path']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in ('.', '..') or name in seen:
            raise ValueError('Unsafe or duplicate artifact')
        seen.add(name)
        if type(row['bytes']) is not int or row['bytes'] <= 0:
            raise ValueError('Invalid artifact size')
        digest = row['sha256'] or row['git_blob']
        if not re.fullmatch(r'[0-9a-f]{64}' if row['sha256'] else r'[0-9a-f]{40}', digest):
            raise ValueError('Invalid artifact digest')
    return lock['source_artifacts']


def verify(path, row):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != row['bytes']:
        raise ValueError('Artifact missing, unsafe or wrong size: ' + row['path'])
    digest = hashlib.sha256() if row['sha256'] else hashlib.sha1()
    if not row['sha256']:
        digest.update(('blob ' + str(row['bytes']) + '\0').encode())
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(65536), b''):
            digest.update(chunk)
    if digest.hexdigest() != (row['sha256'] or row['git_blob']):
        raise ValueError('Artifact digest mismatch: ' + row['path'])


def fetch(root, row, url, opener=urllib.request.urlopen):
    destination = root / row['path']
    if destination.exists() or destination.is_symlink():
        verify(destination, row)
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=root, prefix='.download-', delete=False) as output:
            temporary = Path(output.name)
            with opener(url, timeout=60) as response:
                received = 0
                while True:
                    chunk = response.read(min(65536, row['bytes'] - received + 1))
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > row['bytes']:
                        raise ValueError('Artifact exceeds pinned size')
                    output.write(chunk)
        verify(temporary, row)
        # Atomic no-clobber publication; never replace an existing file.
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--download-approved', action='store_true', help='Use only after operator approval')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    lock = json.loads(Path(__file__).with_name('qwen3-0.6b-source-lock.json').read_text())
    rows = artifacts(lock)
    print(json.dumps({'model': lock['model'], 'revision': lock['model_revision'],
                      'bytes': sum(row['bytes'] for row in rows), 'license': lock['license']}))
    if not args.download_approved and not args.verify_only:
        return
    if args.destination is None:
        parser.error('--destination required')
    root = args.destination
    if root.is_symlink():
        raise ValueError('Symlink destination denied')
    if args.verify_only:
        for row in rows:
            verify(root / row['path'], row)
        return
    root.mkdir(parents=True, exist_ok=True)
    for row in rows:
        url = 'https://huggingface.co/' + lock['model'] + '/resolve/' + lock['model_revision'] + '/' + row['path']
        fetch(root, row, url)
        print('Verified ' + row['path'])


if __name__ == '__main__':
    main()
