"""Joined iOS-simulator and host-JVM native worker evaluation; no devices or capture."""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
from check_native import HERE, run, verify
from manifests import require, sha256

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cache','model','output','java-home','android-sdk','jni-build'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--udid',required=True)
    p.add_argument('--capture',action='store_true',help='Evaluate the bounded callback-to-worker transport')
    args=p.parse_args()
    probe_name='swift_capture_probe.swift' if args.capture else 'swift_worker_probe.swift'
    jvm_name='NativeVadCaptureRuntimeTest' if args.capture else 'NativeVadRuntimeTest'
    cache=args.cache.resolve();model=args.model.resolve();output=args.output.resolve();jni=args.jni_build.resolve()
    verify(cache,model)
    record=json.loads((jni/'results.json').read_text())
    require(sha256(jni/'libeilo_vad_jni.dylib')==record['host_jni_sha256'],'JNI binary changed')
    for name,digest in record['source_sha256'].items():require(sha256(HERE/name)==digest,'JNI source changed')
    devices=json.loads(run(['xcrun','simctl','list','devices','booted','--json']))
    require(any(d['udid']==args.udid and d['name']=='iPhone 18 Pro' and d['isAvailable']
                for rows in devices['devices'].values() for d in rows),'same simulator required')
    require(not output.exists(),'refusing to overwrite evidence');output.mkdir(parents=True)
    sdk=run(['xcrun','--sdk','iphonesimulator','--show-sdk-path']).strip()
    framework=cache/'ios/onnxruntime.xcframework/ios-arm64_x86_64-simulator'
    headers=cache/'ios/onnxruntime.xcframework/ios-arm64/onnxruntime.framework/Headers'
    objects=[]
    for source in (HERE/'eilo_vad.cc',HERE/'eilo_vad_onnx.cc'):
        obj=output/(source.stem+'.o');objects.append(obj)
        run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-target','arm64-apple-ios18.0-simulator',
             '-isysroot',sdk,'-I',HERE/'include','-I',headers,'-c',source,'-o',obj])
    swift=[HERE.parent/'native-test-seam/Sources/NativeTestSeam'/name for name in
           ('EndpointDetector.swift','NativeVadStream.swift','VadWindowDelivery.swift')]
    if args.capture:swift=sorted((HERE.parent/'native-test-seam/Sources/NativeTestSeam').glob('*.swift'))
    probe=output/'worker-probe'
    run(['xcrun','swiftc','-parse-as-library','-D','DEBUG','-D','EILO_VAD_EVALUATION',
         '-target','arm64-apple-ios18.0-simulator','-sdk',sdk,'-I',HERE/'include',*swift,
         HERE/'tests'/probe_name,*objects,'-F',framework,'-framework','onnxruntime',
         '-framework','CoreML','-framework','Foundation','-lc++','-o',probe])
    runtime=cache/'sherpa-onnx-v1.13.8-osx-arm64-shared-no-tts/lib/libonnxruntime.dylib'
    with tempfile.TemporaryDirectory(prefix='eilo-vad-worker-') as folder:
        temp=Path(folder)
        staged={probe:temp/'worker',model:temp/'model.onnx',runtime:temp/runtime.name,
                jni/'libeilo_vad_jni.dylib':temp/'libeilo_vad_jni.dylib'}
        for source,target in staged.items():
            shutil.copy2(source,target);require(sha256(source)==sha256(target),'temporary copy changed')
        ios=json.loads(run(['xcrun','simctl','spawn',args.udid,staged[probe],staged[model]]))
        project=HERE.parents[1]/'apps/mobile/android'
        init=output/'native-worker.init.gradle'
        properties={'eilo.vad.model':str(staged[model]),'eilo.vad.runtime':str(staged[runtime]),
                    'eilo.vad.wrapper':str(staged[jni/'libeilo_vad_jni.dylib']),
                    'eilo.vad.runtimeSha':sha256(runtime),'eilo.vad.wrapperSha':record['host_jni_sha256'],
                    'eilo.vad.result':str(output/'jvm-results.json')}
        text='gradle.afterProject { p ->\n if (p.path == ":app") {\n p.android.sourceSets.test.java.srcDir('+json.dumps(str(HERE/'tests/jvm'))+')\n'
        text+=' p.tasks.withType(org.gradle.api.tasks.testing.Test).configureEach {\n'
        for key,value in properties.items():text+=' systemProperty '+json.dumps(key)+', '+json.dumps(value)+'\n'
        text+=' }\n }\n}\n';init.write_text(text)
        import subprocess
        env=dict(os.environ,JAVA_HOME=str(args.java_home),ANDROID_HOME=str(args.android_sdk))
        executed=subprocess.run([str(project/'gradlew'),'-p',str(project),'-I',str(init),':app:testDebugUnitTest',
                                '--tests','com.eilo.foundation.'+jvm_name,'--offline','--max-workers=2'],
                               env=env,capture_output=True,text=True,timeout=300)
        (output/'jvm-build.log').write_text(executed.stdout+executed.stderr)
        require(executed.returncode==0,'host JNI probe failed; inspect local build log')
        jvm=json.loads((output/'jvm-results.json').read_text())
    android=project/'app/src/main/java/com/eilo/foundation'
    sources=[*swift,android/'EndpointDetector.kt',android/'NativeVadStream.kt',android/'VadWindowDelivery.kt',
             HERE/'eilo_vad_jni.cc',HERE/'tests'/probe_name,HERE/'tests/jvm'/(jvm_name+'.kt')]
    if args.capture:sources.extend(android/name for name in ('VadCaptureTransport.kt','VadAsrHandoff.kt','StreamingAsr.kt','StreamingRateConverter.kt','SpeechPackLease.kt','PackManifest.kt'))
    result={'schema_version':1,'scope':'JOINED_NATIVE_VAD_CAPTURE_TRANSPORT_SYNTHETIC' if args.capture else 'JOINED_NATIVE_VAD_WORKER_SYNTHETIC','ios_simulator':ios,'host_jvm_jni':jvm,
            'model_sha256':sha256(model),'jni_sha256':record['host_jni_sha256'],
            'source_sha256':{str(p.relative_to(HERE.parents[1])):sha256(p) for p in sources},
            'android_device_execution':'NOT_RUN','production_readiness':'NOT_ENABLED','physical_gates':'NOT_RUN'}
    (output/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Joined iOS simulator and host-JVM/JNI '+('capture transports' if args.capture else 'workers')+' PASS; physical/Android-device NOT_RUN.')
