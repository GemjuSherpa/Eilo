"""Validate only an owned trial app's aggregate JSON; no phone access or acceptance promotion."""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import re

REQUIRED={'schema_version','scope','physical_gate_acceptance','production','raw_audio_saved','raw_text_exported',
 'confidence','airplane_mode','wifi_bluetooth','sdk_probe_completed','operator_heard_probe','microphone_finals',
 'clarification_completed','synthetic_model_completed','synthetic_model_starts','os_build','physical_memory_bytes','phase','updated_utc'}
OPTIONAL={'preparation_stage','radio_attestation_recorded_utc','microphone_permission_granted','audio_session_deactivated','foreground',
 'voice_id','probe_route','route_input','route_output','source_rate','normalized_samples','speech_route','input_kind'}
PHASES={'LAUNCHED_NO_CAPTURE','PREPARING_MODELS','MODELS_READY','MODEL_PREPARATION_FAILED','NO_INSTALLED_ENGLISH_VOICE',
 'VOICE_SESSION_FAILED','VOICE_PROBE_PLAYING','VOICE_PROBE_SDK_COMPLETED','SINGLE_PHRASE_OPERATOR_CONFIRMED',
 'VOICE_READINESS_FAILED','VOICE_SETUP_FAILED','FOREGROUND_REQUIRED','CAPTURE_START_DENIED','CAPTURE_START_REQUESTED',
 'CAPTURE_OR_REPLY_FAILED','TRIAL_TIMEOUT','CAPTURE_TRANSITION_DENIED','MODEL_CONFIGURATION_MISSING','NO_SPEECH',
 'SIGNED_CAPTURE_ATTACHMENT_FAILED','MICROPHONE_SPEAK_NOW','STALE_REPLY_DENIED','REPLY_AUDIO_SESSION_FAILED',
 'REPLY_SUBMIT_FAILED','REPLY_SUBMITTED','STOPPED_CONTENT_CLEARED','SINGLE_TURN_SDK_COMPLETED'}


def require(value,message):
    if not value: raise ValueError(message)


def validate(r):
    require(isinstance(r,dict) and REQUIRED<=set(r)<=REQUIRED|OPTIONAL,'unexpected or missing aggregate fields')
    require(type(r['schema_version']) is int and r['schema_version']==1 and r['scope']=='INTERNAL_IOS_FOREGROUND_TRIAL','wrong trial scope')
    require(r['physical_gate_acceptance']=='NOT_RUN' and r['production']=='NOT_ENABLED' and r['raw_audio_saved'] is False
            and r['raw_text_exported'] is False and r['confidence']=='UNAVAILABLE','false acceptance or content claim')
    require(r['phase'] in PHASES,'unknown trial phase')
    for key in ['sdk_probe_completed','operator_heard_probe', 'microphone_permission_granted','audio_session_deactivated','foreground']:
        if key in r: require(type(r[key]) is bool,'invalid boolean field')
    for key in ['microphone_finals','clarification_completed','synthetic_model_completed','synthetic_model_starts']:
        require(type(r[key]) is int and 0<=r[key]<=1000,'invalid trial counters')
    require(r['synthetic_model_completed']<=r['synthetic_model_starts'],'synthetic reply without model start')
    require(r['clarification_completed']<=r['microphone_finals'],'clarification without a microphone final')
    require(not r['operator_heard_probe'] or r['sdk_probe_completed'],'audibility attestation without completed probe')
    require(not (r['microphone_finals'] or r['synthetic_model_completed']) or r['operator_heard_probe'],'trial ran without voice attestation')
    declared=r['airplane_mode']=='OPERATOR_DECLARED_AT_BUILD' and r['wifi_bluetooth']=='OPERATOR_DECLARED_OFF_AT_BUILD'
    require(declared or (r['airplane_mode']=='NOT_PROVIDED' and r['wifi_bluetooth']=='NOT_PROVIDED'),'unsupported network proof claim')
    require(not r['sdk_probe_completed'] or declared,'probe without operator network declaration')
    require(type(r['physical_memory_bytes']) is int and 0<r['physical_memory_bytes']<=2**40,'invalid hardware memory metadata')
    require(isinstance(r['os_build'],str) and 0<len(r['os_build'])<=160,'invalid OS metadata')
    for key in ['updated_utc','radio_attestation_recorded_utc']:
        if key in r:
            require(isinstance(r[key],str) and len(r[key])<=64,'invalid timestamp')
            require(datetime.fromisoformat(r[key].replace('Z','+00:00')).tzinfo is not None,'timezone required')
    if declared:require('radio_attestation_recorded_utc' in r,'operator declaration provenance missing')
    if 'preparation_stage' in r:require(r['preparation_stage'] in ['READ_BUNDLED_PINS','VERIFY_LAB_MANIFEST','VERIFY_BUNDLED_ARTIFACTS','ACTIVATE_LAB_PACK','PROTECT_LAB_PACK','SELECT_RUNTIME_PINS'],'invalid preparation stage')
    if 'voice_id' in r:require(isinstance(r['voice_id'],str) and re.fullmatch(r'[A-Za-z0-9._-]{1,256}',r['voice_id']) is not None,'invalid public voice ID')
    for key in ['probe_route','route_input','route_output','speech_route']:
        if key in r:require(isinstance(r[key],list) and len(r[key])<=8 and all(isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_]{1,64}',v) for v in r[key]),'invalid public route metadata')
    if 'source_rate' in r:require(type(r['source_rate']) in [int,float] and math.isfinite(r['source_rate']) and 8000<=r['source_rate']<=192000,'invalid source rate')
    if 'normalized_samples' in r:require(type(r['normalized_samples']) is int and 0<=r['normalized_samples']<=480000,'invalid normalized count')
    if 'input_kind' in r:require(r['input_kind'] in ['FIXED_SYNTHETIC_PROMPT','PHYSICAL_MICROPHONE_UNCALIBRATED'],'invalid input origin')
    return r


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    require(a.source.stat().st_size<=16384,'aggregate report too large');r=validate(json.loads(a.source.read_text()))
    if a.output:
        require(not a.output.exists(),'refusing to overwrite evidence');a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print('Aggregate valid: '+r['phase']+'; physical acceptance NOT_RUN. No raw speech content exported.')


if __name__=='__main__':main()
