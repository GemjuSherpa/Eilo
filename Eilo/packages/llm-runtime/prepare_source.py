#!/usr/bin/env python3
"""Explicit build-only download of the exact public runtime source, never models."""
import hashlib
import tarfile
import urllib.request
from check_host import CACHE, PROVENANCE, SOURCE, verify_tree


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    archive = CACHE / 'llama-v0.6.0.tar.gz'
    request = urllib.request.Request(PROVENANCE['runtime']['source_url'],
                                     headers={'User-Agent': 'Eilo-source-verification'})
    staged = CACHE / 'source-download.tmp'
    try:
        with urllib.request.urlopen(request, timeout=60) as response, staged.open('wb') as output:
            if response.geturl() != PROVENANCE['runtime']['source_url']:
                raise ValueError('unexpected source redirect')
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > 100 * 1024 * 1024:
                    raise ValueError('source archive too large')
                output.write(chunk)
        with staged.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != PROVENANCE['runtime']['source_archive_sha256']:
                raise ValueError('source archive integrity failed')
        if SOURCE.exists():
            verify_tree(staged, SOURCE, SOURCE.name)
        else:
            with tarfile.open(staged) as archive_file:
                archive_file.extractall(CACHE, filter='data')
            verify_tree(staged, SOURCE, SOURCE.name)
        staged.replace(archive)
    finally:
        staged.unlink(missing_ok=True)
    print('Pinned official llama.cpp source verified in ignored cache; no model download.')


if __name__ == '__main__':
    main()
