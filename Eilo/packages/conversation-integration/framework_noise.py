"""Frozen paired direct/VAD-framework-ASR file replay; no confidence fit or device/audio access."""
import argparse
import array
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from check_framework_capture import HERE, framework_module, source_pins as joined_pins
sys.path.insert(0,str(HERE.parent/'vad-runtime'))
from check_installer import verify,verified_asr,verify_fixture,require,run,sha256

FLAGS=dict(physical='NOT_RUN',production='NOT_ENABLED',microphone='NOT_OPENED',speech='NOT_STARTED',llm='NOT_RUN',
    confidence='NOT_EVALUATED',calibration='NOT_ESTABLISHED',threshold='NOT_GRANTED',wake='NOT_ATTACHED',
    end_to_end_false_activation='NOT_MEASURED',pack_trust='SYNTHETIC_EVALUATOR_ONLY',release='HOLD',persistent_memory='DISABLED')


def policy():
    f=framework_module();p=f.read(HERE/'noise-protocol.json')
    prior=f.read(HERE.parent/'asr-calibration/negative-results.json')
    expected=dict(schema_version=1,purpose='PAIRED_IOS_DIRECT_VAD_ASR_NOISE_DIAGNOSTIC',
        trailing_silence_samples=32000,minimum_input_samples=80000,maximum_input_samples=480000,
        base_controls_sha256=prior['controls_sha256'],musan_manifest_sha256=prior['musan_manifest_sha256'],
        musan_labels='CORPUS_CATEGORY_WEAK_LABEL_NOT_VERIFIED_SPEECH_ABSENCE',synthetic_labels='NO_SPEECH_BY_CONSTRUCTION',
        pairing='SAME_IOS_RUNTIME_AND_PADDED_INPUT_DIFFERENT_ENDPOINT_CONSUMPTION',text_measure='NONEMPTY_NOT_WORD_ACCURACY',**FLAGS)
    require(type(p) is dict and set(p)==set(expected)|{'inputs'},'protocol schema changed')
    require(all(p[k]==v for k,v in expected.items()),'protocol policy changed')
    rows=p['inputs'];require(type(rows) is list and len(rows)==19,'nineteen frozen inputs required')
    require([r['group'] for r in rows]==['positive_question']+['musan_weak_noise']*12+['digital_silence']*3+['uniform_noise']*3,'input groups changed')
    for r in rows:
        require(set(r)=={'group','samples','sha256'} and type(r['samples']) is int and 80000<=r['samples']<=480000,'input bounds changed')
        require(type(r['sha256']) is str and len(r['sha256'])==64 and all(c in '0123456789abcdef' for c in r['sha256']),'input digest invalid')
    return p


