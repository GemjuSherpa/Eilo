"""Validate recorded privacy declaration evidence without Apple acceptance claims."""
import argparse
import html
import json
from pathlib import Path
import re
from audit import HERE, BUILD, GATES, SYMBOLS, pins
from collect import need
from inventory_report import read, validate as validate_baseline, closed, digest, integer


def validate(value):
    closed(value, 'schema_version source_pins app_tree_sha256 nm_sha256 manifests binaries ' + ' '.join(GATES))
    need(type(value['schema_version']) is int and value['schema_version'] == 1 and value['source_pins'] == pins())
    need(all(value[k] == v for k, v in GATES.items()))
    baseline = read(BUILD/'observed.json'); validate_baseline(baseline)
    need(value['app_tree_sha256'] == baseline['ios']['tree_sha256']); digest(value['nm_sha256'])
    need(type(value['manifests']) is list and len(value['manifests']) == len(baseline['ios']['privacy_declarations']))
    categories = set(); pairs = set()
    for row, old in zip(value['manifests'], baseline['ios']['privacy_declarations']):
        closed(row, 'path sha256 tracking tracking_domains_count collected_data_count accessed_api_list_present declarations')
        need(row['path'] == old['path'] and row['sha256'] == old['sha256'] and row['tracking'] == old['declared_tracking'])
        need(row['tracking'] is None or type(row['tracking']) is bool)
        need(type(row['accessed_api_list_present']) is bool)
        for key in ['tracking_domains_count', 'collected_data_count']:
            if row[key] is not None: integer(row[key], 0, 100)
        declarations = row['declarations']; need(type(declarations) is list)
        need([d['category'] for d in declarations] == old['accessed_api_types'])
        need(row['accessed_api_list_present'] or not declarations)
        for d in declarations:
            closed(d, 'category reasons'); reasons = d['reasons']
            need(type(reasons) is list and 0 < len(reasons) <= 30 and all(type(r) is str and re.fullmatch(r'[A-F0-9]{4}\.[0-9]{1,2}', r) for r in reasons))
            need(reasons == sorted(set(reasons)))
            categories.add(d['category']); pairs.update((d['category'], r) for r in reasons)
    need(type(value['binaries']) is list and len(value['binaries']) == len(baseline['ios']['native_binaries']))
    matched = set(); matches = 0
    for row, old in zip(value['binaries'], baseline['ios']['native_binaries']):
        closed(row, 'path sha256 selected_imports'); need(row['path'] == old['path'] and row['sha256'] == old['sha256'])
        imports = row['selected_imports']; need(type(imports) is list and len(imports) <= len(SYMBOLS))
        names = []
        for item in imports:
            closed(item, 'category symbols'); category = item['category']; need(category in SYMBOLS)
            s = item['symbols']; need(type(s) is list and s and all(type(x) is str and x in SYMBOLS[category] for x in s) and s == sorted(set(s)))
            matched.add(category); matches += len(s); names.append(category)
        need(names == sorted(set(names)))
    return dict(manifests=len(value['manifests']), binaries=len(value['binaries']), declared_categories=sorted(categories),
                declared_category_reason_pairs=len(pairs), selected_import_matches=matches,
                candidate_categories_without_app_wide_declaration=sorted(matched-categories), **GATES)


def export(value, output):
    summary = validate(value); need(not output.exists()); output.mkdir(parents=True)
    (output/'summary.json').write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    (output/'summary.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>iOS privacy declarations</title>'
        '<h1>Recorded simulator privacy declarations</h1><p>Declared reasons and selected undefined imports in a pinned unsigned simulator build. '
        'Imports are candidates, not proof of executed APIs or permitted purposes. No matches does not mean no API usage. '
        'App-wide category presence does not establish SDK ownership, reason suitability, complete coverage, runtime privacy or App Store acceptance.</p><pre>'
        + html.escape(json.dumps(summary, indent=2)) + '</pre><details><summary>Observed records</summary><pre>'
        + html.escape(json.dumps(value, indent=2)) + '</pre></details></html>\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=HERE/'observed.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(); value = read(args.report)
    print(json.dumps(export(value, args.output) if args.output else validate(value), indent=2))
