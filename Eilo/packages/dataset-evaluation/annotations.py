"""Blind local VAD listening packs and content-bound human annotation imports."""
import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from audio import RATE
from manifests import canonical_digest, require, safe_path

METHOD = 'HUMAN_LISTENING_NO_MODEL_LABELS'
DECLARATION = 'I listened to every clip and reviewed all speech intervals, including explicit no-speech labels; these labels were not copied from model predictions.'


def bindings(manifest):
    result = []
    for case in manifest['cases']:
        require(re.fullmatch('[0-9a-f]{64}', case.get('pcm_sha256', '')), 'PCM hash required')
        result.append({key: case[key] for key in ('id', 'samples', 'pcm_sha256')})
    return result


def draft(manifest):
    return {'schema_version': 1, 'source_manifest_sha256': canonical_digest(manifest),
            'rate': RATE, 'status': 'DRAFT', 'method': METHOD, 'reviewer': '',
            'reviewed_at': '', 'declaration': '',
            'cases': [{**case, 'status': 'UNREVIEWED', 'intervals_samples': []}
                      for case in bindings(manifest)]}


def validate_review(value, expected):
    require(set(value) == {'schema_version', 'source_manifest_sha256', 'rate', 'status',
                           'method', 'reviewer', 'reviewed_at', 'declaration', 'cases'},
            'unexpected annotation fields')
    require(value['schema_version'] == 1 and value['rate'] == RATE, 'unsupported annotation schema/rate')
    require(value['status'] == 'REVIEWED' and value['method'] == METHOD, 'human-reviewed labels required')
    require(value['declaration'] == DECLARATION, 'listening declaration required')
    require(isinstance(value['reviewer'], str) and re.fullmatch('[A-Za-z0-9_.-]{1,64}', value['reviewer']),
            'reviewer pseudonym required')
    at = datetime.fromisoformat(value['reviewed_at'].replace('Z', '+00:00'))
    require(at.tzinfo is not None and at <= datetime.now(timezone.utc), 'invalid/future review time')
    require(len(value['cases']) == len(expected), 'missing/extra annotated cases')
    rows = {x['id']: x for x in value['cases']}
    require(len(rows) == len(expected) and set(rows) == {x['id'] for x in expected}, 'duplicate/changed case IDs')
    for case in expected:
        row = rows[case['id']]
        require(set(row) == {'id', 'samples', 'pcm_sha256', 'status', 'intervals_samples'},
                'unexpected case annotation fields')
        require(all(row[key] == case[key] for key in ('samples', 'pcm_sha256')), 'audio binding changed')
        require(row['status'] == 'REVIEWED', 'unreviewed/uncertain case')
        require(isinstance(row['intervals_samples'], list) and len(row['intervals_samples']) <= 3000,
                'invalid annotation intervals')
        previous = 0
        for pair in row['intervals_samples']:
            require(isinstance(pair, list) and len(pair) == 2 and all(type(x) is int for x in pair),
                    'integer sample endpoints required')
            start, stop = pair
            require(previous <= start < stop <= case['samples'], 'overlap/unsorted/out-of-bounds annotation')
            previous = stop
    return rows


def apply_review(manifest, value):
    require(value['source_manifest_sha256'] == canonical_digest(manifest), 'source manifest changed')
    rows = validate_review(value, bindings(manifest))
    result = copy.deepcopy(manifest)
    for case in result['cases']:
        # VAD-only manifest: do not retain transcripts, command truth or speaker IDs.
        for key in ('reference', 'command', 'speaker', 'speaker_id'):
            case.pop(key, None)
        case['task'] = 'vad'
        case['vad'] = [[a / RATE, b / RATE] for a, b in rows[case['id']]['intervals_samples']]
        case['annotation_status'] = 'REVIEWED_TIME_ALIGNED'
    result['annotation_review'] = copy.deepcopy(value)
    result['annotation_review_sha256'] = canonical_digest(value)
    return result


def validate_reviewed_manifest(manifest):
    value = manifest.get('annotation_review')
    require(isinstance(value, dict), 'bound human annotation review required')
    require(manifest.get('annotation_review_sha256') == canonical_digest(value), 'annotation review changed')
    require(re.fullmatch('[0-9a-f]{64}', value['source_manifest_sha256']), 'source hash required')
    rows = validate_review(value, bindings(manifest))
    require(all(x['task'] == 'vad' and x.get('annotation_status') == 'REVIEWED_TIME_ALIGNED'
                and x['vad'] == [[a / RATE, b / RATE] for a, b in rows[x['id']]['intervals_samples']]
                for x in manifest['cases']), 'reviewed intervals changed')


def prepare(manifest, root, output):
    from benchmark import validate_manifest
    validate_manifest(manifest, root)
    require(len(manifest['cases']) <= 100, 'review pack limited to 100 clips')
    output = Path(output)
    require(not output.exists(), 'refusing to overwrite review pack')
    audio = []
    size = 0
    for case in manifest['cases']:
        data = safe_path(root, case['path']).read_bytes()
        size += len(data)
        require(size <= 50 * 1024 * 1024, 'review pack exceeds 50 MiB audio limit')
        audio.append(base64.b64encode(data).decode('ascii'))
    value = draft(manifest)
    payload = json.dumps({'review': value, 'audio': audio, 'declaration': DECLARATION},
                         separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
    template = Path(__file__).with_name('annotation-review.html').read_text()
    # Allow only the exact inline script; no network or external resources.
    script = template.split('<script>')[1].split('</script>')[0].replace('__PACK__', payload)
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    html = template.replace('__PACK__', payload).replace('__SCRIPT_HASH__', digest)
    output.mkdir(parents=True)
    (output / 'review.html').write_text(html)
    (output / 'draft.json').write_text(json.dumps(value, indent=2) + '\n')
    notice = 'Local evaluation listening copy. Do not upload, rehost or commit this pack.\n'
    notice += 'Audio normalized to mono 16 kHz PCM16; no model labels included.\n'
    if manifest['kind'] == 'public_corpus':
        registry = json.loads(Path(__file__).with_name('registry.json').read_text())
        records = [x for x in registry['datasets'] if x['id'] == manifest['dataset']]
        require(len(records) == 1, 'dataset notice unavailable')
        record = records[0]
        notice += '\n'.join(str(record[key]) for key in
                            ('attribution', 'license', 'source', 'terms_source', 'redistribution')) + '\n'
        notice += 'Original archive licenses and per-component records remain in the local dataset cache.\n'
    (output / 'NOTICE.txt').write_text(notice)
    return value


def main():
    from benchmark import validate_manifest
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'import'))
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    require(args.manifest.stat().st_size <= 20 * 1024 * 1024, 'oversized manifest')
    manifest = validate_manifest(json.loads(args.manifest.read_text()), args.manifest.parent)
    if args.operation == 'prepare':
        prepare(manifest, args.manifest.parent, args.output)
    else:
        require(args.review and args.review.stat().st_size <= 20 * 1024 * 1024, 'bounded review required')
        require(not args.output.exists(), 'refusing to overwrite evidence')
        require(args.output.parent.resolve() == args.manifest.parent.resolve(),
                'write reviewed manifest beside source audio manifest')
        result = apply_review(manifest, json.loads(args.review.read_text()))
        validate_manifest(result, args.manifest.parent)
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