def controls(manifest,cache):
    sys.path.insert(0,str(HERE.parent/'asr-calibration'))
    import negative
    rows,base,manifest_hash=negative.controls(manifest)
    prior=framework_module().read(HERE.parent/'asr-calibration/negative-results.json')
    require((base,manifest_hash)==(prior['controls_sha256'],prior['musan_manifest_sha256']),'frozen controls changed')
    raw,fixture=verify_fixture(cache)
    # Match the existing diagnostic's exact PCM before a frozen endpoint padding/cap.
    values=array.array('f');values.frombytes(raw)
    if sys.byteorder!='little':values.byteswap()
    inputs=[dict(group='positive_question',values=values)]
    for row in rows:
        pcm=array.array('h');pcm.frombytes(row['pcm'])
        if sys.byteorder!='little':pcm.byteswap()
        inputs.append(dict(group=row['group'],values=array.array('f',(v/32768 for v in pcm))))
    for row in inputs:
        row['values'].extend([0.0]*32000)
        row['values']=row['values'][:480000]
        if len(row['values'])<80000:row['values'].extend([0.0]*(80000-len(row['values'])))
        if sys.byteorder!='little':row['values'].byteswap()
        row['raw']=row.pop('values').tobytes()
    inventory=[dict(group=r['group'],samples=len(r['raw'])//4,sha256=hashlib.sha256(r['raw']).hexdigest()) for r in inputs]
    return inputs,inventory,base,manifest_hash


def pins():
    f=framework_module();paths={HERE.parent/r['path'] for r in joined_pins()}
    paths.update(HERE/n for n in ('framework_noise.py','tests/ios_framework_noise.swift','noise-protocol.json'))
    paths.update(HERE.parent/'asr-calibration'/n for n in ('negative.py','negative-protocol.json','negative-results.json','calibrate.py','noise_pilot.py'))
    # All imported control-generation helpers are bound by the prior negative inventory.
    prior=f.read(HERE.parent/'asr-calibration/negative-results.json')['source_pins']
    paths.update(HERE.parent/p for p in prior)
    return [dict(path=str(p.relative_to(HERE.parent)),sha256=sha256(p)) for p in sorted(paths)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('manifest','asr-cache','vad-cache','vad-model','framework','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--udid',required=True);p.add_argument('--protocol-commit',required=True);a=p.parse_args()
    f=framework_module();protocol=policy();before=pins()
    require(len(a.protocol_commit)==40 and all(c in '0123456789abcdef' for c in a.protocol_commit),'invalid protocol commit')
    subprocess.run(['git','merge-base','--is-ancestor',a.protocol_commit,'HEAD'],cwd=HERE.parents[2],check=True,capture_output=True)
    for name in ('framework_noise.py','tests/ios_framework_noise.swift','noise-protocol.json'):
        require(subprocess.check_output(['git','show',a.protocol_commit+':Eilo/packages/conversation-integration/'+name],cwd=HERE.parents[2])==(HERE/name).read_bytes(),'protocol/code not frozen')
    out=a.output.resolve();require(not out.exists(),'refusing overwrite')
    verify(a.vad_cache,a.vad_model);model,record=verified_asr(a.asr_cache)
    inputs,inventory,base,manifest_hash=controls(a.manifest,a.asr_cache)
    require(protocol['inputs']==inventory and protocol['base_controls_sha256']==base and protocol['musan_manifest_sha256']==manifest_hash,'input protocol mismatch')
    entries=f.xcframework_entries(a.framework.resolve());expected=f.read(HERE.parent/'asr-runtime/framework-results.json')
    require(all(entries[k][1]==expected['frameworks'][k] for k in entries),'reviewed framework changed')
    devices=json.loads(run(['xcrun','simctl','list','devices','booted','--json']))['devices']
    require(any(d['udid']==a.udid and d['state']=='Booted' and d.get('isAvailable') for ds in devices.values() for d in ds),'booted simulator required')
    out.mkdir(parents=True);client=out/'original/NoiseEvaluation.app';(client/'Frameworks').mkdir(parents=True)
    shutil.copytree(entries['iphonesimulator'][0],client/'Frameworks/CEiloAsr.framework')
    sdk=run(['xcrun','--sdk','iphonesimulator','--show-sdk-path']).strip();vad=HERE.parent/'vad-runtime'
    objects=[]
    for name in ('eilo_vad.cc','eilo_vad_onnx.cc'):
        obj=out/(Path(name).stem+'.o');objects.append(obj)
        run(['xcrun','clang++','-target','arm64-apple-ios18.0-simulator','-isysroot',sdk,'-std=c++17','-Wall','-Wextra','-Werror',
             '-I',vad/'include','-I',a.vad_cache/'ios/onnxruntime.xcframework/ios-arm64/onnxruntime.framework/Headers','-c',vad/name,'-o',obj])
    sources=sorted((HERE.parent/'native-test-seam/Sources/NativeTestSeam').glob('*.swift'))
    run(['xcrun','swiftc','-swift-version','5','-warnings-as-errors','-parse-as-library','-target','arm64-apple-ios18.0-simulator','-sdk',sdk,
         '-D','DEBUG','-D','EILO_ASR_EVALUATION','-D','EILO_VAD_EVALUATION','-I',vad/'include','-F',client/'Frameworks',*sources,
         HERE/'tests/ios_framework_noise.swift',*objects,'-framework','CEiloAsr','-F',a.vad_cache/'ios/onnxruntime.xcframework/ios-arm64_x86_64-simulator',
         '-framework','onnxruntime','-framework','CoreML','-framework','Accelerate','-framework','Foundation','-framework','AVFoundation','-framework','CryptoKit','-lc++',
         '-Xlinker','-rpath','-Xlinker','@executable_path/Frameworks','-o',client/'NoiseProbe'])
    relocated=out/'relocated/NoiseEvaluation.app';relocated.parent.mkdir();client.rename(relocated);require(not client.exists(),'original directory present')
    binary=relocated/'NoiseProbe';rpaths=f.client_metadata(run(['xcrun','otool','-L',binary]),run(['xcrun','otool','-l',binary]))
    with tempfile.TemporaryDirectory(prefix='eilo-frozen-noise-') as folder:
        stage=Path(folder)
        model_pins=[dict(id='asr-'+str(i),filename=r['file'],source=str((model/r['file']).resolve()),sha256=r['local_sha256'],bytes=r['bytes']) for i,r in enumerate(record['model']['files'])]
        model_pins.append(dict(id='vad',filename='silero.onnx',source=str(a.vad_model.resolve()),sha256=sha256(a.vad_model),bytes=a.vad_model.stat().st_size))
        manifest=stage/'models.json';manifest.write_text(json.dumps(model_pins));rows=[]
        for i,r in enumerate(inputs):
            path=stage/(str(i)+'.f32');path.write_bytes(r['raw']);rows.append(dict(path=str(path),group=r['group'],sha256=inventory[i]['sha256']))
        data=stage/'inputs.json';data.write_text(json.dumps(rows))
        executed=subprocess.run(list(map(str,['xcrun','simctl','spawn',a.udid,binary,manifest,data])),capture_output=True,text=True,timeout=900)
        (out/'evaluation.log').write_text(executed.stdout+executed.stderr);require(executed.returncode==0,'native noise evaluation failed')
        lines=[line.split('\t',1)[1] for line in executed.stdout.splitlines() if line.startswith('EILO_NOISE_RESULT\t')];require(len(lines)==1,'aggregate report required')
        execution=json.loads(lines[0])
    verify(a.vad_cache,a.vad_model);verified_asr(a.asr_cache)
    require(inventory==controls(a.manifest,a.asr_cache)[1] and before==pins(),'inputs/sources changed')
    report=dict(schema_version=1,purpose='PAIRED_IOS_DIRECT_VAD_ASR_NOISE_DIAGNOSTIC',protocol_commit=a.protocol_commit,source_pins=before,
        controls_sha256=base,musan_manifest_sha256=manifest_hash,framework=entries['iphonesimulator'][1],vad_model_sha256=sha256(a.vad_model),
        client_rpaths=rpaths,relocation='EXECUTED_WITH_ORIGINAL_CLIENT_DIRECTORY_ABSENT',binary_sha256=sha256(binary),execution=execution,**FLAGS)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Frozen paired iOS noise collection completed; inspect available/unavailable observations; no confidence/system qualification.')


if __name__=='__main__':main()
