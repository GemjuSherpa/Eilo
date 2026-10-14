"""Offline pinned native VAD compilation/execution; never downloads or opens capture."""
import argparse
import ctypes as C
import json
from pathlib import Path
import subprocess
import shutil
import tempfile
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'dataset-evaluation'))
from audio import RATE, read_wav
from benchmark import PHYSICAL_GATES, validate_manifest
from manifests import canonical_digest, require, safe_path, sha256


def run(args):
    return subprocess.run(list(map(str,args)), check=True, capture_output=True, text=True, timeout=180).stdout


def verify(cache, model):
    provenance = json.loads((HERE / 'provenance.json').read_text())
    ios = json.loads((HERE.parent / 'wake-runtime/ios-provenance.json').read_text())
    for archive in ios['archives']:
        if archive['version'] != '1.28.2':
            continue
        require(sha256(cache / 'ios' / archive['file']) == archive['sha256'], 'ONNX archive changed')
        for item in archive['files']:
            require(sha256(safe_path(cache / 'ios', item['path'])) == item['sha256'], 'ONNX framework changed')
    for item in provenance['build_inputs']:
        require(sha256(safe_path(cache, item['path'])) == item['sha256'], 'build input changed')
    require(sha256(model) == provenance['model_sha256'] and model.stat().st_size == 2313101, 'model changed')
    return provenance


def build(cache, output, sdk=None, slice_name=None):
    headers=cache/'ios/onnxruntime.xcframework/ios-arm64/onnxruntime.framework/Headers'
    base=['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-I',HERE/'include','-I',headers]
    sources=[HERE/'eilo_vad.cc',HERE/'eilo_vad_onnx.cc']
    if sdk:
        target='arm64-apple-ios18.0' + ('-simulator' if sdk=='iphonesimulator' else '')
        framework=cache/'ios/onnxruntime.xcframework'/slice_name
        flags=['-target',target,'-isysroot',run(['xcrun','--sdk',sdk,'--show-sdk-path']).strip(),
               '-F',framework,'-framework','onnxruntime','-framework','CoreML','-framework','Foundation','-Wl,-rpath,'+str(framework)]
        if sdk=='iphoneos':
            for source in sources:
                run([*base,*flags[:4],'-c',source,'-o',output/(source.stem+'-device.o')])
            return None
        target_path=output/'vad-ios-probe'
        run([*base,*flags,*sources,HERE/'tests/probe.cc','-o',target_path])
        return target_path
    libdir=cache/'sherpa-onnx-v1.13.8-osx-arm64-shared-no-tts/lib'
    flags=['-L',libdir,'-lonnxruntime','-Wl,-rpath,'+str(libdir)]
    library=output/'libeilo_vad.dylib'
    run([*base,*sources,*flags,'-fPIC','-shared','-o',library])
    probe=output/'vad-host-probe'
    run([*base,*sources,HERE/'tests/probe.cc',*flags,'-o',probe])
    return library,probe


class Frame(C.Structure):
    _fields_=[('probability',C.c_float),('start_sample',C.c_int32),('samples',C.c_int32),('final_frame',C.c_int32)]


