"""Validate local artifact observations and export an explicitly incomplete inventory."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
from collect import HERE,REPO,REPO_PINS,need,sha,safe_name,text


def closed(value,keys):need(type(value) is dict and set(value)==set(keys.split()))
def integer(value,minimum=0,maximum=2*1024**3):need(type(value) is int and minimum<=value<=maximum)
def digest(value):need(type(value) is str and re.fullmatch('[0-9a-f]{64}',value))
def names(values,pattern=None):
    need(type(values) is list and values==sorted(set(values)))
    for value in values:
        text(value,2000)
        if pattern:need(re.fullmatch(pattern,value))

def validate(r):
    closed(r,'schema_version purpose release_acceptance license_approval network_privacy physical memory source_pins repository_pins input_pins tool_pins android ios maven npm_lock_only pods_lock_and_notices sbom_completeness redistribution_review signing_provenance')
    need(type(r['schema_version']) is int and r['schema_version']==1 and r['purpose']=='NORMAL_BUILD_ARTIFACT_INVENTORY')
    for key,value in dict(release_acceptance='BLOCKED',license_approval='NOT_GRANTED',network_privacy='NOT_ESTABLISHED',physical='NOT_RUN',memory='DISABLED',sbom_completeness='NOT_ESTABLISHED',redistribution_review='REQUIRED',signing_provenance='NOT_REVIEWED').items():need(r[key]==value)
    need(r['source_pins']=={'collect.py':sha(HERE/'collect.py')})
    need(r['repository_pins']=={name:sha(REPO/name) for name in REPO_PINS})
    closed(r['input_pins'],'sdk_metadata pods_lock acknowledgements npm_lock')
    closed(r['tool_pins'],'readelf aapt otool')
    for group in ('input_pins','tool_pins'):
        for value in r[group].values():digest(value)
    need(r['input_pins']['npm_lock']==r['repository_pins']['package-lock.json'])
    need(r['input_pins']['pods_lock']==r['repository_pins']['apps/mobile/ios/Podfile.lock'])
    a=r['android'];closed(a,'sha256 bytes entries native_libraries permissions prohibited_audio_model_resources build_kind')
    digest(a['sha256']);integer(a['bytes'],1);integer(a['entries'],1,50000)
    need(a['build_kind']=='ANDROID_RELEASE_VARIANT_NOT_DISTRIBUTION_APPROVAL' and a['prohibited_audio_model_resources']==[])
    names(a['permissions'],r'[A-Za-z0-9_.]+');need(a['permissions'])
    need(type(a['native_libraries']) is list and 0<len(a['native_libraries'])<=1000)
    paths=[]
    for lib in a['native_libraries']:
        closed(lib,'path bytes sha256 needed');safe_name(lib['path']);need(re.fullmatch(r'lib/[A-Za-z0-9_\-]+/[A-Za-z0-9_.+\-]+\.so',lib['path']))
        integer(lib['bytes'],4,256*1024*1024);digest(lib['sha256']);names(lib['needed'],r'[A-Za-z0-9_.+\-]+');paths.append(lib['path'])
    need(paths==sorted(set(paths)))
    i=r['ios'];closed(i,'tree_sha256 files bytes native_binaries privacy_declarations prohibited_audio_model_resources build_kind')
    digest(i['tree_sha256']);integer(i['files'],1,50000);integer(i['bytes'],1)
    need(i['build_kind']=='UNSIGNED_IOS_SIMULATOR_RELEASE_NOT_DEVICE_ARCHIVE' and i['prohibited_audio_model_resources']==[])
    need(type(i['native_binaries']) is list and 0<len(i['native_binaries'])<=1000)
    paths=[]
    for binary in i['native_binaries']:
        closed(binary,'path bytes sha256 linked_basenames');safe_name(binary['path']);integer(binary['bytes'],4,256*1024*1024);digest(binary['sha256']);names(binary['linked_basenames']);paths.append(binary['path'])
        need(all('/' not in n and '\\' not in n for n in binary['linked_basenames']))
    need(paths==sorted(set(paths)))
    need(type(i['privacy_declarations']) is list and 0<len(i['privacy_declarations'])<=1000)
    privacy_paths=[]
    for declaration in i['privacy_declarations']:
        closed(declaration,'path sha256 declared_tracking accessed_api_types collected_data_types');safe_name(declaration['path']);need(declaration['path'].endswith('PrivacyInfo.xcprivacy'));digest(declaration['sha256'])
        need(declaration['declared_tracking'] is None or type(declaration['declared_tracking']) is bool)
        names(declaration['accessed_api_types']);names(declaration['collected_data_types']);privacy_paths.append(declaration['path'])
    need(privacy_paths==sorted(set(privacy_paths)))
    need(type(r['maven']) is list and 0<len(r['maven'])<=1000)
    coordinates=[]
    for c in r['maven']:
        closed(c,'group artifact version artifact_sha256 cache_match poms license_review')
        for key in ('group','artifact','version'):need(re.fullmatch(r'[A-Za-z0-9_.+\-]+',c[key]))
        coordinates.append((c['group'],c['artifact'],c['version']))
        if c['artifact_sha256'] is None:need(c['cache_match']=='NOT_RECORDED')
        else:digest(c['artifact_sha256']);need(c['cache_match'] in ('VERIFIED','MISSING','MISMATCH'))
        need(c['license_review']=='REQUIRED' and type(c['poms']) is list and len(c['poms'])<=5)
        for pom in c['poms']:
            closed(pom,'sha256 licenses');digest(pom['sha256']);need(type(pom['licenses']) is list and len(pom['licenses'])<=20)
            for license in pom['licenses']:
                closed(license,'name url');text(license['name'])
                if license['url'] is not None:text(license['url'],512);need(license['url'].startswith(('https://','http://')))
    need(coordinates==sorted(set(coordinates)))
    need(type(r['npm_lock_only']) is list and 0<len(r['npm_lock_only'])<=10000)
    entries=[]
    for c in r['npm_lock_only']:
        closed(c,'lock_entry name version declared_license development_only workspace');safe_name(c['lock_entry']);text(c['name']);text(c['version']);entries.append(c['lock_entry'])
        need(re.fullmatch(r'(?:@[A-Za-z0-9_.\-]+/)?[A-Za-z0-9_.\-]+',c['name']))
        if c['declared_license'] is not None:text(c['declared_license'])
        need(type(c['development_only']) is bool and type(c['workspace']) is bool)
    need(entries==sorted(set(entries)))
    p=r['pods_lock_and_notices'];closed(p,'components notice_evidence');need(type(p['components']) is list and 0<len(p['components'])<=1000)
    pairs=[]
    for c in p['components']:
        closed(c,'name version');text(c['name']);text(c['version']);pairs.append((c['name'],c['version']))
    need(pairs==sorted(set(pairs)) and type(p['notice_evidence']) is list and 0<len(p['notice_evidence'])<=1000)
    for n in p['notice_evidence']:
        closed(n,'title bytes sha256');text(n['title']);integer(n['bytes'],1,2*1024*1024);digest(n['sha256'])
    return dict(android_native_libraries=len(a['native_libraries']),ios_native_binaries=len(i['native_binaries']),maven_metadata_entries=len(r['maven']),
        maven_verified=sum(c['cache_match']=='VERIFIED' for c in r['maven']),maven_without_digest=sum(c['cache_match']=='NOT_RECORDED' for c in r['maven']),
        maven_other_unverified=sum(c['cache_match'] in ('MISSING','MISMATCH') for c in r['maven']),maven_without_direct_license_declaration=sum(not any(p['licenses'] for p in c['poms']) for c in r['maven']),
        npm_lock_entries=len(r['npm_lock_only']),npm_undeclared_licenses=sum(c['declared_license'] is None for c in r['npm_lock_only']),pods_lock_entries=len(p['components']),notice_records=len(p['notice_evidence']),
        release_acceptance='BLOCKED',sbom_completeness='NOT_ESTABLISHED',network_privacy='NOT_ESTABLISHED',physical='NOT_RUN')


def read(path):
    need(path.stat().st_size<=4*1024*1024)
    def unique(pairs):
        result={}
        for key,value in pairs:need(key not in result);result[key]=value
        return result
    def reject(_):raise ValueError('nonfinite JSON')
    return json.loads(path.read_text(),object_pairs_hook=unique,parse_constant=reject)


def export(r,output):
    summary=validate(r);need(not output.exists());output.mkdir(parents=True)
    (output/'summary.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    rows=''.join('<tr><th>'+html.escape(key)+'</th><td>'+html.escape(str(value))+'</td></tr>' for key,value in summary.items())
    (output/'summary.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Normal build inventory</title><h1>Normal build artifact inventory</h1>'
        '<p>Android release variant and unsigned iOS simulator release. No device archive, signing, release approval, complete SBOM, redistribution opinion or runtime network/privacy certification.</p>'
        '<p>Maven records are co-observed AGP metadata, not a complete mapping of classes into the binary. NPM lock records include build/dev dependencies and are not proof of shipment. '
        'Pod lock entries include subspecs; notice hashes do not prove complete transitive license coverage. Missing digests and declarations remain unresolved. '
        'Resource checks cover packaged files with the configured audio/model extensions, not all possible embedded content or device stores.</p><table border="1">'+rows+'</table>'
        '<details><summary>Observed inventory</summary><pre>'+html.escape(json.dumps(r,indent=2,allow_nan=False))+'</pre></details></html>\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',type=Path,default=HERE/'observed.json');parser.add_argument('--output',type=Path);args=parser.parse_args();value=read(args.report)
    print(json.dumps(export(value,args.output) if args.output else validate(value),indent=2))
