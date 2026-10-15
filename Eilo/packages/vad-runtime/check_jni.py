"""Offline JNI builds with existing runtime/toolchains; no device or library loading."""
import argparse
import json
from pathlib import Path
from check_native import HERE, run, verify
from manifests import require, sha256

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cache','model','output','java-home','ndk'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();cache=args.cache.resolve();output=args.output.resolve()
    verify(cache,args.model.resolve())
    record=json.loads((HERE.parent/'wake-runtime/android-provenance.json').read_text())['archive']
    require(sha256(cache/'android'/record['file'])==record['sha256'],'Android runtime archive changed')
    for item in record['files']:
        require(sha256(cache/'android'/item['path'])==item['sha256'],'Android extracted file changed')
    require('Pkg.Revision = 27.1.12297006' in (args.ndk/'source.properties').read_text(),'unexpected NDK')
    require(not output.exists(),'refusing to overwrite evidence');output.mkdir(parents=True)
    sources=[HERE/'eilo_vad.cc',HERE/'eilo_vad_onnx.cc',HERE/'eilo_vad_jni.cc']
    headers=cache/'ios/onnxruntime.xcframework/ios-arm64/onnxruntime.framework/Headers'
    common=['-std=c++17','-Wall','-Wextra','-Werror','-fPIC','-shared','-I',HERE/'include','-I',headers]
    hostlib=cache/'sherpa-onnx-v1.13.8-osx-arm64-shared-no-tts/lib'
    host=output/'libeilo_vad_jni.dylib'
    run(['xcrun','clang++',*common,'-I',args.java_home/'include','-I',args.java_home/'include/darwin',
         *sources,'-L',hostlib,'-lonnxruntime','-Wl,-rpath,'+str(hostlib),'-o',host])
    result={'scope':'JNI_LINK_ONLY','host_jni_sha256':sha256(host),'android':{},
            'source_sha256':{str(p.relative_to(HERE)):sha256(p) for p in [*sources,HERE/'include/eilo_vad.h',HERE/'vad_backend.h']}}
    tools=args.ndk/'toolchains/llvm/prebuilt/darwin-x86_64/bin'
    for abi,triple in [('arm64-v8a','aarch64-linux-android'),('armeabi-v7a','armv7a-linux-androideabi'),
                       ('x86_64','x86_64-linux-android'),('x86','i686-linux-android')]:
        libs=cache/'android/jniLibs'/abi;target=output/abi/'libeilo_vad_jni.so';target.parent.mkdir()
        run([tools/(triple+'24-clang++'),*common,'-static-libstdc++','-Wl,--no-undefined',
             '-Wl,-z,max-page-size=16384',*sources,'-L',libs,'-Wl,-rpath-link,'+str(libs),
             '-lonnxruntime','-o',target])
        result['android'][abi]={'status':'LINKED_NOT_EXECUTED','sha256':sha256(target)}
    (output/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Host and four Android JNI links PASS; no device execution claim.')