def corpus(library, model, path):
    manifest=validate_manifest(json.loads(path.read_text()),path.parent)
    lib=C.CDLL(str(library))
    lib.eilo_vad_create.argtypes=[C.c_char_p];lib.eilo_vad_create.restype=C.c_void_p
    lib.eilo_vad_process.argtypes=[C.c_void_p,C.POINTER(C.c_float),C.c_int32,C.c_int32,C.POINTER(Frame)]
    lib.eilo_vad_process.restype=C.c_int32
    lib.eilo_vad_destroy.argtypes=[C.c_void_p];lib.eilo_vad_destroy.restype=None
    total=windows=high=low=0
    for case in manifest['cases']:
        samples=read_wav(safe_path(path.parent,case['path']))
        stream=lib.eilo_vad_create(str(model).encode());require(stream,'native open failed')
        try:
            for start in range(0,len(samples),512):
                chunk=samples[start:start+512];buffer=(C.c_float*len(chunk))(*(x/32768 for x in chunk))
                frame=Frame()
                try:
                    code=lib.eilo_vad_process(stream,buffer,len(chunk),int(start+len(chunk)==len(samples)),C.byref(frame))
                    require(code==0 and frame.start_sample==start and frame.samples==len(chunk)
                            and 0<=frame.probability<=1,'invalid native frame')
                    windows+=1;high+=int(frame.probability>=.8);low+=int(frame.probability<=.2)
                    total+=frame.samples
                finally:
                    C.memset(C.addressof(buffer),0,C.sizeof(buffer))
        finally:
            lib.eilo_vad_destroy(stream)
    return {'dataset':manifest['dataset'],'manifest_sha256':canonical_digest(manifest),'clips':len(manifest['cases']),
            'valid_samples':total,'native_windows':windows,'windows_ge_0_8':high,'windows_le_0_2':low,
            'status':'EXECUTED_UNSCORED','quality_acceptance':'NOT_ASSESSED'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',required=True,type=Path)
    parser.add_argument('--model',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--manifest',action='append',type=Path,default=[])
    parser.add_argument('--ios-simulator')
    parser.add_argument('--ndk',type=Path)
    args=parser.parse_args();cache=args.cache.resolve();model=args.model.resolve();output=args.output.resolve()
    require(not output.exists(),'refusing to overwrite native evidence')
    pinned=verify(cache,model);output.mkdir(parents=True)
    library,probe=build(cache,output)
    result={'schema_version':1,'scope':'NATIVE_PROBABILITY_CORE_EVALUATION','host':json.loads(run([probe,model])),
            'provenance_sha256':canonical_digest(pinned),'library_sha256':sha256(library),
            'source_sha256':{p.name:sha256(p) for p in (HERE/'eilo_vad.cc',HERE/'eilo_vad_onnx.cc',HERE/'include/eilo_vad.h')},
            'corpora':[corpus(library,model,p.resolve()) for p in args.manifest],
            'physical_gates':{x:'NOT_RUN' for x in PHYSICAL_GATES},'production_readiness':'NOT_ENABLED'}
    (output/'host-results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    if args.ios_simulator:
        devices=json.loads(run(['xcrun','simctl','list','devices','booted','--json']))
        selected=[d for rows in devices['devices'].values() for d in rows if d['udid']==args.ios_simulator and d['isAvailable']]
        require(len(selected)==1 and selected[0]['name']=='iPhone 18 Pro','same booted simulator required')
        probe=build(cache,output,'iphonesimulator','ios-arm64_x86_64-simulator')
        # Simulator launchd may lack Documents/Desktop access. Use local temporary copies,
        # verified byte-for-byte, instead of requesting broader filesystem permission.
        with tempfile.TemporaryDirectory(prefix='eilo-vad-sim-') as folder:
            temp_probe=Path(folder)/'vad-probe';temp_model=Path(folder)/'model.onnx'
            shutil.copy2(probe,temp_probe);shutil.copyfile(model,temp_model)
            require(sha256(temp_probe)==sha256(probe) and sha256(temp_model)==sha256(model),'temporary copy changed')
            result['ios_simulator']=json.loads(run(['xcrun','simctl','spawn',args.ios_simulator,temp_probe,temp_model]))
        build(cache,output,'iphoneos','ios-arm64');result['ios_device_compile']='PASS_NOT_EXECUTED'
    if args.ndk:
        headers=cache/'ios/onnxruntime.xcframework/ios-arm64/onnxruntime.framework/Headers'
        result['android_compile']={}
        for abi,triple in [('arm64-v8a','aarch64-linux-android'),('armeabi-v7a','armv7a-linux-androideabi'),
                           ('x86_64','x86_64-linux-android'),('x86','i686-linux-android')]:
            compiler=args.ndk/'toolchains/llvm/prebuilt/darwin-x86_64/bin'/(triple+'24-clang++')
            for source in (HERE/'eilo_vad.cc',HERE/'eilo_vad_onnx.cc'):
                run([compiler,'-std=c++17','-Wall','-Wextra','-Werror','-I',HERE/'include','-I',headers,
                     '-c',source,'-o',output/(source.stem+'-'+abi+'.o')])
            result['android_compile'][abi]='PASS_OBJECTS_ONLY_NOT_LINKED_OR_EXECUTED'
    (output/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('Native VAD evaluation complete; physical gates NOT_RUN, production NOT_ENABLED.')
