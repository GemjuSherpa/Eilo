#!/usr/bin/env python3
"""Explicit joined synthetic iOS evaluation with existing pinned native assets only.
No microphone, app readiness override, download or production trust configuration.
"""
import argparse,hashlib,importlib.util,json,subprocess,sys,tempfile,array,wave
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def load(package):
    path=HERE.parent/package
    sys.modules.pop('check_host',None);sys.path.insert(0,str(path))
    spec=importlib.util.spec_from_file_location(package.replace('-','_')+'_ios',path/'check_ios.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);sys.path.pop(0);return m

def main():
    p=argparse.ArgumentParser();p.add_argument('--udid',required=True);a=p.parse_args()
    devices=json.loads(subprocess.run(['xcrun','simctl','list','devices','--json'],check=True,capture_output=True,text=True).stdout)
    if not any(d['udid']==a.udid and d['state']=='Booted' for group in devices['devices'].values() for d in group):raise ValueError('explicit booted simulator required')
    llm=load('llm-runtime');llm.verify_source();_,record=llm.build('iphonesimulator')
    wake=load('wake-runtime');wake_root,wake_model,fixtures=wake.verify_candidates()
    wake_build,sdk,wake_link,wake_lib=wake.compile_runtime(wake_root,'ios-arm64_x86_64-simulator','iphonesimulator','arm64-apple-ios18.0-simulator')
    asr=load('asr-runtime');asr_model,asr_record=asr.verified_model();ios=asr_record['ios']
    if asr.digest(asr.CACHE/ios['archive'])!=ios['publisher_sha256']:raise ValueError('ASR archive integrity')
    for item in ios['files']:
        if asr.digest(asr.CACHE/item['path'])!=item['sha256']:raise ValueError('ASR extracted integrity')
    cache=ROOT/'.local/conversation-integration';cache.mkdir(exist_ok=True)
    moon=asr.CACHE/'ios-0.1.5/Moonshine.xcframework/ios-arm64_x86_64-simulator'
    subprocess.run(list(map(str,['xcrun','--sdk','iphonesimulator','clang++','-target','arm64-apple-ios18.0-simulator','-isysroot',sdk,'-std=c++17','-Wall','-Wextra','-Werror','-I',asr.HERE/'include','-I',moon/'Headers','-c',asr.HERE/'eilo_asr.cc','-o',cache/'eilo_asr.o'])),check=True)
    # Isolate the unchanged Moonshine static vendor archive behind only our four C exports.
    # No multiply-defined suppression, vendor patch or global runtime-symbol substitution.
    exports=cache/'asr.exports';exports.write_text('_eilo_asr_create\n_eilo_asr_accept\n_eilo_asr_text\n_eilo_asr_destroy\n')
    dynamic=cache/'libeilo_joined_asr.dylib'
    subprocess.run(list(map(str,['xcrun','--sdk','iphonesimulator','clang++','-target','arm64-apple-ios18.0-simulator','-isysroot',sdk,'-dynamiclib',cache/'eilo_asr.o',moon/'libmoonshine.a','-framework','Accelerate','-framework','Foundation','-Wl,-twolevel_namespace','-Wl,-exported_symbols_list,'+str(exports),'-Wl,-install_name,@rpath/libeilo_joined_asr.dylib','-o',dynamic])),check=True)
    symbols=subprocess.run(['xcrun','nm','-gUj',str(dynamic)],check=True,capture_output=True,text=True).stdout.splitlines()
    if set(symbols)!=set(exports.read_text().splitlines()):raise ValueError('ASR export isolation failed')
    flags=subprocess.run(['xcrun','otool','-hv',str(dynamic)],check=True,capture_output=True,text=True).stdout
    if 'TWOLEVEL' not in flags:raise ValueError('ASR two-level namespace missing')
    sources=sorted((HERE.parent/'native-test-seam/Sources/NativeTestSeam').glob('*.swift'))
    libs=[llm.CACHE/i['file'] for i in record['libraries']]
    binary=cache/'ios-joined-turn'
    command=['xcrun','--sdk','iphonesimulator','swiftc','-swift-version','5','-warnings-as-errors','-target','arm64-apple-ios18.0-simulator','-sdk',sdk,'-parse-as-library','-D','DEBUG','-D','EILO_LLM_EVALUATION','-D','EILO_WAKE_EVALUATION','-D','EILO_ASR_EVALUATION','-I',llm.HERE/'include','-I',wake.HERE/'include','-I',asr.HERE/'include',*sources,HERE/'tests/ios_joined.swift',llm.CACHE/'build-ios-iphonesimulator/eilo_llm.o',*libs,wake_lib,*wake_link[:-1],dynamic,'-Xlinker','-rpath','-Xlinker',cache,'-framework','Accelerate','-framework','AVFoundation','-framework','Foundation','-framework','CryptoKit','-lc++','-o',binary]
    with (cache/'compile.log').open('w') as out:subprocess.run(list(map(str,command)),stdout=out,stderr=subprocess.STDOUT,check=True,timeout=180)
    manifest=json.loads((asr.HERE/'tests/fixtures.json').read_text());case=next(x for x in manifest['cases'] if x['id']=='quiet');question=asr.CACHE/'fixtures'/case['file']
    if asr.digest(question)!=case['sha256']:raise ValueError('ASR fixture integrity')
    wake_case=next(x for x in fixtures if x['file']=='ay-low-padded.wav');wake_audio=wake.CACHE/'fixtures'/wake_case['file']
    model=llm.PROVENANCE['model'];model_path=ROOT/'.local/model-build'/model['file']
    # Fixed generic fixture contains no personal history. No raw audio is logged.
    args=[binary,model_path,model['sha256'],model['bytes'],wake_model,wake_audio,asr_model,question]
    with (cache/'evaluation.log').open('w') as out:subprocess.run(list(map(str,['xcrun','simctl','spawn',a.udid,*args])),stdout=out,stderr=subprocess.STDOUT,check=True,timeout=420)
    lines=[x.removeprefix('EILO_JOIN_RESULT\t') for x in (cache/'evaluation.log').read_text().splitlines() if x.startswith('EILO_JOIN_RESULT\t')]
    if len(lines)!=1:raise ValueError('missing joined report')
    result=json.loads(lines[0]);result.update({'date':'2026-10-14','model':model,'runtime':llm.PROVENANCE['runtime'],'wake_fixture_sha256':wake_case['sha256'],'asr_fixture_sha256':case['sha256'],'combined_question_boundary':'Scripted fixture start; no calibrated wake-end timestamp','source_sha256':hashlib.sha256((HERE/'tests/ios_joined.swift').read_bytes()).hexdigest(),'ordinary_app_attachment':'NOT ENABLED','physical_airplane_mode_and_egress_capture':'NOT RUN','ASR_confidence':'Synthetic fixture confidence supplied; runtime does not provide calibrated confidence','VAD':'NOT ATTACHED; fixture end is scripted','offline_voice_evidence':'Synthetic exact installed voice/OS proof only; not production evidence','semantic_review':'pending_review','ASR_dynamic_export_isolation':'PASS: exactly four Eilo C exports; TWOLEVEL namespace','first_audible_and_user_heard':'NOT MEASURED'})
    (HERE/'tests/ios-joined-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Real wake -> native ASR -> signed CPU generation -> approved SDK speech: PASS (synthetic simulator; physical gates open).')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,subprocess.SubprocessError) as e:raise SystemExit('Joined iOS evaluation unavailable ('+type(e).__name__+'); see ignored logs.') from None
