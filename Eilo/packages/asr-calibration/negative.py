"""Frozen direct-ASR negative controls; no claim of VAD/system false activation."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import wave
from calibrate import HERE,CORPUS,DATA,SDK,need,read,sha,canonical_digest,normalize,predict,SOURCES
from noise_pilot import model
from diagnostics import validate_response,REASONS

spec=importlib.util.spec_from_file_location('negative_native_runner',CORPUS/'run_android.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
GROUPS=('musan_weak_noise','digital_silence','uniform_noise')
FLAGS=dict(calibrator_refit='NOT_PERFORMED',threshold_fitting='NOT_PERFORMED',end_to_end_false_activation='NOT_MEASURED',
           vad='BYPASSED',native_calibration='NOT_ESTABLISHED',threshold_authorization='NOT_GRANTED',production='NOT_ENABLED',physical='NOT_RUN')


def policy():
    p=read(HERE/'negative-protocol.json')
    expected=dict(schema_version=1,purpose='DIRECT_ASR_NOISE_ONLY_DIAGNOSTIC',musan_cases=12,digital_silence_seconds=[1,5,10],
                  uniform_noise_seconds=3,uniform_noise_peak_pcm=[328,3277,9830],seed=20261029,cases_total=18,threshold=.85,
                  musan_labels='CORPUS_CATEGORY_WEAK_LABEL_NOT_VERIFIED_SPEECH_ABSENCE',synthetic_labels='NO_SPEECH_BY_CONSTRUCTION',
                  pairing='UNIFORM_NOISE_LEVELS_SHARE_ONE_DETERMINISTIC_WAVEFORM',unavailable='TEXT_OUTCOME_NOT_OBSERVABLE',**FLAGS)
    need(canonical_digest(p)==canonical_digest(expected))
    return p


def pins():
    paths=[HERE/n for n in ('negative.py','negative-protocol.json','calibrate.py','freeze.json','noise_pilot.py','calibration_report.py')]
    paths += [CORPUS/n for n in ('run_android.py','diagnostics.py','main.cpp','CMakeLists.txt')]
    paths += [SDK/n for n in ('overlay.py','score_trace.h','overlay-expected.json')]
    paths += [DATA/n for n in ('audio.py','benchmark.py','manifests.py')]
    return {str(p.relative_to(HERE.parent)):sha(p) for p in paths}


def committed(commit):
    import re
    need(type(commit) is str and re.fullmatch('[0-9a-f]{40}',commit))
    root=HERE.parents[2]
    subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],cwd=root,check=True,capture_output=True)
    for name in ('negative.py','negative-protocol.json'):
        need(subprocess.check_output(['git','show',commit+':Eilo/packages/asr-calibration/'+name],cwd=root)==(HERE/name).read_bytes())


def controls(manifest_path):
    p=policy();m=read(manifest_path);native.validate_manifest(m,manifest_path.parent)
    need(m['dataset']=='musan' and len(m['cases'])==p['musan_cases'])
    need(canonical_digest(m)==read(CORPUS/'noise-results/suite.json')['noise_manifest_sha256'])
    rows=[]
    for c in m['cases']:
        need(c['task']=='vad' and c['vad']==[] and c['slice']=='noise_only' and c['annotation_status']=='CORPUS_CATEGORY_WEAK_LABEL')
        path=native.safe_path(manifest_path.parent,c['path'])
        with wave.open(str(path),'rb') as stream:raw=stream.readframes(c['samples'])
        rows.append(dict(group=GROUPS[0],pcm=raw))
    for seconds in p['digital_silence_seconds']:
        rows.append(dict(group=GROUPS[1],pcm=b'\0\0'*(16000*seconds)))
    count=16000*p['uniform_noise_seconds'];blocks=[]
    for i in range(math.ceil(count*2/32)):
        blocks.append(hashlib.sha256(f"{p['seed']}:{i}".encode()).digest())
    base=struct.unpack('<'+'h'*count,b''.join(blocks)[:count*2])
    for peak in p['uniform_noise_peak_pcm']:
        raw=struct.pack('<'+'h'*count,*(int(x*peak/32768) for x in base))
        rows.append(dict(group=GROUPS[2],pcm=raw))
    need(len(rows)==p['cases_total']==18)
    for r in rows:need(0<len(r['pcm'])<=16000*30*2 and len(r['pcm'])%2==0)
    return rows,canonical_digest([dict(group=r['group'],samples=len(r['pcm'])//2,pcm_sha256=hashlib.sha256(r['pcm']).hexdigest()) for r in rows]),canonical_digest(m)


def observation(group,value,models):
    need(group in GROUPS);rows=[]
    for path in validate_response(value):
        if path['status']=='UNAVAILABLE':rows.append(dict(source=path['source'],status='UNAVAILABLE',reason=path['reason']));continue
        score=path['confidence'];mapped=predict(models[path['source']],score);m=models[path['source']]
        rows.append(dict(source=path['source'],status='AVAILABLE',word_bearing=bool(normalize(path['transcript'])),
                         raw=score,mapped=mapped,outside=score<m['minimum'] or score>m['maximum']))
    return dict(group=group,paths=rows)


def summarize(rows):
    need(type(rows) is list and len(rows)==18 and Counter(r['group'] for r in rows)==dict(zip(GROUPS,(12,3,3))))
    result=[]
    for group in GROUPS:
        subset=[r for r in rows if r['group']==group]
        for index,source in enumerate(SOURCES):
            available=[];reasons=Counter()
            for row in subset:
                need(set(row)=={'group','paths'} and len(row['paths'])==2)
                path=row['paths'][index];need(path['source']==source)
                if path['status']=='UNAVAILABLE':
                    need(set(path)=={'source','status','reason'} and path['reason'] in REASONS);reasons[path['reason']]+=1;continue
                need(set(path)=={'source','status','word_bearing','raw','mapped','outside'} and path['status']=='AVAILABLE')
                need(type(path['word_bearing']) is bool and type(path['outside']) is bool)
                for k in ('raw','mapped'):need(type(path[k]) in (int,float) and math.isfinite(path[k]) and 0<=path[k]<=1)
                available.append(path)
            total=len(subset);words=sum(r['word_bearing'] for r in available)
            result.append(dict(group=group,source=source,cases=total,available=len(available),unavailable=total-len(available),
                               unavailable_reasons=dict(sorted(reasons.items())),observed_word_bearing=words,observed_word_bearing_fraction_all_cases=words/total,
                               raw_accepted_word_bearing=sum(r['word_bearing'] and r['raw']>=.85 for r in available),
                               mapped_accepted_word_bearing=sum(r['word_bearing'] and r['mapped']>=.85 for r in available),
                               outside_development_range=sum(r['outside'] for r in available)))
    return result


def main():
    a=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','private-model','source','cache','build','ndk','android-sdk','cmake','output'):a.add_argument('--'+name,type=Path,required=True)
    a.add_argument('--protocol-commit',required=True);a.add_argument('--serial',choices=['emulator-5554'],required=True);args=a.parse_args()
    for k,v in vars(args).items():
        if isinstance(v,Path):setattr(args,k,v.resolve())
    committed(args.protocol_commit);before=pins();models=model(args.private_model);model_hash=sha(args.private_model)
    need(not args.build.exists() and not args.output.exists());inputs,input_hash,manifest_hash=controls(args.manifest)
    provenance=read(HERE.parent/'asr-runtime/provenance.json');bundle=args.cache/provenance['model']['directory']
    for item in provenance['model']['files']:
        path=bundle/item['file'];need(path.is_file() and path.stat().st_size==item['bytes'] and sha(path)==item['local_sha256'])
    ort=args.cache/'android-0.1.5/jni/arm64-v8a/libonnxruntime.so';need(sha(ort)=='86e85022fc539963177e478c8e9a8a8219bc3b0d7515bf5297a62986dbc45e7a')
    need(args.ndk.name=='27.1.12297006');args.build.mkdir(parents=True)
    overlay=native.generate(args.source,args.build/'overlay');need(overlay==read(SDK/'overlay-expected.json'))
    def build(command):
        with (args.build/'build.log').open('a') as log:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=300)
    build([str(args.cmake),'-S',str(CORPUS),'-B',str(args.build),'-DCMAKE_TOOLCHAIN_FILE='+str(args.ndk/'build/cmake/android.toolchain.cmake'),'-DANDROID_ABI=arm64-v8a','-DANDROID_PLATFORM=android-26','-DSOURCE_ROOT='+str(args.source),'-DORT_LIBRARY='+str(ort),'-DOVERLAY='+str(args.build/'overlay'),'-DSCORE_HEADERS='+str(SDK)])
    build([str(args.cmake),'--build',str(args.build),'-j','2'])
    need(sum(p.stat().st_size for p in args.build.rglob('*') if p.is_file())<5*1024**3)
    adb=args.android_sdk/'platform-tools/adb';remote='/data/local/tmp/eilo-negative-score'
    def run(*command,check=True):return subprocess.run([str(adb),'-s',args.serial,*command],capture_output=True,text=True,check=check,timeout=180)
    need(run('shell','getprop','ro.kernel.qemu').stdout.strip()=='1' and run('shell','getprop','ro.product.cpu.abi').stdout.strip()=='arm64-v8a' and run('shell','getprop','ro.build.version.sdk').stdout.strip()=='35')
    need(run('shell','test','-e',remote,check=False).returncode==1)
    binary=args.build/'corpus-score-probe';cxx=args.ndk/'toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/lib/aarch64-linux-android/libc++_shared.so'
    rows=[];rejected=[];scratch=args.build/'input.f32';run('shell','mkdir',remote)
    try:
        for path in (binary,ort,cxx,bundle):run('push',str(path),remote+'/')
        run('shell','chmod','700',remote+'/corpus-score-probe')
        def invoke(raw):
            scratch.write_bytes(raw);run('push',str(scratch),remote+'/input.f32')
            return run('shell',f'LD_LIBRARY_PATH={remote} timeout 120 {remote}/corpus-score-probe {remote}/{bundle.name} {remote}/input.f32',check=False)
        for i,control in enumerate(inputs):
            values=struct.unpack('<'+'h'*(len(control['pcm'])//2),control['pcm'])
            response=invoke(struct.pack('<'+'f'*len(values),*(x/32768 for x in values)))
            if response.returncode:value=dict(schema_version=1,paths=[dict(source=s,status='UNAVAILABLE',reason='COLLECTOR_ERROR') for s in SOURCES])
            else:
                lines=[line for line in response.stdout.splitlines() if line.startswith('{')];need(len(lines)==1 and len(lines[0].encode())<=32768)
                value=json.loads(lines[0],object_pairs_hook=native.unique,parse_constant=native.reject)
            rows.append(observation(control['group'],value,models));del response,value
            (args.build/'progress-private.json').write_text(json.dumps(dict(status='IN_PROGRESS',rows=rows),indent=2)+'\n')
            print('Negative control',i+1,'of',len(inputs),flush=True)
        for name,raw in [('empty',b''),('unaligned',b'x'),('nan',struct.pack('<f',float('nan'))),('out_of_range',struct.pack('<f',2))]:
            response=invoke(raw);need(response.returncode!=0 and '{' not in response.stdout);rejected.append(name)
    finally:
        run('shell','rm','-rf',remote);scratch.unlink(missing_ok=True)
    need(before==pins() and sha(args.private_model)==model_hash)
    _,final_inputs,final_manifest=controls(args.manifest);need(final_inputs==input_hash and final_manifest==manifest_hash)
    public=dict(schema_version=1,purpose=policy()['purpose'],protocol_commit=args.protocol_commit,source_pins=before,
                controls_sha256=input_hash,musan_manifest_sha256=manifest_hash,private_counts_sha256=canonical_digest(rows),
                private_model_sha256=model_hash,model_bundle_sha256=canonical_digest(provenance['model']),model_provenance_sha256=sha(HERE.parent/'asr-runtime/provenance.json'),
                runtime_sha256=sha(binary),ort_sha256=sha(ort),cxx_sha256=sha(cxx),overlay_pins=overlay,groups=summarize(rows),rejected_inputs=rejected,**FLAGS)
    from negative_report import validate
    validate(public)
    (args.build/'completed-private.json').write_text(json.dumps(dict(status='COMPLETED',rows=rows),indent=2)+'\n')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as stream:stream.write(json.dumps(public,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
