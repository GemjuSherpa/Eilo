#!/usr/bin/env python3
"""Explicit local evaluation setup. Only generic pinned models/libraries and synthetic speech.
Nothing here runs from the app. No personal recording, auth or inference upload.
"""
import argparse
import array
import base64
import hashlib
import json
from pathlib import Path
import random
import subprocess
import tarfile
import urllib.request
import wave
import zipfile
from check_host import CACHE,HERE,digest

def crc32c(data):
    table=[]
    for i in range(256):
        value=i
        for _ in range(8):value=(value>>1)^(0x82f63b78 if value&1 else 0)
        table.append(value)
    value=0xffffffff
    for byte in data:
        value=table[(value^byte)&255]^(value>>8)
    return base64.b64encode((value^0xffffffff).to_bytes(4,'big')).decode()

def fetch(url,path,sha,size=None,crc=None):
    if path.exists() and digest(path)==sha:return
    request=urllib.request.Request(url,headers={'User-Agent':'Eilo-local-model-evaluation/0.1','Accept':'application/octet-stream'})
    with urllib.request.urlopen(request,timeout=60) as response:data=response.read(200000001)
    if len(data)>200000000 or (size is not None and len(data)!=size) or hashlib.sha256(data).hexdigest()!=sha or (crc is not None and crc32c(data)!=crc):raise ValueError('pinned asset integrity failed')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--with-ios',action='store_true');p.add_argument('--with-android',action='store_true');p.add_argument('--generate-fixtures',action='store_true');args=p.parse_args()
    record=json.loads((HERE/'provenance.json').read_text());CACHE.mkdir(parents=True,exist_ok=True)
    host=record['host'];archive=CACHE/host['archive'];fetch(host['url'],archive,host['publisher_sha256'])
    with tarfile.open(archive) as t:t.extractall(CACHE,filter='data')
    for item in record['model']['files']:
        fetch(item['url'],CACHE/record['model']['directory']/item['file'],item['local_sha256'],item['bytes'],item['publisher_crc32c'])
    for enabled,kind,archive_name,folder in [(args.with_ios,'ios','Moonshine-v0.1.5.xcframework.zip','ios-0.1.5'),(args.with_android,'android','moonshine-voice-0.1.5.aar','android-0.1.5')]:
        if enabled:
            entry=record[kind];archive=CACHE/archive_name;fetch(entry['url'],archive,entry['publisher_sha256'])
            with zipfile.ZipFile(archive) as z:
                if any(Path(n).is_absolute() or '..' in Path(n).parts for n in z.namelist()):raise ValueError('invalid archive path')
                z.extractall(CACHE/folder)
    if args.generate_fixtures:
        fixtures=json.loads((HERE/'tests/fixtures.json').read_text());directory=CACHE/'fixtures';directory.mkdir(exist_ok=True)
        for item in fixtures['cases']:
            path=directory/item['file']
            if path.exists() and digest(path)==item['sha256']:continue
            aiff=directory/(item['id']+'.aiff')
            subprocess.run(['say','-v',item['voice'],'-o',str(aiff),item['reference']],check=True,timeout=30)
            subprocess.run(['afconvert','-f','WAVE','-d','LEI16@16000','-c','1',str(aiff),str(path)],check=True,timeout=30)
            with wave.open(str(path),'rb') as w:pcm=array.array('h',w.readframes(w.getnframes()))
            pcm=array.array('h',[0]*8000)+pcm+array.array('h',[0]*16000)
            if item['slice']=='noise':
                rng=random.Random(1705);pcm=array.array('h',[max(-32768,min(32767,int(v+rng.gauss(0,500)))) for v in pcm])
            with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(pcm.tobytes())
            aiff.unlink()
            if digest(path)!=item['sha256']:raise ValueError('installed voice differs from frozen fixture; do not silently update the reference')
    print('Pinned generic ASR evaluation assets prepared. No microphone or production activation.')

if __name__=='__main__':main()
