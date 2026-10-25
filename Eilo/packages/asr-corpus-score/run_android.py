#!/usr/bin/env python3
"""Explicit bounded cached Common Voice evaluation, with no physical audio or downloads."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import wave

HERE=Path(__file__).resolve().parent
SDK=HERE.parent/'asr-sdk-score-probe'
sys.path.insert(0,str(SDK))
from overlay import generate
sys.path.insert(0,str(HERE.parent/'dataset-evaluation'))
from benchmark import validate_manifest
from manifests import canonical_digest,safe_path
from confidence import unique
from diagnostics import SOURCES,score_response,summarize,need

REMOTE='/data/local/tmp/eilo-corpus-score'
PINS=('main.cpp','CMakeLists.txt','run_android.py','diagnostics.py')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def reject(_):raise ValueError('nonfinite JSON')
def read_json(path):
    need(path.stat().st_size<=4*1024*1024)
    return json.loads(path.read_text(),object_pairs_hook=unique,parse_constant=reject)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','cache','build','manifest','ndk','android-sdk','cmake','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--serial',choices=['emulator-5554'],required=True);args=parser.parse_args()
    for key,value in vars(args).items():
        if isinstance(value,Path):setattr(args,key,value.resolve())
    need(not args.output.exists() and not args.build.exists())
    manifest=read_json(args.manifest);validate_manifest(manifest,args.manifest.parent)
    need(manifest['kind']=='public_corpus' and manifest['dataset']=='common_voice' and 1<=len(manifest['cases'])<=30)
    need(all(c['task']=='asr' and c['split']=='test' for c in manifest['cases']))
    pins={name:sha(HERE/name) for name in PINS};sdk_pins={name:sha(SDK/name) for name in ['score_trace.h','overlay.py','overlay-expected.json']}
    provenance=read_json(HERE.parent/'asr-runtime/provenance.json');model=args.cache/provenance['model']['directory']
    for item in provenance['model']['files']:
        path=model/item['file'];need(path.is_file() and path.stat().st_size==item['bytes'] and sha(path)==item['local_sha256'])
    ort=args.cache/'android-0.1.5/jni/arm64-v8a/libonnxruntime.so';need(sha(ort)=='86e85022fc539963177e478c8e9a8a8219bc3b0d7515bf5297a62986dbc45e7a')
    need(args.ndk.name=='27.1.12297006');args.build.mkdir(parents=True)
    overlay_pins=generate(args.source,args.build/'overlay');need(overlay_pins==read_json(SDK/'overlay-expected.json'))
    def build(command):
        with (args.build/'build.log').open('a') as log:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=300)
    build([str(args.cmake),'-S',str(HERE),'-B',str(args.build),'-DCMAKE_TOOLCHAIN_FILE='+str(args.ndk/'build/cmake/android.toolchain.cmake'),'-DANDROID_ABI=arm64-v8a','-DANDROID_PLATFORM=android-26','-DSOURCE_ROOT='+str(args.source),'-DORT_LIBRARY='+str(ort),'-DOVERLAY='+str(args.build/'overlay'),'-DSCORE_HEADERS='+str(SDK)])
    build([str(args.cmake),'--build',str(args.build),'-j','2'])
    need(sum(p.stat().st_size for p in args.build.rglob('*') if p.is_file())<5*1024**3)
    adb=args.android_sdk/'platform-tools/adb'
    def run(*command,check=True):return subprocess.run([str(adb),'-s',args.serial,*command],capture_output=True,text=True,check=check,timeout=180)
    need(run('shell','getprop','ro.kernel.qemu').stdout.strip()=='1' and run('shell','getprop','ro.product.cpu.abi').stdout.strip()=='arm64-v8a' and run('shell','getprop','ro.build.version.sdk').stdout.strip()=='35')
    need(run('shell','test','-e',REMOTE,check=False).returncode==1)
    binary=args.build/'corpus-score-probe';cxx=args.ndk/'toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/lib/aarch64-linux-android/libc++_shared.so'
    rows=[];run('shell','mkdir',REMOTE)
    try:
        for path in (binary,ort,cxx,model):run('push',str(path),REMOTE+'/')
        run('shell','chmod','700',REMOTE+'/corpus-score-probe')
        for index,case in enumerate(manifest['cases']):
            path=safe_path(args.manifest.parent,case['path']);need(sha(path)==case['sha256'])
            with wave.open(str(path),'rb') as stream:
                need((stream.getframerate(),stream.getnchannels(),stream.getsampwidth(),stream.getnframes())==(16000,1,2,case['samples']))
                pcm=stream.readframes(case['samples'])
            values=struct.unpack('<'+'h'*(len(pcm)//2),pcm)
            input_path=args.build/'input.f32';input_path.write_bytes(struct.pack('<'+'f'*len(values),*(x/32768 for x in values)))
            run('push',str(input_path),REMOTE+'/input.f32')
            start=time.monotonic();response=run('shell',f'LD_LIBRARY_PATH={REMOTE} timeout 120 {REMOTE}/corpus-score-probe {REMOTE}/{model.name} {REMOTE}/input.f32',check=False);seconds=time.monotonic()-start
            if response.returncode:
                result=dict(schema_version=1,paths=[dict(source=s,status='UNAVAILABLE',reason='COLLECTOR_ERROR') for s in SOURCES])
            else:
                lines=[line for line in response.stdout.splitlines() if line.startswith('{')];need(len(lines)==1 and len(lines[0].encode())<=32768)
                result=json.loads(lines[0],object_pairs_hook=unique,parse_constant=reject)
            rows.append(score_response(case,result,seconds));del result,response
            (args.build/'progress.json').write_text(json.dumps({'status':'IN_PROGRESS','cases':rows},indent=2,allow_nan=False)+'\n')
            print('Scored corpus case',index+1,'of',len(manifest['cases']),flush=True)
        rejected=[]
        for name,raw in [('empty',b''),('unaligned',b'x'),('nan',struct.pack('<f',float('nan'))),('out_of_range',struct.pack('<f',2))]:
            input_path=args.build/'input.f32';input_path.write_bytes(raw);run('push',str(input_path),REMOTE+'/input.f32')
            response=run('shell',f'LD_LIBRARY_PATH={REMOTE} timeout 120 {REMOTE}/corpus-score-probe {REMOTE}/{model.name} {REMOTE}/input.f32',check=False)
            need(response.returncode!=0 and '{' not in response.stdout);rejected.append(name)
    finally:
        run('shell','rm','-rf',REMOTE);(args.build/'input.f32').unlink(missing_ok=True)
    need(pins=={name:sha(HERE/name) for name in PINS} and sdk_pins=={name:sha(SDK/name) for name in sdk_pins})
    sources=summarize(rows)
    report=dict(schema_version=1,purpose='CURATOR_TEST_SCORE_DIAGNOSTIC',status='DIAGNOSTIC_ONLY' if all(s['status']=='DIAGNOSTIC_ONLY' for s in sources) else 'INCOMPLETE_SCORES',dataset=manifest['dataset'],release=manifest['release'],cases_total=len(rows),
        partition='CURATOR_TEST',model_training_overlap='UNKNOWN',native_calibration='NOT_ESTABLISHED',threshold_authorization='NOT_GRANTED',production='NOT_ENABLED',physical='NOT_RUN',
        score='ARITHMETIC_MEAN_ACCEPTED_NON_EOS_TOKEN_PREBIAS_PROBABILITY',draft='SAME_UTTERANCE_GREEDY_HYPOTHESIS_NO_REFERENCE',normalization='nfkc-casefold-alnum-v1',
        platform='Android API35 ARM64 emulator',provenance=dict(manifest_sha256=canonical_digest(manifest),registry_sha256=sha(HERE.parent/'dataset-evaluation/registry.json'),
            runtime_sha256=sha(binary),ort_sha256=sha(ort),cxx_sha256=sha(cxx),model_bundle_sha256=canonical_digest(provenance['model']),model_provenance_sha256=sha(HERE.parent/'asr-runtime/provenance.json'),
            source_pins=pins,sdk_pins=sdk_pins,overlay_pins=overlay_pins,case_counts_sha256=canonical_digest(rows)),sources=sources,rejected_inputs=rejected)
    (args.build/'completed-private.json').write_text(json.dumps({'status':'COMPLETED','cases':rows},indent=2,allow_nan=False)+'\n')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as output:output.write(json.dumps(report,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':main()
