"""Offline aggregate-evidence inventory. Never executes a device journey."""
import argparse
import hashlib
import json
import re
from pathlib import Path

CASES = {
    'foreground': ('ios', 'android'),
    'consent-denied-revoked': ('ios', 'android'),
    'locked-content-redaction': ('ios', 'android'),
    'stop-new-query-stale-callback': ('ios', 'android'),
    'expiry-pin-accessibility-focus': ('ios', 'android'),
    'screen-reader-large-text-reduced-motion': ('ios', 'android'),
    'media-denied-and-explicit-resume': ('ios', 'android'),
    'termination-relaunch-no-auto-resume': ('ios', 'android'),
    'notification-generic-payload-and-explicit-open': ('ios',),
    'notification-focus-settings-system-timing': ('ios',),
    'overlay-touch-back-insets-native-stop': ('android',),
    'overlay-blocking-app-and-oem-lifecycle': ('android',),
    'independent-mic-background-display-consent': ('ios', 'android'),
    'search-declined-confirmed-minimized-egress': ('ios', 'android'),
    'storage-cache-snapshot-privacy': ('ios', 'android'),
}
STATUSES = {'PASS', 'FAIL', 'NOT_RUN', 'BLOCKED', 'UNSUPPORTED'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def closed(value, keys):
    require(type(value) is dict and set(value) == set(keys), 'closed record required')


def token(value):
    require(type(value) is str and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', value), 'invalid alias')


def digest(value):
    require(type(value) is str and re.fullmatch(r'[a-f0-9]{64}', value), 'invalid SHA256')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def load(path):
    with path.open('rb') as stream:
        raw = stream.read(131073)
    require(len(raw) <= 131072, 'matrix exceeds 128 KiB')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object)


def evaluate(matrix, root):
    closed(matrix, ('schema', 'sprint', 'owner_approved_devices', 'devices', 'results'))
    require(type(matrix['schema']) is int and matrix['schema'] == 1 and matrix['sprint'] == 'S16', 'unsupported schema')
    require(type(matrix['owner_approved_devices']) is bool, 'owner approval must be boolean')
    devices = matrix['devices']
    rows = matrix['results']
    require(type(devices) is list and len(devices) <= 32, 'invalid device list')
    require(type(rows) is list and len(rows) <= 480, 'invalid result list')
    by_id = {}
    for device in devices:
        closed(device, ('alias', 'platform', 'model_family', 'os_version', 'build_sha256', 'physical'))
        token(device['alias'])
        token(device['model_family'])
        require(device['platform'] in ('ios', 'android'), 'unsupported platform')
        require(type(device['os_version']) is str and re.fullmatch(r'[0-9]{1,2}(\.[0-9]{1,3}){1,2}', device['os_version']), 'invalid OS version')
        digest(device['build_sha256'])
        require(device['physical'] is True, 'simulator evidence cannot satisfy physical matrix')
        require(device['alias'] not in by_id, 'duplicate device alias')
        by_id[device['alias']] = device
    seen = set()
    counts = {status: 0 for status in sorted(STATUSES)}
    evidence_paths = set()
    for row in rows:
        closed(row, ('device', 'case', 'status', 'evidence'))
        require(type(row['device']) is str and row['device'] in by_id, 'unknown device')
        require(type(row['case']) is str and row['case'] in CASES, 'unknown case')
        device = by_id[row['device']]
        require(device['platform'] in CASES[row['case']], 'case not applicable to platform')
        key = (row['device'], row['case'])
        require(key not in seen, 'duplicate result')
        seen.add(key)
        require(type(row['status']) is str and row['status'] in STATUSES, 'invalid status')
        counts[row['status']] += 1
        evidence = row['evidence']
        if row['status'] in ('PASS', 'FAIL', 'UNSUPPORTED'):
            closed(evidence, ('path', 'sha256', 'build_sha256', 'reviewed_by_owner'))
            digest(evidence['sha256'])
            require(evidence['build_sha256'] == device['build_sha256'], 'evidence build mismatch')
            require(evidence['reviewed_by_owner'] is True, 'physical evidence needs owner review')
            name = evidence['path']
            require(type(name) is str and re.fullmatch(r'evidence/[a-z0-9-]{1,100}\.json', name), 'invalid aggregate evidence path')
            require(name not in evidence_paths, 'one aggregate artifact required per device/case')
            evidence_paths.add(name)
            path = root / name
            require(not path.is_symlink() and not (root / 'evidence').is_symlink(), 'symlink evidence forbidden')
            with path.open('rb') as stream:
                raw = stream.read(65537)
            require(0 < len(raw) <= 65536, 'evidence size out of bounds')
            require(hashlib.sha256(raw).hexdigest() == evidence['sha256'], 'evidence checksum mismatch')
            require(type(json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object)) is dict, 'aggregate JSON object required')
        else:
            require(evidence is None, 'unrun/blocked row must not claim evidence')
    expected = {(d['alias'], case) for d in devices for case, platforms in CASES.items() if d['platform'] in platforms}
    missing = len(expected - seen)
    accepted = (matrix['owner_approved_devices'] and bool(devices) and not missing
                and counts['PASS'] == len(expected))
    return {'sprint': 'S16', 'decision': 'READY_FOR_MANUAL_ACCEPTANCE_REVIEW' if accepted else 'HOLD',
            'physical_acceptance': 'NOT_ESTABLISHED_BY_THIS_TOOL', 'devices': len(devices),
            'required_cases': len(expected), 'missing_cases': missing, 'counts': counts,
            's08_decision': 'HOLD', 'persistent_memory_allowed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('matrix', type=Path)
    parser.add_argument('--require-ready', action='store_true')
    args = parser.parse_args()
    try:
        result = evaluate(load(args.matrix), args.matrix.parent)
    except (ValueError, OSError, TypeError, KeyError) as error:
        # Do not echo input values, paths, JSON bodies or exception content.
        print(json.dumps({'decision': 'INVALID', 'error_type': type(error).__name__}))
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 2 if args.require_ready and result['decision'] == 'HOLD' else 0


if __name__ == '__main__':
    raise SystemExit(main())
