"""Validate opt-in app framework packaging without native caches or runtime activation."""
import argparse
import html
import json
from pathlib import Path
from app_framework import HERE, FLAGS, pins
from framework import read, need


def closed(value,keys):need(type(value) is dict and set(value)==set(keys.split()))


def digest(value):need(type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value))


def validate(r):
    closed(r,'schema_version purpose source_pins dependency_archives app cold_launches dwell_seconds release_gate_probe swift_runtime_evaluation_flags framework project '+' '.join(FLAGS))
    need(type(r['schema_version']) is int and r['schema_version']==1 and r['purpose']=='OPT_IN_UNSIGNED_SIMULATOR_APP_FRAMEWORK')
    need(r['source_pins']==pins())
    for k,v in FLAGS.items():need(r[k]==v)
    need(r['project']=='TEMPORARY_COPY_ONLY' and r['swift_runtime_evaluation_flags']=='ABSENT')
    need(r['release_gate_probe']=='EXECUTED_UNAVAILABLE_ASR_AND_MISSING_MODELS_NO_CAPTURE')
    need(type(r['cold_launches']) is int and r['cold_launches']==3 and type(r['dwell_seconds']) is int and r['dwell_seconds']==10)
    expected=read(HERE/'framework-results.json')['frameworks']['iphonesimulator'];need(r['framework']==expected)
    app=r['app'];closed(app,'binary_sha256 tree_sha256 files framework_sha256 code_signature platform configuration architecture rpaths required_framework_load packaged_model_audio_extensions')
    for key in ('binary_sha256','tree_sha256','framework_sha256'):digest(app[key])
    need(app['framework_sha256']==expected['sha256'] and app['code_signature'] in ('UNSIGNED','TOOLCHAIN_AD_HOC'))
    need(app['platform']=='iPhoneSimulator' and app['configuration']=='Release' and app['architecture']=='arm64')
    need(app['required_framework_load'] is True and app['packaged_model_audio_extensions']=='NONE_OBSERVED')
    need(type(app['files']) is int and 1<=app['files']<=10000)
    paths=app['rpaths'];need(type(paths) is list and '@executable_path/Frameworks' in paths and all(p in ('/usr/lib/swift','@executable_path/Frameworks','@loader_path/Frameworks') for p in paths))
    archives=r['dependency_archives'];names=['ReactNativeCore-artifacts/reactnative-core-0.87.1-release.tar.gz','ReactNativeDependencies-artifacts/reactnative-dependencies-0.87.1-release.tar.gz','hermes-engine-artifacts/hermes-ios-250829098.0.17-release.tar.gz']
    need(type(archives) is list and len(archives)==3 and [v['name'] for v in archives]==names)
    for row in archives:
        closed(row,'name bytes sha256');digest(row['sha256']);need(type(row['bytes']) is int and 0<row['bytes']<1024**3)
    return dict(purpose=r['purpose'],app=app,cold_launches=3,dwell_seconds=10,release_gate_probe=r['release_gate_probe'],project=r['project'],**FLAGS)


def export(r,out):
    result=validate(r);need(not out.exists());out.mkdir(parents=True)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'summary.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Unsigned app framework embedding</title><h1>Unsigned app framework embedding</h1><p>Opt-in simulator Release build from a temporary project copy. Three process launch checks and a separate Release guard probe. No model load, microphone, ordinary voice, device, signing or distribution acceptance.</p><pre>'+html.escape(json.dumps(result,indent=2))+'</pre></html>\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,default=HERE/'app-framework-results.json');p.add_argument('--output',type=Path)
    a=p.parse_args();r=read(a.report);print(json.dumps(export(r,a.output) if a.output else validate(r),indent=2))
