#!/usr/bin/env python3
"""Offline real native ASR evaluation of checksum-frozen synthetic files, never microphone audio.
Exit0 validates execution/bounds; WER is a measured result, not a physical quality pass.
"""
import array
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
import wave

HERE=Path(__file__).resolve().parent
CACHE=HERE.parents[1]/'.local/asr'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verified_model():
    record=json.loads((HERE/'provenance.json').read_text())
    host=record['host']
    if digest(CACHE/host['archive'])!=host['publisher_sha256']:
        raise ValueError('native archive integrity failed')
    for item in host['files']:
        if digest(CACHE/item['path'])!=item['sha256']:
            raise ValueError('native extracted artifact integrity failed')
    model=CACHE/record['model']['directory']
    for item in record['model']['files']:
        path=model/item['file']
        if path.stat().st_size!=item['bytes'] or digest(path)!=item['local_sha256']:
            raise ValueError('model integrity failed')
    return model,record

def main():
    model,record=verified_model()
    runtime=CACHE/'moonshine-voice-macos-arm64'
    build=CACHE/'build';build.mkdir(exist_ok=True)
    executable=build/'asr-host'
    subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror',
        '-I',str(HERE/'include'),'-I',str(runtime/'include'),str(HERE/'eilo_asr.cc'),str(HERE/'tests/host.cc'),
        str(runtime/'lib/libmoonshine.a'),'-framework','Accelerate','-framework','Foundation','-o',str(executable)],check=True,timeout=120)
    manifest=json.loads((HERE/'tests/fixtures.json').read_text())
    cases=[]
    with tempfile.TemporaryDirectory(prefix='eilo-synthetic-asr-') as temp:
        raw=Path(temp)/'synthetic.f32'
        for item in manifest['cases']:
            path=CACHE/'fixtures'/item['file']
            if digest(path)!=item['sha256']:
                raise ValueError('synthetic fixture changed')
            with wave.open(str(path),'rb') as w:
                if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())!=(1,2,16000,item['samples']):
                    raise ValueError('invalid synthetic fixture')
                pcm=array.array('h',w.readframes(w.getnframes()))
            raw.write_bytes(array.array('f',(v/32768 for v in pcm)).tobytes())
            start=time.monotonic()
            p=subprocess.run([str(executable),str(model),str(raw)],capture_output=True,text=True,check=True,timeout=120)
            text=p.stdout.strip()
            if len(text.encode())>4096:
                raise ValueError('unbounded native output')
            cases.append({'id':item['id'],'slice':item['slice'],'reference':item['reference'],
                'transcript':text,'seconds':round(time.monotonic()-start,3),'audio_seconds':item['samples']/16000,
                'final_once_and_closed_input':'PASS'})
            raw.write_bytes(bytes(raw.stat().st_size));raw.unlink()
    report={'runtime':record['version'],'platform':'macOS ARM64 native CPU','model':record['model']['directory'],
        'kind':'synthetic-only','cases':cases,'physical':'NOT RUN','production_readiness':'NOT ENABLED'}
    (CACHE/'host-results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Real native streaming ASR: '+str(len(cases))+' frozen synthetic cases executed; final/cancellation boundary checks PASS.')

if __name__=='__main__':
    main()
