"""Opt-in unsigned simulator app build with Xcode-managed ASR framework embedding.
The shipping project and runtime flags are unchanged; no models or capture are enabled.
Requires preinstalled local Pods/node modules. No installer or download fallback exists.
"""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import time
import uuid
from xml.sax.saxutils import escape
from framework import HERE, PACKAGES, NAME, INSTALL, need, read, sha, run, xcframework_entries, inspect_bundle

ROOT=PACKAGES.parent
IOS=ROOT/'apps/mobile/ios'
BUNDLE='org.reactjs.native.example.Eilo'
IDS=[f'A5F0{i:020X}' for i in range(1,5)]
FLAGS=dict(physical='NOT_RUN',ordinary_voice='NOT_ENABLED',release='HOLD',persistent_memory='DISABLED',
           signing='NOT_REVIEWED',distribution='NOT_APPROVED',model_loading='NOT_RUN',microphone='NOT_OPENED')


def pins():
    paths={HERE/'app_framework.py',HERE/'app_framework_probe.swift',HERE/'framework.py',HERE/'framework-results.json',
           IOS/'Eilo.xcodeproj/project.pbxproj',IOS/'Podfile.lock',ROOT/'package-lock.json',ROOT/'scripts/verify-ios-launch.py'}
    for pattern in ('apps/mobile/ios/Eilo/*.swift','apps/mobile/ios/Eilo/*.mm','apps/mobile/src/**/*','apps/mobile/*.json','apps/mobile/*.js','packages/native-test-seam/Sources/NativeTestSeam/*.swift'):
        paths.update(p for p in ROOT.glob(pattern) if p.is_file())
    return [dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(paths)]


def project(original,bundle):
    """Modify an in-memory project only; fail on unexpected target structure."""
    need(type(original) is dict and len(IDS)==len(set(IDS)))
    p=plistlib.loads(plistlib.dumps(original));objects=p['objects'];need(not set(IDS)&set(objects))
    targets=[v for v in objects.values() if v.get('isa')=='PBXNativeTarget' and v.get('name')=='Eilo']
    need(len(targets)==1);target=targets[0]
    phases=[objects[k] for k in target['buildPhases'] if objects[k]['isa']=='PBXFrameworksBuildPhase'];need(len(phases)==1)
    ref,link,embed,phase=IDS
    objects[ref]=dict(isa='PBXFileReference',lastKnownFileType='wrapper.framework',name=NAME+'.framework',path=str(bundle),sourceTree='<absolute>')
    objects[link]=dict(isa='PBXBuildFile',fileRef=ref)
    objects[embed]=dict(isa='PBXBuildFile',fileRef=ref,settings=dict(ATTRIBUTES=['RemoveHeadersOnCopy']))
    objects[phase]=dict(isa='PBXCopyFilesBuildPhase',buildActionMask='2147483647',dstPath='',dstSubfolderSpec='10',files=[embed],name='Embed evaluated ASR framework',runOnlyForDeploymentPostprocessing='0')
    phases[0]['files'].append(link);target['buildPhases'].append(phase)
    configurations=[objects[k] for k in objects[target['buildConfigurationList']]['buildConfigurations']]
    need({c['name'] for c in configurations}=={'Debug','Release'})
    for c in configurations:
        settings=c['buildSettings'];settings['IPHONEOS_DEPLOYMENT_TARGET']='18.0'
        settings['FRAMEWORK_SEARCH_PATHS']=['$(inherited)',str(bundle.parent)]
        settings['COPY_PHASE_STRIP']='NO'
        settings['CODE_SIGNING_ALLOWED']='NO';settings['CODE_SIGNING_REQUIRED']='NO';settings['CODE_SIGN_IDENTITY']=''
    return p


