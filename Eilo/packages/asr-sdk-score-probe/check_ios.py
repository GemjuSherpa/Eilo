"""Isolated cached-source iOS simulator score diagnostic; no ordinary runtime replacement."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import wave

HERE=Path(__file__).resolve().parent
PACKAGES=HERE.parent


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


f=module('ios_score_framework',PACKAGES/'asr-runtime/framework.py')
FLAGS=dict(calibrated=False,policy_authorized=False,physical='NOT_RUN',ordinary_runtime='NOT_REPLACED',
           microphone='NOT_OPENED',speech='NOT_STARTED',llm='NOT_RUN',release='HOLD',persistent_memory='DISABLED',
           calibration_transfer='NOT_AUTHORIZED',execution_provider='SOURCE_DEFAULT_NOT_INDEPENDENTLY_PROFILED')


def pins():
    paths=[HERE/n for n in ('check_ios.py','ios/CMakeLists.txt','main.cpp','score_trace.h','overlay.py','overlay-expected.json','report.py')]
    paths += [PACKAGES/'asr-confidence-probe'/n for n in ('source-manifest.json','SOURCE_REVIEW.md')]
    paths += [PACKAGES/'asr-runtime'/n for n in ('framework.py','provenance.json','tests/fixtures.json')]
    paths += [PACKAGES/'wake-runtime/ios-provenance.json',HERE/'check_android.py']
    return [dict(path=str(p.relative_to(PACKAGES)),sha256=f.sha(p)) for p in sorted(paths)]


def verify_ort(cache):
    records=f.read(PACKAGES/'wake-runtime/ios-provenance.json')['archives']
    records=[r for r in records if r['version']=='1.28.2'];f.need(len(records)==1);r=records[0]
    root=(cache/'ios').resolve();f.need(f.sha(root/r['file'])==r['sha256'])
    for row in r['files']:
        path=(root/row['path']).resolve();f.need(path.is_relative_to(root) and f.sha(path)==row['sha256'])
    binary=root/'onnxruntime.xcframework/ios-arm64_x86_64-simulator/onnxruntime.framework/onnxruntime'
    f.need(binary.is_file());return binary,r


def verify_fixtures(cache):
    record=f.read(PACKAGES/'asr-runtime/tests/fixtures.json')
    for case in record['cases']:
        path=cache/'fixtures'/case['file'];f.need(f.sha(path)==case['sha256'])
        with wave.open(str(path),'rb') as audio:
            f.need((audio.getframerate(),audio.getnchannels(),audio.getsampwidth(),audio.getnframes())==(16000,1,2,case['samples']))
    return record['cases']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('source','asr-cache','ort-cache','cmake','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--udid',required=True);a=p.parse_args()
    source=a.source.resolve();cache=a.asr_cache.resolve();out=a.output.resolve();f.need(not out.exists())
    checker=module('ios_score_source_checker',HERE/'check_android.py');checker.verify_source(source)
    model,provenance=f.verify_asr(cache);ort,ort_record=verify_ort(a.ort_cache);fixtures=verify_fixtures(cache);before=pins()
    devices=json.loads(f.run(['xcrun','simctl','list','devices','booted','--json']))['devices']
    f.need(any(d['udid']==a.udid and d['state']=='Booted' and d.get('isAvailable') for ds in devices.values() for d in ds))
    out.mkdir(parents=True)
    overlay=module('ios_score_overlay',HERE/'overlay.py').generate(source,out/'overlay')
    f.need(overlay==f.read(HERE/'overlay-expected.json'))
    sdk=f.run(['xcrun','--sdk','iphonesimulator','--show-sdk-path']).strip();build=out/'build'
    config=[a.cmake,'-S',HERE/'ios','-B',build,'-DCMAKE_SYSTEM_NAME=iOS','-DCMAKE_OSX_SYSROOT='+sdk,
            '-DCMAKE_OSX_ARCHITECTURES=arm64','-DCMAKE_OSX_DEPLOYMENT_TARGET=18.0','-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY','-DCMAKE_SKIP_RPATH=ON','-DSOURCE_ROOT='+str(source),
            '-DOVERLAY='+str(out/'overlay'),'-DORT_LIBRARY='+str(ort)]
    with (out/'build.log').open('w') as log:
        subprocess.run(list(map(str,config)),check=True,stdout=log,stderr=log,timeout=180)
        subprocess.run(list(map(str,[a.cmake,'--build',build,'-j','2'])),check=True,stdout=log,stderr=log,timeout=600)
    original=build/'sdk-score-probe';relocated=out/'relocated/sdk-score-probe';relocated.parent.mkdir();original.rename(relocated);f.need(not original.exists())
    f.need(f.run(['xcrun','lipo','-archs',relocated]).strip()=='arm64')
    target=f.run(['xcrun','vtool','-show-build',relocated]);f.need(re.search(r'platform\s+IOSSIMULATOR\b',target) and re.search(r'minos\s+18\.0\b',target))
    dependencies=[line.strip().split(' (')[0] for line in f.run(['xcrun','otool','-L',relocated]).splitlines()[1:]]
    f.need(all(d.startswith(('/System/Library/Frameworks/','/usr/lib/')) for d in dependencies))
    rpaths=re.findall(r'cmd LC_RPATH\s+cmdsize \d+\s+path (.*?) \(offset \d+\)',f.run(['xcrun','otool','-l',relocated]));f.need(not rpaths)
    results=[]
    with tempfile.TemporaryDirectory(prefix='eilo-ios-score-') as folder:
        raw=Path(folder)/'input.f32'
        def invoke(data):
            raw.write_bytes(data)
            return subprocess.run(list(map(str,['xcrun','simctl','spawn',a.udid,relocated,model,raw])),capture_output=True,text=True,timeout=240)
        for case in fixtures:
            path=cache/'fixtures'/case['file']
            with wave.open(str(path),'rb') as audio:pcm=audio.readframes(audio.getnframes())
            samples=struct.unpack('<'+'h'*(len(pcm)//2),pcm);result=invoke(struct.pack('<'+'f'*len(samples),*(x/32768 for x in samples)))
            (out/(case['id']+'.log')).write_text(result.stdout+result.stderr)
            if result.returncode:
                (out/'failed-case.json').write_text(json.dumps(dict(case=case['id'],native_returncode=result.returncode))+'\n')
                raise RuntimeError('isolated iOS score fixture failed; inspect local diagnostic log')
            rows=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')];f.need(len(rows)==8)
            results.append(dict(case=case['id'],paths=rows[:6],shape_comparison=rows[6],faults=rows[7]))
            (out/'progress.json').write_text(json.dumps(results,indent=2)+'\n');print('Verified iOS fixture:',case['id'],flush=True)
        rejected=[]
        for name,data in [('empty',b''),('unaligned',b'x'),('nan',struct.pack('<f',float('nan'))),('out_of_range',struct.pack('<f',2))]:
            result=invoke(data);f.need(result.returncode!=0 and not any(line.startswith('{') for line in result.stdout.splitlines()));rejected.append(name)
        raw.write_bytes(bytes(raw.stat().st_size));raw.unlink()
    checker.verify_source(source);f.verify_asr(cache);verify_ort(a.ort_cache);verify_fixtures(cache);f.need(before==pins())
    # Original source experiments plus this probe remain below the approved cumulative cap.
    local=PACKAGES.parent/'.local';f.need(sum(p.stat().st_size for name in ('asr-sdk-score','asr-confidence') for p in (local/name).rglob('*') if p.is_file())<5*1024**3)
    report=dict(schema_version=1,purpose='IOS_SOURCE_SDK_SCORE_DIAGNOSTIC_ONLY',platform='ARM64_IOS_SIMULATOR_18_MINIMUM',
        source_commit=f.read(PACKAGES/'asr-confidence-probe/source-manifest.json')['commit'],source_pins=before,overlay_pins=overlay,
        ort_version='1.28.2',ort_archive_sha256=ort_record['sha256'],ort_binary_sha256=f.sha(ort),binary_sha256=f.sha(relocated),
        relocation='EXECUTED_WITH_ORIGINAL_BINARY_ABSENT',custom_dynamic_dependencies='NONE',rpaths=rpaths,
        rejected_inputs=rejected,cases=results,**FLAGS)
    (out/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('Isolated iOS source score diagnostic completed; no calibration or ordinary-runtime authorization.')


if __name__=='__main__':main()
