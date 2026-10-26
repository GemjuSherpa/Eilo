"""Closed notice-provenance reporting, without licensing or release approval."""
import argparse
import base64
from collections import Counter
import html
import json
from pathlib import Path
from notices import HERE,BUILD,pins,coordinate,is_notice
from collect import need,sha,safe_name,text
from inventory_report import read,validate as validate_baseline,closed,digest,integer


def notice_records(rows):
    need(type(rows) is list and len(rows)<=1000)
    paths=[]
    for n in rows:
        closed(n,'path bytes sha256');need(type(n['path']) is str)
        fragments=n['path'].split('!');need(len(fragments)<=2)
        if len(fragments)==2:need(fragments[0]=='classes.jar')
        for fragment in fragments:safe_name(fragment)
        need(is_notice(fragments[-1]));integer(n['bytes'],0,512*1024);digest(n['sha256']);paths.append(n['path'])
    need(paths==sorted(set(paths)))


def declaration(value,row):
    closed(value,'status chain child_embedded_pom_sha256')
    need(value['status'] in {'CACHED_POM_MISSING','NO_VERIFIED_CHILD_ARTIFACT','CHILD_POM_NOT_EMBEDDED','CACHED_PARENT_DECLARATION','CACHED_DIRECT_DECLARATION','NO_DECLARATION_IN_CHAIN','DEPTH_BOUND_REACHED'})
    chain=value['chain'];need(type(chain) is list and len(chain)<=4)
    coordinates=[]
    for i,item in enumerate(chain):
        closed(item,'coordinate pom_sha256 licenses');coordinate(item['coordinate'].split(':'));digest(item['pom_sha256']);coordinates.append(item['coordinate'])
        if i==0:need(item['coordinate']==':'.join(row[k] for k in ['group','artifact','version']) and item['pom_sha256'] in {p['sha256'] for p in row['poms']})
        need(type(item['licenses']) is list and len(item['licenses'])<=20)
        for license in item['licenses']:
            closed(license,'name url');text(license['name'])
            if license['url'] is not None:text(license['url'],512);need(license['url'].startswith(('http://','https://')))
    need(len(set(coordinates))==len(coordinates))
    if chain:
        need(value['child_embedded_pom_sha256']==chain[0]['pom_sha256'])
        need(all(not item['licenses'] for item in chain[:-1]))
    else:need(value['child_embedded_pom_sha256'] is None)
    if value['status'] in ('CACHED_PARENT_DECLARATION','CACHED_DIRECT_DECLARATION'):
        need(chain and chain[-1]['licenses'])
        need(len(chain)>=2 if value['status']=='CACHED_PARENT_DECLARATION' else len(chain)==1)
    else:need(all(not item['licenses'] for item in chain))


