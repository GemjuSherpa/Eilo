"""Validate file-fed iPhone ASR diagnostics; no microphone/quality acceptance inference."""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
FIXTURES=Path(__file__).parent.parent/'asr-runtime/tests/fixtures.json'
def require(ok,message):
 if not ok:raise ValueError(message)
def validate(r):
 require(isinstance(r,dict) and set(r)=={'schema_version','scope','phase','input_kind','microphone','physical_quality_acceptance','acoustic_timing','raw_text_exported','fixture_manifest_sha256','os_build','physical_memory_bytes','updated_utc','cases'},'unexpected report fields')
 require(type(r['schema_version']) is int and r['schema_version']==1 and r['scope']=='IOS_DEVICE_FILE_ASR_DIAGNOSTIC','wrong report scope')
 require(r['input_kind']=='FROZEN_SYNTHETIC_FILES' and r['microphone']=='NOT_OPENED' and r['physical_quality_acceptance']=='NOT_RUN' and r['acoustic_timing']=='NOT_RUN' and r['raw_text_exported'] is False,'unsupported physical/content claim')
 require(r['fixture_manifest_sha256']==hashlib.sha256(FIXTURES.read_bytes()).hexdigest(),'frozen fixtures changed')
 require(isinstance(r['os_build'],str) and 0<len(r['os_build'])<=160 and type(r['physical_memory_bytes']) is int and 0<r['physical_memory_bytes']<=2**40,'invalid device metadata')
 require(isinstance(r['updated_utc'],str) and len(r['updated_utc'])<=64 and datetime.fromisoformat(r['updated_utc'].replace('Z','+00:00')).tzinfo is not None,'invalid timestamp')
 require(r['phase'] in ['RUNNING','CANCELLED','INFERENCE_FAILED','COMPLETED'] and isinstance(r['cases'],list),'invalid phase/cases')
 if r['phase']!='COMPLETED':require(not r['cases'],'incomplete run contains success rows');return r
 pins=json.loads((Path(__file__).parent/'tests/asr-pcm-pins.json').read_text());
 fixtures=json.loads(FIXTURES.read_text())['cases'];require(len(r['cases'])==len(fixtures),'missing cases')
 for a,f,pin in zip(r['cases'],fixtures,pins):
  require(isinstance(a,dict) and set(a)=={'fixture_id','pcm_sha256','samples','runtime_elapsed_ms','reference_words','substitutions','deletions','insertions','errors'},'unexpected case fields')
  require(a['fixture_id']==f['id'] and type(a['samples']) is int and a['samples']==f['samples'],'case order/size changed')
  require(a['pcm_sha256']==pin['sha256'] and pin['id']==f['id'] and pin['samples']==f['samples'],'invalid PCM pin')
  for key in ['reference_words','substitutions','deletions','insertions','errors']:require(type(a[key]) is int and 0<=a[key]<=4096,'invalid edit counts')
  count=len(re.findall(r"[a-z0-9]+(?:'[a-z]+)?",f['reference'].lower()))
  require(a['reference_words']==count and a['errors']==a['substitutions']+a['deletions']+a['insertions'] and a['substitutions']+a['deletions']<=count,'inconsistent edit accounting')
  require(type(a['runtime_elapsed_ms']) in [int,float] and math.isfinite(a['runtime_elapsed_ms']) and 0<=a['runtime_elapsed_ms']<=180000,'invalid runtime')
 return r
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();require(a.source.stat().st_size<=16384,'report too large');r=validate(json.loads(a.source.read_text()))
 if a.output:
  with a.output.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
 print('File ASR report valid: '+r['phase']+'; physical microphone quality NOT_RUN.')
if __name__=='__main__':main()
