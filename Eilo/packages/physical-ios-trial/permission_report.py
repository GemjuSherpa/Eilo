"""Validate lab OS permission/controller observations; hardware capture remains untested."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import uuid

ROOT={'schema_version','scope','samples','raw_audio_saved','raw_text_exported','physical_gate_acceptance','hardware_capture','production'}
ROW={'kind','permission','start_requested','start_accepted','capture_effect_calls','capture_pending','controller_state','prior_denial_same_process','outcome','process_session','updated_utc'}


def require(value):
    if not value: raise ValueError('invalid or unsupported permission evidence')


def validate(report):
    require(type(report) is dict and set(report)==ROOT)
    require(type(report['schema_version']) is int and report['schema_version']==1)
    require(report['scope']=='IOS_OS_PERMISSION_BOUNDARY' and report['physical_gate_acceptance']=='NOT_RUN')
    require(report['raw_audio_saved'] is False and report['raw_text_exported'] is False)
    require(report['hardware_capture']=='NOT_OPENED' and report['production']=='NOT_ENABLED')
    require(type(report['samples']) is list and 1<=len(report['samples'])<=8)
    denied_sessions=set();restored=[];failures=0
    for row in report['samples']:
        require(type(row) is dict and set(row)==ROW)
        require(row['kind'] in ['DENIED_START','RESTORED_NO_START'])
        require(row['permission'] in ['DENIED','GRANTED','UNAVAILABLE'])
        require(row['outcome'] in ['OBSERVED','FAILED'])
        require(row['controller_state'] in ['setup','permission_required','stopped','standby','listening','thinking','speaking','paused','error'])
        for key in ['start_requested','start_accepted','capture_pending','prior_denial_same_process']:require(type(row[key]) is bool)
        require(type(row['capture_effect_calls']) is int and 0<=row['capture_effect_calls']<=16)
        session=row['process_session'];require(type(session) is str and str(uuid.UUID(session)).upper()==session.upper())
        date=row['updated_utc'];require(type(date) is str and len(date)<=64 and datetime.fromisoformat(date.replace('Z','+00:00')).tzinfo is not None)
        denied=row['kind']=='DENIED_START'
        require(row['start_requested']==denied)
        require(row['prior_denial_same_process']==(session in denied_sessions))
        if not denied:require(bool(denied_sessions))
        expected=(row['permission']==('DENIED' if denied else 'GRANTED') and not row['start_accepted'] and
                  row['capture_effect_calls']==0 and not row['capture_pending'] and
                  row['controller_state'] in (['permission_required'] if denied else ['stopped','permission_required']))
        require((row['outcome']=='OBSERVED')==expected)
        if row['outcome']=='FAILED':failures+=1
        elif denied:denied_sessions.add(session)
        else:restored.append(row)
    return dict(denial_observed=bool(denied_sessions),restoration_no_start_observed=bool(restored),
                restoration_same_process_observed=any(row['prior_denial_same_process'] for row in restored),
                failed_attempts=failures,hardware_capture='NOT_OPENED',active_hardware_revocation='NOT_RUN',physical_gate_acceptance='NOT_RUN')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);args=parser.parse_args()
    require(args.source.stat().st_size<=32768)
    print(json.dumps(validate(json.loads(args.source.read_text())),indent=2))


if __name__=='__main__':main()
