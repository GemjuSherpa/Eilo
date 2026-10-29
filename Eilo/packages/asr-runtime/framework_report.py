"""Validate unsigned framework observations without granting signing or release approval."""
import argparse
import html
import hashlib
import plistlib
import json
from pathlib import Path
import re
from framework import HERE,PACKAGES,FLAGS,EXPORTS,INSTALL,pins,read,sha,need,metadata


def closed(value,keys):need(type(value) is dict and set(value)==set(keys.split()))


def digest(value):need(type(value) is str and re.fullmatch('[0-9a-f]{64}',value))


def validate(r):
    closed(r,'schema_version purpose source_pins asr_provenance_sha256 llm_provenance_sha256 frameworks xcframework relocation framework_client_sha256 client_rpaths fixture_sha256 execution llm_static_archives compiler '+' '.join(FLAGS))
    need(type(r['schema_version']) is int and r['schema_version']==1 and r['purpose']=='UNSIGNED_IOS_ASR_FRAMEWORK_EVALUATION' and r['source_pins']==pins())
    for k,v in FLAGS.items():need(r[k]==v)
    need(r['asr_provenance_sha256']==sha(HERE/'provenance.json') and r['llm_provenance_sha256']==sha(PACKAGES/'llm-runtime/provenance.json'))
    need(r['xcframework']=='TWO_ARM64_SLICES' and r['relocation']=='EXECUTED_WITH_ORIGINAL_CLIENT_DIRECTORY_ABSENT')
    need(type(r['client_rpaths']) is list and len(r['client_rpaths'])==2 and set(r['client_rpaths'])=={'/usr/lib/swift','@executable_path/Frameworks'})
    digest(r['framework_client_sha256']);need(type(r['compiler']) is str and r['compiler'].startswith('Apple clang version ') and len(r['compiler'])<300 and '/' not in r['compiler'])
    fixture=next(x for x in read(HERE/'tests/fixtures.json')['cases'] if x['id']=='question');need(r['fixture_sha256']==fixture['sha256'])
    frameworks=r['frameworks'];need(type(frameworks) is dict and set(frameworks)=={'iphoneos','iphonesimulator'})
    for sdk,row in frameworks.items():
        closed(row,'architecture platform minimum_os install_name exports namespace code_signature dependencies sha256 bytes header_sha256 module_sha256 info_sha256')
        need(row['architecture']=='arm64' and row['platform']==('IOS' if sdk=='iphoneos' else 'IOSSIMULATOR') and row['minimum_os']=='18.0')
        need(row['install_name']==INSTALL and row['exports']==EXPORTS and row['namespace']=='TWOLEVEL' and row['code_signature'] in ('UNSIGNED','TOOLCHAIN_AD_HOC'))
        need(type(row['bytes']) is int and 0<row['bytes']<1024**3)
        need(type(row['dependencies']) is list and 1<=len(row['dependencies'])<=32 and INSTALL in row['dependencies'])
        need(all(type(d) is str and (d==INSTALL or d.startswith('/System/Library/Frameworks/') or d.startswith('/usr/lib/')) for d in row['dependencies']))
        for k in ('sha256','header_sha256','module_sha256','info_sha256'):digest(row[k])
        need(row['header_sha256']==sha(HERE/'include/eilo_asr.h'))
        need(row['module_sha256']==hashlib.sha256(b'framework module CEiloAsr { umbrella header "eilo_asr.h" export * }\n').hexdigest())
        need(row['info_sha256']==hashlib.sha256(plistlib.dumps(metadata(sdk))).hexdigest())
    execution=r['execution'];closed(execution,'framework_asr_final duplicate_final_rejected stale_final_rejected linked_llm_unloaded_gate_rejected microphone llm_generation physical')
    for k in ('framework_asr_final','duplicate_final_rejected','stale_final_rejected','linked_llm_unloaded_gate_rejected'):need(execution[k] is True)
    need(execution['microphone']=='NOT_OPENED' and execution['llm_generation']=='NOT_RUN' and execution['physical']=='NOT_RUN')
    libs=r['llm_static_archives'];need(type(libs) is list and [v['name'] for v in libs]==['libllama.a','libggml.a','libggml-cpu.a','libggml-base.a'])
    for row in libs:closed(row,'name sha256');digest(row['sha256'])
    return dict(frameworks=[dict(sdk=sdk,platform=row['platform'],architecture=row['architecture'],bytes=row['bytes'],exports=len(row['exports']),install_name=row['install_name']) for sdk,row in frameworks.items()],
                relocation=r['relocation'],execution=execution,**FLAGS)


def export(r,out):
    result=validate(r);need(not out.exists());out.mkdir(parents=True)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    body=html.escape(json.dumps(result,indent=2))
    (out/'summary.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Unsigned ASR framework evaluation</title><h1>Unsigned ASR framework evaluation</h1>'
        '<p>Device and simulator ARM64 framework builds; relocated simulator ASR final/cancellation with a linked, unloaded LLM. No production embedding/signing, model generation, physical or release acceptance.</p><pre>'+body+'</pre></html>\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,default=HERE/'framework-results.json');p.add_argument('--output',type=Path)
    a=p.parse_args();r=read(a.report);print(json.dumps(export(r,a.output) if a.output else validate(r),indent=2))
