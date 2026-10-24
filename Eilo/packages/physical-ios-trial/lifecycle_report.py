"""Validate owned lab lifecycle aggregates; no acoustic, lock-support or release acceptance."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import uuid

CASES=['playback_stop','playback_background','playback_lock','capture_stop','capture_background','capture_lock']
ROOT={'schema_version','scope','cases','phase','pending_case','physical_gate_acceptance','production',
      'acoustic_stop_timing','locked_capture_support','network_observation','raw_audio_saved','raw_text_exported',
      'lock_action','process_session','os_build','physical_memory_bytes','updated_utc'}
ROW={'case','attempt','outcome','active_observed','stop_event','stopped_after_event','resumption_observed','return_check_completed'}


def require(value):
    if not value: raise ValueError('invalid or unsupported lifecycle evidence')


def validate(r):
    require(type(r) is dict and set(r)==ROOT)
    require(type(r['schema_version']) is int and r['schema_version']==1 and r['scope']=='IOS_LAB_LIFECYCLE_OBSERVATIONS')
    require(r['physical_gate_acceptance']=='NOT_RUN' and r['production']=='NOT_ENABLED' and r['acoustic_stop_timing']=='NOT_RUN')
    require(r['locked_capture_support']=='NOT_ENABLED' and r['network_observation']=='NOT_RUN')
    require(r['raw_audio_saved'] is False and r['raw_text_exported'] is False)
    require(r['lock_action']=='OPERATOR_REQUESTED_NOT_OS_LOCK_PROOF')
    require(type(r['process_session']) is str and str(uuid.UUID(r['process_session'])).upper()==r['process_session'].upper())
    require(type(r['os_build']) is str and 0<len(r['os_build'])<=160)
    require(type(r['physical_memory_bytes']) is int and 0<r['physical_memory_bytes']<2**40)
    require(type(r['updated_utc']) is str and len(r['updated_utc'])<=64 and datetime.fromisoformat(r['updated_utc'].replace('Z','+00:00')).tzinfo is not None)
    require(type(r['cases']) is list and len(r['cases'])<=18)
    counts={key:0 for key in CASES};observed=set();index=0
    for row in r['cases']:
        require(type(row) is dict and set(row)==ROW and index<len(CASES))
        key=row['case'];require(key==CASES[index] and key not in observed)
        counts[key]+=1;require(type(row['attempt']) is int and row['attempt']==counts[key]<=3)
        for field in ['active_observed','stopped_after_event','resumption_observed','return_check_completed']:
            require(type(row[field]) is bool)
        require(row['outcome'] in ['OBSERVED','FAILED'])
        require(row['stop_event'] in ['NONE','STOP_BUTTON','SCENE_RESIGNED','PROTECTED_DATA_UNAVAILABLE','AUDIO_INTERRUPTION_OR_ROUTE'])
        if row['outcome']=='OBSERVED':
            require(row['active_observed'] and row['stopped_after_event'] and row['return_check_completed'] and not row['resumption_observed'])
            events=['STOP_BUTTON'] if key.endswith('_stop') else ['SCENE_RESIGNED']
            if key.endswith('_lock'): events.append('PROTECTED_DATA_UNAVAILABLE')
            require(row['stop_event'] in events)
            observed.add(key);index+=1
    complete=len(observed)==6
    require(r['phase'] in ['PARTIAL','IN_PROGRESS','COMPLETED'])
    require((r['phase']=='COMPLETED')==complete)
    if r['phase']=='IN_PROGRESS':
        require(index<6 and r['pending_case']==CASES[index] and counts[CASES[index]]<3)
    else: require(r['pending_case']=='NONE')
    return {'observed_cases':len(observed),'failed_attempts':sum(row['outcome']=='FAILED' for row in r['cases']),
            'phase':r['phase'],'physical_gate_acceptance':'NOT_RUN','locked_capture_support':'NOT_ENABLED',
            'acoustic_stop_timing':'NOT_RUN','network_observation':'NOT_RUN'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);args=parser.parse_args()
    require(args.source.stat().st_size<=32768)
    print(json.dumps(validate(json.loads(args.source.read_text())),indent=2))


if __name__=='__main__': main()
