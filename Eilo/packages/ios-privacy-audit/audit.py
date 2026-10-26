"""Read the pinned simulator app's privacy declarations and selected undefined imports."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent / 'build-inventory'
sys.path.insert(0, str(BUILD))
from collect import need, sha, safe_name
from inventory_report import read, validate as validate_baseline

# Deliberately incomplete candidate list. Imports do not prove use or purpose.
SYMBOLS = {
    'NSPrivacyAccessedAPICategoryFileTimestamp': ['_fstat', '_lstat', '_stat'],
    'NSPrivacyAccessedAPICategorySystemBootTime': ['_mach_absolute_time'],
    'NSPrivacyAccessedAPICategoryUserDefaults': ['_OBJC_CLASS_$_NSUserDefaults'],
    'NSPrivacyAccessedAPICategoryDiskSpace': ['_fstatfs', '_fstatvfs', '_statfs', '_statvfs'],
}
GATES = dict(scope='PINNED_UNSIGNED_SIMULATOR_DECLARATIONS_AND_SELECTED_IMPORTS',
             purpose_review='REQUIRED', api_coverage='NOT_ESTABLISHED',
             app_store_acceptance='NOT_ESTABLISHED', network_privacy='NOT_ESTABLISHED',
             release_acceptance='BLOCKED', physical='NOT_RUN', memory='DISABLED')
DOCTYPE = b'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">'


def pins():
    paths = [HERE/'audit.py', BUILD/'collect.py', BUILD/'inventory_report.py', BUILD/'observed.json']
    return {str(p.relative_to(HERE.parent.parent)): sha(p) for p in paths}


def manifest(raw):
    """Reject duplicate plist keys; allow only the standard non-resolving plist doctype."""
    need(0 < len(raw) <= 256*1024)
    if not raw.startswith(b'bplist'):
        cleaned = raw.replace(DOCTYPE, b'')
        need(b'<!DOCTYPE' not in cleaned.upper() and b'<!ENTITY' not in cleaned.upper())
        tree = ET.fromstring(cleaned)
        for node in tree.iter('dict'):
            children = list(node)
            need(len(children) % 2 == 0)
            keys = [children[i].text for i in range(0, len(children), 2)]
            need(all(children[i].tag == 'key' for i in range(0, len(children), 2)))
            need(all(type(k) is str for k in keys) and len(set(keys)) == len(keys))
        raw = cleaned
    else:
        # Binary dictionaries must also reject duplicate keys while decoding.
        class Unique(dict):
            def __setitem__(self, key, value):
                need(key not in self)
                super().__setitem__(key, value)
        return declaration(plistlib.loads(raw, dict_type=Unique))
    return declaration(plistlib.loads(raw))


def declaration(value):
    need(isinstance(value, dict))
    need(set(value) <= {'NSPrivacyAccessedAPITypes', 'NSPrivacyCollectedDataTypes', 'NSPrivacyTracking', 'NSPrivacyTrackingDomains'})
    tracking = value.get('NSPrivacyTracking')
    need(tracking is None or type(tracking) is bool)
    domains = value.get('NSPrivacyTrackingDomains')
    need(domains is None or type(domains) is list and len(domains) <= 100 and all(type(d) is str and 0 < len(d) <= 253 for d in domains))
    # Export counts only, never domain values or collected-data detail/purpose text.
    collected = value.get('NSPrivacyCollectedDataTypes')
    need(collected is None or type(collected) is list and len(collected) <= 100)
    rows = value.get('NSPrivacyAccessedAPITypes')
    need(rows is None or type(rows) is list and len(rows) <= 100)
    declarations = []
    for item in rows or []:
        need(isinstance(item, dict) and set(item) == {'NSPrivacyAccessedAPIType', 'NSPrivacyAccessedAPITypeReasons'})
        category, reasons = item['NSPrivacyAccessedAPIType'], item['NSPrivacyAccessedAPITypeReasons']
        need(type(category) is str and re.fullmatch(r'NSPrivacyAccessedAPICategory[A-Za-z]{1,60}', category))
        need(type(reasons) is list and 0 < len(reasons) <= 30 and all(type(r) is str and re.fullmatch(r'[A-F0-9]{4}\.[0-9]{1,2}', r) for r in reasons))
        need(len(set(reasons)) == len(reasons))
        declarations.append(dict(category=category, reasons=sorted(reasons)))
    need(len({d['category'] for d in declarations}) == len(declarations))
    return dict(tracking=tracking, tracking_domains_count=None if domains is None else len(domains),
                collected_data_count=None if collected is None else len(collected),
                accessed_api_list_present=rows is not None,
                declarations=sorted(declarations, key=lambda x: x['category']))


def tree_digest(root):
    need(root.is_dir() and not root.is_symlink())
    entries = sorted(root.rglob('*'))
    need(len(entries) <= 50000 and all(not p.is_symlink() for p in entries))
    rows = []
    for p in entries:
        need(p.is_file() or p.is_dir())
        if p.is_dir(): continue
        name = safe_name(p.relative_to(root).as_posix())
        need(p.stat().st_size <= 256*1024*1024)
        rows.append(dict(path=name, bytes=p.stat().st_size, sha256=sha(p)))
    need(sum(r['bytes'] for r in rows) <= 2*1024**3)
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def selected_imports(output):
    need(type(output) is str and len(output.encode()) <= 8*1024*1024)
    lines = {line.strip() for line in output.splitlines()}
    return [dict(category=category, symbols=sorted(lines & set(symbols)))
            for category, symbols in sorted(SYMBOLS.items()) if lines & set(symbols)]


def inspect(root, nm):
    before = pins()
    baseline = read(BUILD/'observed.json'); validate_baseline(baseline)
    expected = baseline['ios']; need(tree_digest(root) == expected['tree_sha256'])
    tool_pin = sha(nm)
    manifests = []
    for row in expected['privacy_declarations']:
        path = root / safe_name(row['path']); need(sha(path) == row['sha256'])
        d = manifest(path.read_bytes())
        need([v['category'] for v in d['declarations']] == row['accessed_api_types'] and d['tracking'] == row['declared_tracking'])
        manifests.append(dict(path=row['path'], sha256=row['sha256'], **d))
    binaries = []
    for row in expected['native_binaries']:
        path = root / safe_name(row['path']); need(sha(path) == row['sha256'])
        result = subprocess.run([str(nm), '-u', '-j', str(path)], capture_output=True, text=True, check=True, timeout=60)
        binaries.append(dict(path=row['path'], sha256=row['sha256'], selected_imports=selected_imports(result.stdout)))
    need(pins() == before and sha(nm) == tool_pin and tree_digest(root) == expected['tree_sha256'])
    return dict(schema_version=1, source_pins=before, app_tree_sha256=expected['tree_sha256'], nm_sha256=tool_pin,
                manifests=manifests, binaries=binaries, **GATES)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ios-app', required=True, type=Path)
    parser.add_argument('--nm', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(); need(not args.output.exists())
    result = inspect(args.ios_app, args.nm)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