def validate(r):
    closed(r,'schema_version purpose source_pins baseline_inventory_sha256 maven npm_exit packaged own_workspace_license sbom_completeness redistribution_review release_acceptance network_privacy physical memory')
    need(type(r['schema_version']) is int and r['schema_version']==1 and r['purpose']=='CACHED_DEPENDENCY_NOTICE_PROVENANCE')
    need(r['source_pins']==pins() and r['baseline_inventory_sha256']==sha(BUILD/'observed.json'))
    baseline=read(BUILD/'observed.json');validate_baseline(baseline)
    for k,v in dict(own_workspace_license='OWNER_DECISION_PENDING',sbom_completeness='NOT_ESTABLISHED',redistribution_review='REQUIRED',release_acceptance='BLOCKED',network_privacy='NOT_ESTABLISHED',physical='NOT_RUN',memory='DISABLED').items():need(r[k]==v)
    need(type(r['maven']) is list and len(r['maven'])==len(baseline['maven']))
    parent_count=0
    for record,source in zip(r['maven'],baseline['maven']):
        closed(record,'coordinate artifact_sha256 scan notices parent_declaration')
        need(record['coordinate']==coordinate(tuple(source[k] for k in ['group','artifact','version'])) and record['artifact_sha256']==source['artifact_sha256'])
        if source['artifact_sha256'] is None:need(record['scan']=='NO_RECORDED_ARTIFACT_DIGEST' and record['notices'] is None)
        else:
            digest(record['artifact_sha256']);notice_records(record['notices'])
            need(record['scan']==('NOTICE_HASHES_RECORDED' if record['notices'] else 'NO_MATCHING_EMBEDDED_NOTICE'))
        if not any(p['licenses'] for p in source['poms']):
            declaration(record['parent_declaration'],source)
            parent_count+=int(record['parent_declaration']['status']=='CACHED_PARENT_DECLARATION')
        else:need(record['parent_declaration'] is None)
    n=r['npm_exit'];closed(n,'name version integrity archive_sha256 archive_bytes legacy_license_declarations files source')
    lock=read(HERE.parent.parent/'package-lock.json')['packages']['node_modules/exit']
    need(n['name']=='exit' and n['version']==lock['version']=='0.1.2' and n['integrity']==lock['integrity'])
    need(n['integrity'].startswith('sha512-') and len(base64.b64decode(n['integrity'][7:],validate=True))==64)
    digest(n['archive_sha256']);integer(n['archive_bytes'],1,32*1024*1024)
    need(n['legacy_license_declarations']==[{'type':'MIT','url':'https://github.com/cowboy/node-exit/blob/master/LICENSE-MIT'}])
    need(n['source']=='LOCK_SRI_VERIFIED_CACHED_TARBALL_AND_INSTALLED_BYTES')
    need(type(n['files']) is list and [x['path'] for x in n['files']]==['package/LICENSE-MIT','package/package.json'])
    for f in n['files']:
        closed(f,'path bytes sha256 installed_bytes_match');integer(f['bytes'],1,512*1024);digest(f['sha256']);need(f['installed_bytes_match'] is True)
    p=r['packaged'];closed(p,'android ios scope');closed(p['android'],'artifact_sha256 notices');closed(p['ios'],'tree_sha256 notices')
    need(p['scope']=='MATCHING_FILENAMES_AND_EXACT_BYTES_ONLY_NOT_COMPLETE_NOTICE_COVERAGE')
    need(p['android']['artifact_sha256']==baseline['android']['sha256'] and p['ios']['tree_sha256']==baseline['ios']['tree_sha256'])
    notice_records(p['android']['notices']);notice_records(p['ios']['notices'])
    unique={n['sha256'] for record in r['maven'] for n in record['notices'] or []}
    packed={n['sha256'] for n in p['android']['notices']}
    counts=Counter(record['scan'] for record in r['maven'])
    return dict(maven_entries=len(r['maven']),verified_artifacts_scanned=sum(record['artifact_sha256'] is not None for record in r['maven']),
        artifacts_with_notices=counts['NOTICE_HASHES_RECORDED'],artifacts_without_matching_notice=counts['NO_MATCHING_EMBEDDED_NOTICE'],unrecorded_artifact_digests=counts['NO_RECORDED_ARTIFACT_DIGEST'],
        notice_records=sum(len(record['notices'] or []) for record in r['maven']),distinct_notice_hashes=len(unique),distinct_notice_hashes_found_in_apk=len(unique&packed),
        cached_parent_declarations=parent_count,npm_exit_source_notice='SRI_AND_INSTALLED_BYTES_VERIFIED',apk_matching_notice_files=len(p['android']['notices']),ios_matching_notice_files=len(p['ios']['notices']),
        own_workspace_license='OWNER_DECISION_PENDING',redistribution_review='REQUIRED',sbom_completeness='NOT_ESTABLISHED',release_acceptance='BLOCKED',physical='NOT_RUN')


def export(r,output):
    summary=validate(r);need(not output.exists());output.mkdir(parents=True)
    (output/'summary.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    rows=''.join('<tr><th>'+html.escape(k)+'</th><td>'+html.escape(str(v))+'</td></tr>' for k,v in summary.items())
    (output/'summary.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Dependency notice provenance</title><h1>Cached dependency notice provenance</h1>'
        '<p>Notice hashes, npm lock-SRI verification, installed-byte matches and literal cached POM parent declarations. No new license selection, complete SBOM, legal/redistribution approval, signing, runtime privacy or physical acceptance.</p>'
        '<p>Missing matching notice filenames do not establish missing licensing. Equal notice bytes do not prove complete attribution. The iOS filename check does not inspect embedded text or replace full notice review. '
        'Maven parent hashes are locally observed, not authenticated publisher metadata or a full effective-POM resolver. Eilo ownership licensing remains unresolved.</p><table border="1">'+rows+'</table>'
        '<details><summary>Observed provenance</summary><pre>'+html.escape(json.dumps(r,indent=2,allow_nan=False))+'</pre></details></html>\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',type=Path,default=HERE/'observed.json');parser.add_argument('--output',type=Path);args=parser.parse_args();r=read(args.report)
    print(json.dumps(export(r,args.output) if args.output else validate(r),indent=2))
