"""Local archive receipts and immutable corpus checks; no network or extraction."""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_registry(value):
    require(value['schema_version'] == 1, 'unsupported registry version')
    ids = set()
    for item in value['datasets']:
        require(item['id'] not in ids, 'duplicate dataset')
        ids.add(item['id'])
        require(item['license'] in ('CC0-1.0', 'CC-BY-4.0'), 'unreviewed license')
        require(item['source'].startswith('https://'), 'non-HTTPS source')
        require(item['download_url'] is None or item['download_url'].startswith('https://'),
                'non-HTTPS download')
        require(item['sha256'] is None or re.fullmatch('[0-9a-f]{64}', item['sha256']),
                'invalid checksum')
        require(item['bytes'] is None or type(item['bytes']) is int and item['bytes'] > 0,
                'invalid archive size')
        require(item['checksum_status'] in ('NOT_DOWNLOADED', 'LOCAL_OBSERVED', 'PUBLISHER_VERIFIED'),
                'invalid checksum status')
        if item['checksum_status'] != 'NOT_DOWNLOADED':
            require(item['sha256'] is not None and item['bytes'] is not None, 'missing receipt')
        require(item['version'] != 'UNSELECTED' or item['sha256'] is None, 'release not selected')
    return value


def receipt(registry, dataset, archive, license_evidence):
    validate_registry(registry)
    item = next(x for x in registry['datasets'] if x['id'] == dataset)
    require(item['permission'].startswith('APPROVED_BY_USER'), 'download/use approval required')
    require(item['version'] != 'UNSELECTED', 'select release first')
    require(Path(license_evidence).is_file(), 'local license evidence required')
    return {'schema_version': 1, 'dataset': dataset, 'version': item['version'],
            'source': item['source'], 'sha256': sha256(archive),
            'bytes': Path(archive).stat().st_size, 'checksum_status': 'LOCAL_OBSERVED',
            'license': item['license'], 'license_evidence_sha256': sha256(license_evidence),
            'attribution': item['attribution'], 'permission': item['permission']}


def validate_receipt(value):
    require(value['schema_version'] == 1, 'invalid receipt schema')
    require(value['dataset'] in ('common_voice', 'musan', 'speech_commands'), 'unknown receipt corpus')
    require(isinstance(value['version'], str) and value['version'] != 'UNSELECTED', 'unselected receipt')
    require(value['permission'].startswith('APPROVED_BY_USER'), 'corpus permission required')
    require(value['license'] in ('CC0-1.0', 'CC-BY-4.0'), 'unreviewed corpus license')
    for key in ('sha256', 'license_evidence_sha256'):
        require(re.fullmatch('[0-9a-f]{64}', value[key]), 'invalid receipt checksum')
    require(type(value['bytes']) is int and value['bytes'] > 0, 'invalid receipt archive size')
    require(value['checksum_status'] in ('LOCAL_OBSERVED', 'PUBLISHER_VERIFIED'), 'unverified receipt')
    return value


def verify_receipt(value, archive):
    validate_receipt(value)
    require(value['checksum_status'] in ('LOCAL_OBSERVED', 'PUBLISHER_VERIFIED'), 'unverified receipt')
    require(Path(archive).stat().st_size == value['bytes'], 'archive size changed')
    require(sha256(archive) == value['sha256'], 'archive checksum changed')


def safe_path(root, relative):
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts, 'unsafe relative path')
    target = (Path(root) / path).resolve()
    require(target.is_relative_to(Path(root).resolve()), 'path escaped root')
    require(target.is_file(), 'missing input file')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, default=HERE / 'registry.json')
    parser.add_argument('--dataset', choices=['musan', 'speech_commands', 'common_voice'])
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--license-evidence', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    registry = validate_registry(json.loads(args.registry.read_text()))
    if args.dataset:
        require(all((args.archive, args.license_evidence, args.output)), 'receipt arguments missing')
        args.output.write_text(json.dumps(receipt(registry, args.dataset, args.archive,
                                                  args.license_evidence), indent=2) + '\n')
    else:
        print('Registry valid; downloaded corpus acceptance remains separate.')


if __name__ == '__main__':
    main()
