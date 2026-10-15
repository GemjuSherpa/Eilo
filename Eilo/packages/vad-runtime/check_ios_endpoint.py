"""Actual native VAD -> Swift endpoint on the existing simulator; synthetic silence only."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from check_native import HERE, run, verify
from manifests import require, sha256

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--udid',required=True)
    args=parser.parse_args();cache=args.cache.resolve();model=args.model.resolve();output=args.output.resolve()
    verify(cache,model)
    inventory=json.loads(run(['xcrun','simctl','list','devices','booted','--json']))
    require(any(d['udid']==args.udid and d['name']=='iPhone 18 Pro' and d['isAvailable']
                for rows in inventory['devices'].values() for d in rows),'same simulator required')
    require(not output.exists(),'refusing to overwrite evidence');output.mkdir(parents=True)
    sdk=run(['xcrun','--sdk','iphonesimulator','--show-sdk-path']).strip()
    framework=cache/'ios/onnxruntime.xcframework/ios-arm64_x86_64-simulator'
    headers=cache/'ios/onnxruntime.xcframework/ios-arm64/onnxruntime.framework/Headers'
    objects=[]
    for source in (HERE/'eilo_vad.cc',HERE/'eilo_vad_onnx.cc'):
        obj=output/(source.stem+'.o');objects.append(obj)
        run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-target','arm64-apple-ios18.0-simulator',
             '-isysroot',sdk,'-I',HERE/'include','-I',headers,'-c',source,'-o',obj])
    source=HERE.parent/'native-test-seam/Sources/NativeTestSeam/EndpointDetector.swift'
    probe=output/'endpoint-probe'
    run(['xcrun','swiftc','-parse-as-library','-target','arm64-apple-ios18.0-simulator','-sdk',sdk,
         '-I',HERE/'include',source,HERE/'tests/swift_endpoint_probe.swift',*objects,
         '-F',framework,'-framework','onnxruntime','-framework','CoreML','-framework','Foundation','-lc++','-o',probe])
    with tempfile.TemporaryDirectory(prefix='eilo-vad-endpoint-') as folder:
        temp_probe=Path(folder)/'probe';temp_model=Path(folder)/'model.onnx'
        shutil.copy2(probe,temp_probe);shutil.copyfile(model,temp_model)
        require(sha256(temp_probe)==sha256(probe) and sha256(temp_model)==sha256(model),'copy changed')
        result=json.loads(run(['xcrun','simctl','spawn',args.udid,temp_probe,temp_model]))
    result.update({'endpoint_source_sha256':sha256(source),'probe_source_sha256':sha256(HERE/'tests/swift_endpoint_probe.swift'),
                   'model_sha256':sha256(model),'normal_app_readiness':'NOT_ENABLED'})
    (output/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Native VAD -> Swift endpoint PASS on synthetic silence; physical NOT_RUN.')
