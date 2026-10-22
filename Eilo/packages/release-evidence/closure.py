"""Validate a pending requirement ledger without conferring release acceptance."""
import argparse
import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PLAN = 'planning/sprint-issues.json'
BLOCKERS = {'INTEGRATED_PHYSICAL_ACCEPTANCE', 'PRIVACY_STORE_IDENTITY_ACCEPTANCE',
            'PERFORMANCE_BACKGROUND_ACCEPTANCE', 'PROVIDER_NATIVE_SEARCH_ACCEPTANCE',
            'NATIVE_VISUAL_SURFACE_ACCEPTANCE'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def closed(obj, fields):
    require(type(obj) is dict and set(obj) == set(fields), 'closed record required')


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, 'duplicate JSON key')
        obj[key] = value
    return obj


def read(path, limit=524288):
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, 'input too large')
    return raw


def parse(raw):
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object)


def requirements(raw):
    issues = parse(raw)
    require(type(issues) is list and 0 < len(issues) <= 32, 'invalid planning source')
    mapping = {}
    tasks = set()
    for issue in issues:
        require(type(issue) is dict and type(issue.get('body')) is str, 'missing issue body')
        task = None
        for line in issue['body'].splitlines():
            match = re.match(r'- \[[ x]\] \*\*(VC-[A-Z0-9-]+)', line)
            if match:
                task = match[1]
                require(task not in tasks, 'duplicate planned task')
                tasks.add(task)
            if line.strip().startswith('- Requirements:'):
                require(task is not None, 'requirement without task')
                ids = re.findall(r'\b[A-Z]{1,2}\d{2}\b', line)
                require(bool(ids), 'empty requirement assignment')
                for requirement in ids:
                    mapping.setdefault(requirement, set()).add(task)
    require(bool(mapping), 'no requirements found')
    return {key: sorted(value) for key, value in sorted(mapping.items())}


def pinned(root, record):
    closed(record, ('path', 'sha256', 'kind'))
    require(record['kind'] == 'SUPPORTING_CONTEXT_NOT_ACCEPTANCE', 'source is not acceptance')
    name = record['path']
    require(type(name) is str and re.fullmatch(r'(?:planning|Eilo)/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+', name), 'invalid source path')
    parts = Path(name).parts
    require(all(part not in ('.', '..') for part in parts), 'source traversal')
    path = root
    for part in parts:
        path = path / part
        require(not path.is_symlink(), 'symlink source forbidden')
    require(type(record['sha256']) is str and re.fullmatch(r'[a-f0-9]{64}', record['sha256']), 'invalid SHA256')
    raw = read(path)
    require(hashlib.sha256(raw).hexdigest() == record['sha256'], 'stale source evidence')
    return raw


def evaluate(ledger, root=REPO):
    closed(ledger, ('schema', 'sprint', 'reviewed_main', 'release_decision', 's08_decision',
                    'persistent_memory_allowed', 'supported_configurations', 'sources', 'requirements'))
    require(type(ledger['schema']) is int and ledger['schema'] == 1 and ledger['sprint'] == 'S17', 'wrong schema')
    require(type(ledger['reviewed_main']) is str and re.fullmatch(r'[a-f0-9]{40}', ledger['reviewed_main']), 'invalid reviewed revision')
    require(ledger['release_decision'] == 'HOLD' and ledger['s08_decision'] == 'HOLD'
            and ledger['persistent_memory_allowed'] is False and ledger['supported_configurations'] == [], 'pending ledger cannot approve release, memory or support')
    sources = ledger['sources']
    require(type(sources) is dict and 1 <= len(sources) <= 32 and 'plan' in sources, 'source inventory required')
    require(all(type(key) is str and re.fullmatch(r'[a-z][a-z0-9-]{0,40}', key) for key in sources), 'invalid source alias')
    source_bytes = {key: pinned(root, value) for key, value in sources.items()}
    require(sources['plan']['path'] == PLAN, 'canonical planning source required')
    expected = requirements(source_bytes['plan'])
    rows = ledger['requirements']
    require(type(rows) is list and len(rows) == len(expected), 'all requirements required')
    seen = set()
    for row in rows:
        closed(row, ('id', 'tasks', 'full_app_acceptance', 'blocker', 'supporting_sources'))
        identifier = row['id']
        require(type(identifier) is str and identifier in expected and identifier not in seen, 'unknown/duplicate requirement')
        seen.add(identifier)
        require(row['tasks'] == expected[identifier], 'planned requirement/task mapping mismatch')
        require(row['full_app_acceptance'] == 'BLOCKED', 'preparation cannot establish full-app pass')
        require(type(row['blocker']) is str and row['blocker'] in BLOCKERS, 'explicit blocker required')
        refs = row['supporting_sources']
        require(type(refs) is list and 0 < len(refs) <= 8 and all(type(ref) is str and ref in sources for ref in refs), 'known supporting records required')
        require(len(set(refs)) == len(refs), 'duplicate supporting record')
    return {'sprint': 'S17', 'structure': 'VALID_PENDING_LEDGER', 'requirements': len(rows),
            'blocked_requirements': len(rows), 'supporting_sources': len(sources),
            'release_decision': 'HOLD', 'physical_acceptance': 'NOT_ESTABLISHED',
            's08_decision': 'HOLD', 'persistent_memory_allowed': False, 'supported_configurations': []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', type=Path, nargs='?', default=Path(__file__).with_name('ledger.json'))
    parser.add_argument('--require-release-ready', action='store_true')
    args = parser.parse_args()
    try:
        result = evaluate(parse(read(args.ledger)))
    except (ValueError, OSError, TypeError, KeyError, RecursionError) as error:
        print(json.dumps({'release_decision': 'INVALID', 'error_type': type(error).__name__}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if args.require_release_ready else 0


if __name__ == '__main__':
    raise SystemExit(main())
