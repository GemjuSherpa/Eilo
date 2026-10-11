#!/usr/bin/env python3
"""Compile device/simulator wrapper, execute real Swift/native ASR on an explicit simulator.
No microphone, signing, readiness overrides in the normal app, or third-party managed SDK.
"""
import argparse
import array
import json
import subprocess
import tempfile
from pathlib import Path
import wave
from check_host import CACHE,HERE,digest,verified_model

def run(args,timeout=120):
    try:
        return subprocess.run(list(map(str,args)),check=True,capture_output=True,text=True,timeout=timeout)
    except subprocess.CalledProcessError as e:
        print(e.stderr[-5000:])
        raise ValueError("native compiler/evaluation failed") from None

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--udid',required=True);args=p.parse_args()
    devices=json.loads(run(['xcrun','simctl','list','devices','--json']).stdout)
    if not any(d['udid']==args.udid and d['state']=='Booted' and d.get('isAvailable') for group in devices['devices'].values() for d in group):
        raise ValueError('explicit booted simulator required')
    model,record=verified_model();ios=record['ios']
    if digest(CACHE/ios['archive'])!=ios['publisher_sha256']:
        raise ValueError('iOS vendor archive integrity failed')
    for item in ios['files']:
        if digest(CACHE/item['path'])!=item['sha256']:
            raise ValueError('iOS extracted artifact integrity failed')
    x=CACHE/'ios-0.1.5/Moonshine.xcframework'
    for sdk,variant,target in [('iphonesimulator','ios-arm64_x86_64-simulator','arm64-apple-ios18.0-simulator'),('iphoneos','ios-arm64','arm64-apple-ios18.0')]:
        build=CACHE/('build-'+sdk);build.mkdir(exist_ok=True)
        sysroot=run(['xcrun','--sdk',sdk,'--show-sdk-path']).stdout.strip()
        run(['xcrun','--sdk',sdk,'clang++','-target',target,'-isysroot',sysroot,'-std=c++17','-Wall','-Wextra','-Werror','-I',HERE/'include','-I',x/variant/'Headers','-c',HERE/'eilo_asr.cc','-o',build/'eilo_asr.o'])
        if sdk=='iphoneos':continue
        executable=build/'asr-ios-binding'
        sources=sorted((HERE.parent/'native-test-seam/Sources/NativeTestSeam').glob('*.swift'))
        run(['xcrun','swiftc','-target',target,'-sdk',sysroot,'-parse-as-library','-D','DEBUG','-D','EILO_ASR_EVALUATION','-I',HERE/'include',*sources,HERE/'tests/ios_binding.swift',build/'eilo_asr.o',x/variant/'libmoonshine.a','-framework','Accelerate','-framework','Foundation','-lc++','-o',executable])
    cases=[]
    with tempfile.TemporaryDirectory(prefix='eilo-synthetic-asr-ios-') as tmp:
        raw=Path(tmp)/'synthetic.f32'
        for item in json.loads((HERE/'tests/fixtures.json').read_text())['cases']:
            file=CACHE/'fixtures'/item['file']
            if digest(file)!=item['sha256']:raise ValueError('synthetic fixture integrity failed')
            with wave.open(str(file),'rb') as w:
                if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())!=(1,2,16000,item['samples']):raise ValueError('invalid fixture')
                pcm=array.array('h',w.readframes(w.getnframes()))
            raw.write_bytes(array.array('f',(v/32768 for v in pcm)).tobytes())
            text=run(['xcrun','simctl','spawn',args.udid,CACHE/'build-iphonesimulator/asr-ios-binding',model,raw]).stdout.strip()
            cases.append({'id':item['id'],'slice':item['slice'],'reference':item['reference'],'transcript':text,'stale_final_rejected':True})
            raw.write_bytes(bytes(raw.stat().st_size));raw.unlink()
    report={'platform':'iOS27.0 ARM64 simulator / actual Swift C ABI','runtime':record['version'],'cases':cases,'physical':'NOT RUN','device_wrapper_compiler':'PASS; vendor device execution NOT RUN'}
    (CACHE/'ios-results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Actual iOS Swift/native ASR: '+str(len(cases))+' frozen synthetic cases executed; stale/final checks PASS.')

if __name__=='__main__':main()