def app_metadata(app,expected):
    info=plistlib.loads((app/'Info.plist').read_bytes())
    need(info['CFBundleIdentifier']==BUNDLE and info['CFBundleExecutable']=='Eilo' and info['CFBundleSupportedPlatforms']==['iPhoneSimulator'])
    need(not (app/'embedded.mobileprovision').exists() and not (app/'_CodeSignature').exists())
    signature=subprocess.run(['codesign','-dv','--verbose=2',str(app/'Eilo')],capture_output=True,text=True,timeout=30)
    if signature.returncode==0:
        need('Signature=adhoc' in signature.stderr and 'Authority=' not in signature.stderr);signing='TOOLCHAIN_AD_HOC'
    else:
        need('code object is not signed at all' in signature.stderr);signing='UNSIGNED'
    embedded=app/'Frameworks/CEiloAsr.framework'
    # Xcode's RemoveHeadersOnCopy removes headers/modules; inspect unchanged binary/metadata.
    need((embedded/NAME).is_file() and sha(embedded/NAME)==expected['sha256'])
    need(sha(embedded/'Info.plist')==expected['info_sha256'])
    loads=run(['xcrun','otool','-L',app/'Eilo']).splitlines()[1:]
    deps=[s.strip().split(' (')[0] for s in loads];need(INSTALL in deps)
    need(all(s==INSTALL or s.startswith(('/System/Library/Frameworks/','/usr/lib/','@rpath/')) for s in deps))
    commands=run(['xcrun','otool','-l',app/'Eilo'])
    rpaths=re.findall(r'cmd LC_RPATH\s+cmdsize \d+\s+path (.*?) \(offset \d+\)',commands)
    need('@executable_path/Frameworks' in rpaths and all(s in ('/usr/lib/swift','@executable_path/Frameworks','@loader_path/Frameworks') for s in rpaths))
    need(not any(p.suffix.lower() in ('.gguf','.onnx','.ort','.f32','.wav','.mp3') for p in app.rglob('*') if p.is_file()))
    entries=[dict(path=str(p.relative_to(app)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(app.rglob('*')) if p.is_file()]
    need(not any(p.is_symlink() for p in app.rglob('*')))
    tree=hashlib.sha256(json.dumps(entries,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return dict(binary_sha256=sha(app/'Eilo'),tree_sha256=tree,files=len(entries),framework_sha256=sha(embedded/NAME),
                code_signature=signing,platform='iPhoneSimulator',configuration='Release',architecture=run(['xcrun','lipo','-archs',app/'Eilo']).strip(),
                rpaths=rpaths,required_framework_load=True,packaged_model_audio_extensions='NONE_OBSERVED')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('framework','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--udid',required=True);a=p.parse_args();out=a.output.resolve();need(not out.exists())
    need((ROOT/'node_modules').is_dir() and (IOS/'Pods/Pods.xcodeproj').is_dir() and not (IOS/'Pods').is_symlink())
    need(all((IOS/'build'/n).is_dir() for n in ('rncore-facades','rndeps-facades')))
    need((IOS/'Pods/Manifest.lock').read_bytes()==(IOS/'Podfile.lock').read_bytes())
    devices=json.loads(run(['xcrun','simctl','list','devices','booted','--json']))['devices']
    need(any(d['udid']==a.udid and d['state']=='Booted' and d.get('isAvailable') for ds in devices.values() for d in ds))
    archive_names=('ReactNativeCore-artifacts/reactnative-core-0.87.1-release.tar.gz',
                   'ReactNativeDependencies-artifacts/reactnative-dependencies-0.87.1-release.tar.gz',
                   'hermes-engine-artifacts/hermes-ios-250829098.0.17-release.tar.gz')
    archives=[IOS/'Pods'/n for n in archive_names];need(all(p.is_file() for p in archives))
    archive_pins=[dict(name=n,bytes=p.stat().st_size,sha256=sha(p)) for n,p in zip(archive_names,archives)]
    before=pins();entries=xcframework_entries(a.framework.resolve());expected=read(HERE/'framework-results.json')
    need(all(entries[k][1]==expected['frameworks'][k] for k in entries))
    bundle=entries['iphonesimulator'][0];out.mkdir(parents=True)
    original=plistlib.loads(subprocess.check_output(['plutil','-convert','xml1','-o','-',str(IOS/'Eilo.xcodeproj/project.pbxproj')]))
    generated=project(original,bundle)
    temp=IOS/('.EiloFrameworkEvaluation-'+uuid.uuid4().hex+'.xcodeproj');temp.mkdir()
    workspace=out/'Evaluation.xcworkspace';workspace.mkdir()
    (workspace/'contents.xcworkspacedata').write_text('<?xml version="1.0"?><Workspace version="1.0"><FileRef location="absolute:'+escape(str(temp),{'"':'&quot;'})+'"/><FileRef location="absolute:'+escape(str(IOS/'Pods/Pods.xcodeproj'),{'"':'&quot;'})+'"/></Workspace>')
    (temp/'project.pbxproj').write_bytes(plistlib.dumps(generated))
    try:
        command=['xcodebuild','-workspace',workspace,'-scheme','Eilo','-configuration','Release','-destination','generic/platform=iOS Simulator','ARCHS=arm64','ONLY_ACTIVE_ARCH=YES','-derivedDataPath',out/'derived','CODE_SIGNING_ALLOWED=NO','CODE_SIGNING_REQUIRED=NO','CODE_SIGN_IDENTITY=','-disableAutomaticPackageResolution','build']
        with (out/'build.log').open('w') as log:
            subprocess.run(list(map(str,command)),stdout=log,stderr=log,check=True,timeout=1500)
        app=out/'derived/Build/Products/Release-iphonesimulator/Eilo.app'
        observation=app_metadata(app,entries['iphonesimulator'][1])
        settings=json.loads(run([*command[:-1],'-showBuildSettings','-json']))
        own=[r['buildSettings'] for r in settings if r['target']=='Eilo'];need(len(own)==1);s=own[0]
        conditions=s.get('SWIFT_ACTIVE_COMPILATION_CONDITIONS','');need(not any(w in conditions for w in ('DEBUG','EILO_ASR_EVALUATION','EILO_LLM_EVALUATION','EILO_VAD_EVALUATION')))
        need(s['CODE_SIGNING_ALLOWED']=='NO' and s['CONFIGURATION']=='Release')
        sdk=run(['xcrun','--sdk','iphonesimulator','--show-sdk-path']).strip()
        client=out/'probe/FrameworkGate.app';(client/'Frameworks').mkdir(parents=True)
        shutil.copytree(bundle,client/'Frameworks/CEiloAsr.framework')
        sources=sorted((PACKAGES/'native-test-seam/Sources/NativeTestSeam').glob('*.swift'))
        run(['xcrun','swiftc','-O','-swift-version','5','-warnings-as-errors','-parse-as-library','-target','arm64-apple-ios18.0-simulator','-sdk',sdk,
             '-F',client/'Frameworks',*sources,HERE/'app_framework_probe.swift','-framework',NAME,'-framework','Foundation','-framework','AVFoundation','-framework','CryptoKit',
             '-Xlinker','-rpath','-Xlinker','@executable_path/Frameworks','-o',client/'GateProbe'])
        result=run(['xcrun','simctl','spawn',a.udid,client/'GateProbe'])
        need(result.strip()=='FRAMEWORK_RELEASE_GATES_PASS')
        run(['xcrun','simctl','install',a.udid,app])
        run(['python3',ROOT/'scripts/verify-ios-launch.py','--udid',a.udid,'--cycles','3','--dwell','10'],timeout=150)
        need(archive_pins==[dict(name=n,bytes=p.stat().st_size,sha256=sha(p)) for n,p in zip(archive_names,archives)])
        need(before==pins());need(inspect_bundle(bundle,'iphonesimulator')==entries['iphonesimulator'][1])
        report=dict(schema_version=1,purpose='OPT_IN_UNSIGNED_SIMULATOR_APP_FRAMEWORK',source_pins=before,dependency_archives=archive_pins,app=observation,
                    cold_launches=3,dwell_seconds=10,release_gate_probe='EXECUTED_UNAVAILABLE_ASR_AND_MISSING_MODELS_NO_CAPTURE',
                    swift_runtime_evaluation_flags='ABSENT',framework=entries['iphonesimulator'][1],project='TEMPORARY_COPY_ONLY',**FLAGS)
        (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
        print('Unsigned Release simulator app framework embedding and three launch checks PASS; runtime gates remain unavailable.')
    finally:
        shutil.rmtree(temp)


if __name__=='__main__':main()
