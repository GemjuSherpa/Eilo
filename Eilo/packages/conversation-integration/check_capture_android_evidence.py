"""Offline closed-schema review of ART capture/reply evidence; no models, SDK or audio."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'vad-runtime'))
from check_android_installer_evidence import load, digest
from check_installer import sha256, require
from check_capture_android import validate_joined, LIBRARIES

ROOT=Path(__file__).resolve().parents[2]
NATIVE={'scope','physical','production','microphone','confidence','speech_sink','cases'}
EXTRA={'vad_model_sha256','schema_version','runtime_profile','ort_header_commit','abi','android_api','library_sha256',
       'evaluation_apk_sha256','normal_apk_sha256','temporary_files_removed','normal_app_restored',
       'internet_permission','microphone_permission','fixture_sha256','vad_source_model_sha256',
       'vad_conversion','asr_model_files','controller_permission_and_readiness','network_acceptance','llm'}
ROW={'case','recognized','metadata','normalized_samples','llm_starts','reply_submitted','completed','clauses',
     'transcript_sha256','context_messages','worker_verified'}


def source_paths(root):
    patterns=('apps/mobile/android/app/src/main/java/com/eilo/*.kt','apps/mobile/android/app/src/main/java/com/eilo/foundation/*.kt',
              'packages/conversation-integration/tests/android-device/*','packages/conversation-integration/tests/android-joined-speech/*','packages/vad-runtime/eilo_vad*.cc','packages/vad-runtime/include/*',
              'packages/vad-runtime/tests/android-device/*.cc','packages/asr-runtime/eilo_asr*.cc','packages/asr-runtime/include/*',
              'packages/llm-runtime/eilo_llm*.cc','packages/llm-runtime/include/*')
    paths={str(p.relative_to(root)) for pattern in patterns for p in root.glob(pattern) if p.is_file()}
    paths.update('packages/'+p for p in ('conversation-integration/check_capture_android.py','vad-runtime/vad_backend.h',
        'vad-runtime/check_installer.py','vad-runtime/check_installer_android.py','vad-runtime/check_native.py',
        'vad-runtime/provenance.json','vad-runtime/android-ort-header-provenance.json','asr-runtime/provenance.json',
        'asr-runtime/tests/fixtures.json','llm-runtime/provenance.json','llm-runtime/check_host.py','llm-runtime/check_android.py'))
    return paths


def validate_report(report, root=ROOT, sdk=False):
    require(set(report)==NATIVE|EXTRA and type(report['schema_version']) is int and report['schema_version']==1,'report schema changed')
    validate_joined(report, sdk)
    require(report['microphone']=='NOT_USED' and report['network_acceptance']=='NOT_RUN'
            and report['controller_permission_and_readiness']=='SYNTHETIC','acceptance promoted')
    require(report['temporary_files_removed'] is True and report['normal_app_restored'] is True
            and report['internet_permission']=='ABSENT' and report['microphone_permission']=='ABSENT','cleanup/permissions failed')
    require(type(report['android_api']) is int and report['android_api']==35 and report['abi']=='arm64-v8a','platform changed')
    baseline=load(root/'packages/vad-runtime/tests/signed-installer-android-results.json')
    for key in ('runtime_profile','ort_header_commit','fixture_sha256','vad_source_model_sha256','asr_model_files'):
        require(report[key]==baseline[key],'speech source/conversion changed')
    conversion=report['vad_conversion']; reference=baseline['vad_conversion']
    require(set(conversion)==set(reference) and all(conversion[k]==reference[k] for k in reference if k!='bytes')
            and type(conversion['bytes']) is int and 2_000_000<=conversion['bytes']<=4_000_000,'conversion provenance changed')
    digest(report['vad_model_sha256']) # ORT serialization can vary; this run's report/audit pins its actual bytes.
    require(set(report['library_sha256'])==set(LIBRARIES),'library inventory changed')
    for name in ('libonnxruntime.so','libmoonshine.so'):
        require(report['library_sha256'][name]==baseline['library_sha256'][name],'vendor binary changed')
    for value in [report['evaluation_apk_sha256'],report['normal_apk_sha256'],*report['library_sha256'].values()]:digest(value)
    provenance=load(root/'packages/llm-runtime/provenance.json'); llm=report['llm']
    require(set(llm)=={'runtime_commit','model','cpu_options','archive_network_clients'}
            and llm['runtime_commit']==provenance['runtime']['commit'] and llm['model']==provenance['model']
            and llm['archive_network_clients']=='ABSENT','LLM provenance changed')
    options=llm['cpu_options']
    require(options['ANDROID_ABI']=='arm64-v8a' and options['ANDROID_PLATFORM']=='android-26'
            and options['GGML_CPU']=='ON' and options['GGML_NATIVE']=='OFF'
            and options['LLAMA_OPENSSL']=='OFF' and options['LLAMA_SUBPROCESS']=='OFF'
            and all(v=='OFF' for k,v in options.items() if k in {'GGML_CUDA','GGML_VULKAN','GGML_METAL','GGML_OPENCL','GGML_RPC','GGML_BACKEND_DL'}),'LLM build profile changed')
    require(type(report['cases']) is list and len(report['cases'])==3,'case inventory changed')
    expected_hash=baseline['cases'][0]['transcript_sha256']
    for index,row in enumerate(report['cases']):
        require(set(row)==ROW,'case schema changed')
        for key in ('recognized','metadata','normalized_samples','llm_starts','clauses','context_messages'):
            require(type(row[key]) is int and row[key]>=0,'invalid count')
        for key in ('reply_submitted','completed','worker_verified'):require(type(row[key]) is bool,'invalid flag')
        require(row['normalized_samples']==(29184 if index<2 else 80000),'capture sample count changed')
        require(row['transcript_sha256']==(expected_hash if index<2 else ''),'transcript mismatch')
        require(row['reply_submitted'] is (index<2),'reply scope changed')
        require(row['clauses']<=5,'clause bound changed')
    return report


def check_evidence(root=ROOT, sdk=False):
    prefix="android-sdk-capture" if sdk else "android-capture"
    path=root/('packages/conversation-integration/tests/'+prefix+'-results.json')
    audit=load(root/('packages/conversation-integration/tests/'+prefix+'-evidence.json'))
    require(set(audit)=={'schema_version','report_sha256','inputs'} and audit['schema_version']==1,'audit schema changed')
    require(sha256(path)==audit['report_sha256'],'report changed')
    paths=source_paths(root)
    require(len(audit['inputs'])==len(paths) and {p['path'] for p in audit['inputs']}==paths,'source coverage changed')
    for row in audit['inputs']:
        require(set(row)=={'path','sha256'},'source pin schema changed')
        require(sha256(root/row['path'])==row['sha256'],'evaluated source changed')
    validate_report(load(path),root,sdk)
    print('Android capture/local reply evidence PASS; sink=' + ('muted native SDK' if sdk else 'synthetic') + '; physical/acoustic/network NOT_RUN.')


if __name__=='__main__':
    check_evidence();check_evidence(sdk=True)
