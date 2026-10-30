"""Previously exposed Common Voice/MUSAN iOS source diagnostics; no fitting or new data."""
import argparse
import hashlib
import math
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import time
import wave

HERE=Path(__file__).resolve().parent;PACKAGES=HERE.parent;SDK=PACKAGES/'asr-sdk-score-probe';CORPUS=PACKAGES/'asr-corpus-score'
sys.path.insert(0,str(SDK))
from check_ios import f
sys.path.insert(0,str(CORPUS))
import run_android as native
from diagnostics import SOURCES,REASONS,validate_response,score_response,summarize
from manifests import canonical_digest,safe_path
# Historical modules share a generic report.py name. Bind only this import,
# then restore the caller's module namespace; old packages remain untouched.
legacy_metrics=f.module('ios_reference_legacy_metrics',CORPUS/'report.py')
_previous_report=sys.modules.get('report')
sys.modules['report']=legacy_metrics
try:noise_suite=f.module('ios_reference_noise_pairing',CORPUS/'noise_suite.py')
finally:
    if _previous_report is None:sys.modules.pop('report',None)
    else:sys.modules['report']=_previous_report
from benchmark import normalize
GROUPS=('musan_weak_noise','digital_silence','uniform_noise')


def negative_controls(manifest):
    # Exact original PCM recipe, checked against the prior aggregate fingerprint.
    p=f.read(PACKAGES/'asr-calibration/negative-protocol.json');m=f.read(manifest)
    native.validate_manifest(m,manifest.parent);f.need(m['dataset']=='musan' and len(m['cases'])==12)
    rows=[]
    for c in m['cases']:
        f.need(c['task']=='vad' and c['vad']==[] and c['annotation_status']=='CORPUS_CATEGORY_WEAK_LABEL')
        with wave.open(str(safe_path(manifest.parent,c['path'])),'rb') as stream:pcm=stream.readframes(c['samples'])
        rows.append(dict(group=GROUPS[0],pcm=pcm))
    for seconds in p['digital_silence_seconds']:rows.append(dict(group=GROUPS[1],pcm=b'\0\0'*(16000*seconds)))
    count=16000*p['uniform_noise_seconds']
    blocks=[hashlib.sha256(f"{p['seed']}:{i}".encode()).digest() for i in range(math.ceil(count*2/32))]
    base=struct.unpack('<'+'h'*count,b''.join(blocks)[:count*2])
    for peak in p['uniform_noise_peak_pcm']:
        rows.append(dict(group=GROUPS[2],pcm=struct.pack('<'+'h'*count,*(int(x*peak/32768) for x in base))))
    fingerprint=canonical_digest([dict(group=r['group'],samples=len(r['pcm'])//2,pcm_sha256=hashlib.sha256(r['pcm']).hexdigest()) for r in rows])
    prior=f.read(PACKAGES/'asr-calibration/negative-results.json');f.need(fingerprint==prior['controls_sha256'] and canonical_digest(m)==prior['musan_manifest_sha256'])
    return rows,fingerprint,canonical_digest(m)

DATASETS=[('exposed_original','cv-frozen-native/manifest.json'),('exposed_development','cv-fresh-split-v2/dev/manifest.json'),
    ('exposed_prior_test','cv-fresh-split-v2/test/manifest.json'),('exposed_audit_test','cv-calibration-test-v2/test/manifest.json'),
    ('correlated_noise','calibrator-noise-v1/manifest.json'),('musan_controls','musan-frozen/manifest.json')]
FLAGS=dict(data_status='PREVIOUSLY_EXPOSED_NOT_HELD_OUT',calibrator_refit='NOT_PERFORMED',threshold_fitting='NOT_PERFORMED',
    calibration='NOT_ESTABLISHED',threshold='NOT_GRANTED',calibration_transfer='NOT_AUTHORIZED',training_overlap='UNKNOWN',
    physical='NOT_RUN',production='NOT_ENABLED',microphone='NOT_OPENED',speech='NOT_STARTED',llm='NOT_RUN',
    release='HOLD',persistent_memory='DISABLED',vad='BYPASSED',end_to_end_false_activation='NOT_MEASURED',
    negative_labels='MUSAN_WEAK_LABELS_SYNTHETIC_NO_SPEECH_ONLY',noise_pairing='SAME_30_EXPOSED_AUDIT_PARENTS_CORRELATED')


def inputs(root):
    manifests={};inventory=[]
    for name,rel in DATASETS:
        path=root/rel;m=f.read(path);native.validate_manifest(m,path.parent)
        count=12 if name=='musan_controls' else 90 if name=='correlated_noise' else 30
        f.need(len(m['cases'])==count);manifests[name]=(m,path.parent)
        inventory.append(dict(name=name,path=rel,canonical_sha256=canonical_digest(m),cases=count))
    groups=noise_suite.validate_pairing(manifests['exposed_audit_test'][0],manifests['correlated_noise'][0],manifests['musan_controls'][0])
    ids=[c['id'] for name,_ in DATASETS[:4] for c in manifests[name][0]['cases']];f.need(len(ids)==len(set(ids))==120)
    controls,control_hash,musan_hash=negative_controls(root/'musan-frozen/manifest.json')
    return manifests,groups,controls,inventory,control_hash,musan_hash


def pins():
    paths={HERE/n for n in ('replay.py','CMakeLists.txt','protocol.json')}
    paths.update(SDK/n for n in ('check_ios.py','ios-results.json','ios-math-results.json','score_trace.h','overlay.py','overlay-expected.json','report.py','check_android.py'))
    paths.update(CORPUS/n for n in ('main.cpp','run_android.py','diagnostics.py','report.py','noise_suite.py'))
    paths.update(PACKAGES/'asr-runtime'/n for n in ('framework.py','provenance.json','tests/fixtures.json'))
    paths.update(PACKAGES/'asr-confidence-probe'/n for n in ('source-manifest.json','SOURCE_REVIEW.md'))
    paths.update(PACKAGES/'dataset-evaluation'/n for n in ('audio.py','benchmark.py','manifests.py','confidence.py','noise.py'))
    prior=f.read(PACKAGES/'asr-calibration/negative-results.json')
    paths.update(PACKAGES/p for p in prior['source_pins']);paths.add(PACKAGES/'asr-calibration/negative-results.json')
    return [dict(path=str(p.relative_to(PACKAGES)),sha256=f.sha(p)) for p in sorted(paths)]


def policy():
    p=f.read(HERE/'protocol.json');f.need(type(p) is dict and set(p)=={'schema_version','purpose','manifests','negative_controls_sha256','musan_manifest_sha256','clean_cases','noise_cases','negative_cases','runtime','diagnostic_cutoff',*FLAGS})
    f.need(type(p['schema_version']) is int and p['schema_version']==1 and p['purpose']=='IOS_EXPOSED_REFERENCE_NOISE_DIAGNOSTIC')
    f.need(all(type(p[k]) is int and p[k]==v for k,v in [('clean_cases',120),('noise_cases',90),('negative_cases',18)]))
    f.need(p['runtime']=='APPROVED_VENDOR_PRELINKED_ORT_1_23_2' and type(p['diagnostic_cutoff']) is float and p['diagnostic_cutoff']==.85)
    for k,v in FLAGS.items():f.need(p[k]==v)
    for row,(name,path) in zip(p['manifests'],DATASETS):
        f.need(set(row)=={'name','path','canonical_sha256','cases'} and row['name']==name and row['path']==path)
        f.need(type(row['cases']) is int and row['cases']==(12 if name=='musan_controls' else 90 if name=='correlated_noise' else 30))
        f.need(type(row['canonical_sha256']) is str and re.fullmatch('[0-9a-f]{64}',row['canonical_sha256']))
    f.need(len(p['manifests'])==6)
    prior=f.read(PACKAGES/'asr-calibration/negative-results.json')
    f.need(p['negative_controls_sha256']==prior['controls_sha256'] and p['musan_manifest_sha256']==prior['musan_manifest_sha256'])
    return p


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('datasets','source','asr-cache','cmake','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--udid',required=True);p.add_argument('--protocol-commit',required=True);a=p.parse_args()
    a.output=a.output.resolve();a.source=a.source.resolve();a.asr_cache=a.asr_cache.resolve();a.datasets=a.datasets.resolve()
    frozen=policy();before=pins();f.need(not a.output.exists())
    f.need(re.fullmatch('[0-9a-f]{40}',a.protocol_commit))
    repo=PACKAGES.parents[1];subprocess.run(['git','merge-base','--is-ancestor',a.protocol_commit,'HEAD'],cwd=repo,check=True,capture_output=True)
    for name in ('replay.py','CMakeLists.txt','protocol.json'):
        f.need(subprocess.check_output(['git','show',a.protocol_commit+':Eilo/packages/asr-ios-corpus/'+name],cwd=repo)==(HERE/name).read_bytes())
    checker=f.module('ios_reference_source',SDK/'check_android.py');checker.verify_source(a.source)
    model,record=f.verify_asr(a.asr_cache)
    manifests,noise_groups,controls,inventory,control_hash,musan_hash=inputs(a.datasets)
    f.need(inventory==frozen['manifests'] and control_hash==frozen['negative_controls_sha256'] and musan_hash==frozen['musan_manifest_sha256'])
    devices=json.loads(f.run(['xcrun','simctl','list','devices','booted','--json']))['devices']
    f.need(any(d['udid']==a.udid and d['state']=='Booted' and d.get('isAvailable') for ds in devices.values() for d in ds))
    out=a.output;out.mkdir(parents=True)
    vendor=a.asr_cache/'ios-0.1.5/Moonshine.xcframework/ios-arm64_x86_64-simulator/libmoonshine.a'
    thin=out/'vendor-arm64.a';f.run(['xcrun','lipo',vendor,'-thin','arm64','-output',thin]);ort=out/'prelinked_objects.o'
    with ort.open('wb') as stream:subprocess.run(['xcrun','ar','-p',str(thin),'prelinked_objects.o'],stdout=stream,check=True,timeout=60)
    runtime=f.read(SDK/'ios-results.json');f.need(f.sha(ort)==runtime['ort_binary_sha256'] and runtime['ort_version']=='1.23.2')
    overlay=f.module('ios_reference_overlay',SDK/'overlay.py').generate(a.source,out/'overlay');f.need(overlay==f.read(SDK/'overlay-expected.json'))
    sdk=f.run(['xcrun','--sdk','iphonesimulator','--show-sdk-path']).strip();build=out/'build'
    command=[a.cmake,'-S',HERE,'-B',build,'-DCMAKE_SYSTEM_NAME=iOS','-DCMAKE_OSX_SYSROOT='+sdk,'-DCMAKE_OSX_ARCHITECTURES=arm64',
        '-DCMAKE_OSX_DEPLOYMENT_TARGET=18.0','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY','-DCMAKE_SKIP_RPATH=ON',
        '-DSOURCE_ROOT='+str(a.source),'-DOVERLAY='+str(out/'overlay'),'-DORT_LIBRARY='+str(ort)]
    with (out/'build.log').open('w') as log:
        subprocess.run(list(map(str,command)),stdout=log,stderr=log,check=True,timeout=180)
        subprocess.run(list(map(str,[a.cmake,'--build',build,'-j','2'])),stdout=log,stderr=log,check=True,timeout=600)
    original=build/'ios-corpus-score';binary=out/'relocated/ios-corpus-score';binary.parent.mkdir();original.rename(binary);f.need(not original.exists())
    f.need(f.run(['xcrun','lipo','-archs',binary]).strip()=='arm64')
    target=f.run(['xcrun','vtool','-show-build',binary]);f.need(re.search(r'platform\s+IOSSIMULATOR\b',target) and re.search(r'minos\s+18\.0\b',target))
    deps=[line.strip().split(' (')[0] for line in f.run(['xcrun','otool','-L',binary]).splitlines()[1:]];f.need(all(x.startswith(('/System/Library/Frameworks/','/usr/lib/')) for x in deps))
    f.need(not re.findall(r'cmd LC_RPATH\s+cmdsize \d+\s+path (.*?) \(offset \d+\)',f.run(['xcrun','otool','-l',binary])))
    clean=[];noisy=[];negative_rows=[];private=[];errors=0
    with tempfile.TemporaryDirectory(prefix='eilo-ios-reference-') as folder:
        raw=Path(folder)/'input.f32'
        def invoke(data):
            raw.write_bytes(data);start=time.monotonic()
            result=subprocess.run(list(map(str,['xcrun','simctl','spawn',a.udid,binary,model,raw])),capture_output=True,text=True,timeout=180)
            return result,time.monotonic()-start
        def decoded(result):
            lines=[s for s in result.stdout.splitlines() if s.startswith('{')];f.need(len(lines)==1);return json.loads(lines[0])
        def floats(pcm):
            values=struct.unpack('<'+'h'*(len(pcm)//2),pcm);return struct.pack('<'+'f'*len(values),*(x/32768 for x in values))
        def audio(case,root):
            path=safe_path(root,case['path'])
            with wave.open(str(path),'rb') as stream:return floats(stream.readframes(case['samples']))
        fixture=f.read(PACKAGES/'asr-runtime/tests/fixtures.json')['cases'][0];path=a.asr_cache/'fixtures'/fixture['file'];f.need(f.sha(path)==fixture['sha256'])
        with wave.open(str(path),'rb') as stream:smoke=invoke(floats(stream.readframes(stream.getnframes())))[0]
        f.need(smoke.returncode==0);smoke_value=decoded(smoke);f.need(all(x['status']=='AVAILABLE' for x in validate_response(smoke_value)))
        def value_for(data):
            nonlocal errors
            result,elapsed=invoke(data)
            if result.returncode:
                errors+=1;value=dict(schema_version=1,paths=[dict(source=s,status='UNAVAILABLE',reason='COLLECTOR_ERROR') for s in SOURCES])
            else:value=decoded(result)
            validate_response(value);return value,elapsed
        def score_group(name,cases,root):
            rows=[]
            for case in cases:
                value,elapsed=value_for(audio(case,root));rows.append(score_response(case,value,elapsed));del value
            private.append(dict(group=name,rows=rows));print('Collected iOS group:',name,flush=True)
            return dict(group=name,reports=[dict(r,scope='PREVIOUSLY_EXPOSED_DIAGNOSTIC_ONLY') for r in summarize(rows)])
        for name,_ in DATASETS[:4]:clean.append(score_group(name,*[manifests[name][0]['cases'],manifests[name][1]]))
        for snr in (20,10,0):noisy.append(score_group('snr_'+str(snr),noise_groups[snr],manifests['correlated_noise'][1]))
        for control in controls:
            value,_=value_for(floats(control['pcm']));paths=[]
            for path in validate_response(value):
                if path['status']=='UNAVAILABLE':paths.append(dict(source=path['source'],status='UNAVAILABLE',reason=path['reason']))
                else:paths.append(dict(source=path['source'],status='AVAILABLE',word_bearing=bool(normalize(path['transcript'])),raw=path['confidence']))
            negative_rows.append(dict(group=control['group'],paths=paths));del value
        private.append(dict(group='negative_controls',rows=negative_rows))
        rejected=[]
        for name,data in [('empty',b''),('unaligned',b'x'),('nan',struct.pack('<f',float('nan'))),('out_of_range',struct.pack('<f',2))]:
            result,_=invoke(data);f.need(result.returncode!=0 and not any(x.startswith('{') for x in result.stdout.splitlines()));rejected.append(name)
        raw.write_bytes(bytes(raw.stat().st_size));raw.unlink()
    neg=[]
    for group in GROUPS:
        values=[r for r in negative_rows if r['group']==group]
        for index,source in enumerate(SOURCES):
            available=[r['paths'][index] for r in values if r['paths'][index]['status']=='AVAILABLE'];reasons=Counter(r['paths'][index]['reason'] for r in values if r['paths'][index]['status']=='UNAVAILABLE')
            neg.append(dict(group=group,source=source,cases=len(values),available=len(available),unavailable=len(values)-len(available),unavailable_reasons=dict(sorted(reasons.items())),
                observed_word_bearing=sum(r['word_bearing'] for r in available),raw_0_85_word_bearing=sum(r['word_bearing'] and r['raw']>=.85 for r in available)))
    private_path=out/'private-counts.json';private_path.write_text(json.dumps(private,indent=2)+'\n')
    checker.verify_source(a.source);f.verify_asr(a.asr_cache);f.need(before==pins() and inventory==inputs(a.datasets)[3])
    f.need(sum(p.stat().st_size for p in out.rglob('*') if p.is_file())<5*1024**3)
    result=dict(schema_version=1,purpose='IOS_EXPOSED_REFERENCE_NOISE_DIAGNOSTIC',protocol_commit=a.protocol_commit,source_pins=before,
        protocol_sha256=f.sha(HERE/'protocol.json'),runtime_object_sha256=f.sha(ort),model_provenance_sha256=f.sha(PACKAGES/'asr-runtime/provenance.json'),
        binary_sha256=f.sha(binary),private_counts_sha256=f.sha(private_path),smoke='TWO_AVAILABLE_SCORE_PATHS',relocation='ORIGINAL_BINARY_ABSENT_NO_CUSTOM_DYNAMIC_DEPENDENCY_OR_RPATH',
        clean=clean,noise=noisy,negative=neg,collector_errors=errors,rejected_inputs=rejected,**FLAGS)
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print('Previously exposed iOS reference/noise collection completed; no confidence fitting or qualification.')


if __name__=='__main__':main()
