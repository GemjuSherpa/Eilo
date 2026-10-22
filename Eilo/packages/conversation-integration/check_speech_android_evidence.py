"""Offline audit of the existing Android speech SDK/voice check, never acoustic acceptance."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'vad-runtime'))
from check_android_installer_evidence import load,digest
from check_installer import require,sha256
ROOT=Path(__file__).resolve().parents[2]
FIELDS={'scope','physical','network_acceptance','acoustic_acceptance','production','microphone','eligible_voice',
        'download_requested','sdk_completed','sdk_started','sdk_finished','status','schema_version','android_api','abi',
        'internet_permission','microphone_permission','temporary_files_removed','normal_app_restored',
        'evaluation_apk_sha256','normal_apk_sha256'}


def source_paths(root):
    paths={str(p.relative_to(root)) for pattern in ('apps/mobile/android/app/src/main/java/com/eilo/*.kt',
        'apps/mobile/android/app/src/main/java/com/eilo/foundation/*.kt','packages/conversation-integration/tests/android-speech/*.kt') for p in root.glob(pattern) if p.is_file()}
    paths.update({'packages/conversation-integration/check_speech_android.py','packages/vad-runtime/check_installer_android.py',
                  'apps/mobile/android/app/src/main/AndroidManifest.xml','apps/mobile/android/app/build.gradle'})
    return paths


def validate(report):
    require(set(report)==FIELDS and type(report['schema_version']) is int and report['schema_version']==1,'SDK report schema changed')
    require(report['scope']=='ANDROID_EMULATOR_SPEECH_SDK' and report['physical']=='NOT_RUN'
            and report['network_acceptance']=='NOT_RUN' and report['acoustic_acceptance']=='NOT_RUN'
            and report['production']=='NOT_ENABLED' and report['microphone']=='NOT_USED','SDK acceptance promoted')
    require(type(report['android_api']) is int and report['android_api']==35 and report['abi']=='arm64-v8a','platform changed')
    require(report['download_requested'] is False and report['temporary_files_removed'] is True and report['normal_app_restored'] is True
            and report['internet_permission']=='ABSENT' and report['microphone_permission']=='ABSENT','SDK permissions/cleanup changed')
    for key in ('sdk_started','sdk_finished'):require(type(report[key]) is int,'invalid SDK count')
    for key in ('sdk_completed','eligible_voice'):require(type(report[key]) is bool,'invalid SDK flag')
    if report['status']=='SDK_CALLBACKS_COMPLETED':
        require(report['eligible_voice'] is True and report['sdk_completed'] is True and report['sdk_started']==report['sdk_finished']==1,'SDK events missing')
    else:
        require(report['status']=='BLOCKED_OFFLINE_VOICE_MISSING' and report['eligible_voice'] is False and report['sdk_completed'] is False
                and report['sdk_started']==report['sdk_finished']==0,'false readiness or unknown SDK status')
    digest(report['evaluation_apk_sha256']);digest(report['normal_apk_sha256'])


def check_evidence(root=ROOT):
    path=root/'packages/conversation-integration/tests/android-speech-results.json'
    audit=load(root/'packages/conversation-integration/tests/android-speech-evidence.json')
    require(set(audit)=={'schema_version','report_sha256','inputs'} and audit['schema_version']==1,'SDK audit changed')
    require(sha256(path)==audit['report_sha256'],'SDK report changed');paths=source_paths(root)
    require(len(audit['inputs'])==len(paths) and {r['path'] for r in audit['inputs']}==paths,'SDK source coverage changed')
    for row in audit['inputs']:
        require(set(row)=={'path','sha256'} and sha256(root/row['path'])==row['sha256'],'SDK source changed')
    report=load(path);validate(report);print(report['status']+'; acoustic/physical/network NOT_RUN.')


if __name__=='__main__':check_evidence()
