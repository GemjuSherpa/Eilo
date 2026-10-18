"""Validate partial operator listening ratings; never acoustic/offline acceptance."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

FIXTURES=Path(__file__).parent.parent/'offline-speech/tests/voice-trial-fixtures.json'

def require(ok,message):
    if not ok:raise ValueError(message)

def validate(r):
    require(isinstance(r,dict) and set(r)=={'schema_version','scope','physical_gate_acceptance','acoustic_timing','network_observation','radio_state','radio_attestation_recorded_utc','fixture_sha256','voice_id','os_build','updated_utc','attempts'},'unexpected survey fields')
    require(type(r['schema_version']) is int and r['schema_version']==1 and r['scope']=='INTERNAL_IOS_LISTENING_SURVEY','wrong survey scope')
    require(r['physical_gate_acceptance']=='NOT_RUN' and r['acoustic_timing']=='NOT_RUN' and r['network_observation']=='NOT_RUN' and r['radio_state']=='OPERATOR_DECLARED_OFF_AT_BUILD','unsupported acceptance or network claim')
    require(r['fixture_sha256']==hashlib.sha256(FIXTURES.read_bytes()).hexdigest(),'frozen corpus changed')
    require(isinstance(r['voice_id'],str) and re.fullmatch(r'[A-Za-z0-9._-]{1,256}',r['voice_id']),'invalid public voice ID')
    require(isinstance(r['os_build'],str) and 0<len(r['os_build'])<=160,'invalid OS metadata')
    require(isinstance(r['radio_attestation_recorded_utc'],str) and len(r['radio_attestation_recorded_utc'])<=64 and datetime.fromisoformat(r['radio_attestation_recorded_utc'].replace('Z','+00:00')).tzinfo is not None,'missing declaration provenance')
    require(isinstance(r['updated_utc'],str) and len(r['updated_utc'])<=64 and datetime.fromisoformat(r['updated_utc'].replace('Z','+00:00')).tzinfo is not None,'invalid timestamp')
    require(isinstance(r['attempts'],list) and len(r['attempts'])<=36,'invalid attempts')
    expected=1;counts={}
    for i,a in enumerate(r['attempts'],1):
        require(isinstance(a,dict) and {'fixture_id','attempt','sdk_status'}<=set(a)<={'fixture_id','attempt','sdk_status','intelligibility'},'unexpected attempt fields')
        require(type(a['attempt']) is int and a['attempt']==i and a['fixture_id']==f'voice-{expected:02d}','unordered or duplicate rated phrase')
        counts[expected]=counts.get(expected,0)+1;require(counts[expected]<=3,'retry limit exceeded')
        require(a['sdk_status'] in ['PLAYING','INTERRUPTED','SDK_COMPLETED'],'invalid SDK status')
        if a['sdk_status']=='PLAYING':require(i==len(r['attempts']),'unfinished attempt is not last')
        if 'intelligibility' in a:
            require(a['sdk_status']=='SDK_COMPLETED' and type(a['intelligibility']) is int and 1<=a['intelligibility']<=5,'invalid operator rating')
            expected+=1
    return r

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    require(a.source.stat().st_size<=16384,'survey too large');r=validate(json.loads(a.source.read_text()))
    if a.output:
        with a.output.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print('Listening survey valid; physical acceptance, acoustic timing and traffic verification NOT_RUN.')
if __name__=='__main__':main()
