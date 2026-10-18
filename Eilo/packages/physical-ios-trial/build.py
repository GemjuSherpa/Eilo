"""Build a separate unsigned foreground trial app from existing approved caches. No install/sign/download.
Signing/provisioning and physical launch are deliberately separate operator steps.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / 'vad-runtime'))
from check_installer import verify, verified_asr, require, sha256, run

BUNDLE = 'com.eilo.ForegroundVoiceTrial'


def identifier(name):
    return hashlib.sha256(name.encode()).hexdigest()[:24].upper()


def project(output, sources, assets, flags, framework):
    """Generate a local native-only Xcode target; no production project edits or account data."""
    objects = {}
    def add(label, isa, **values):
        key = identifier(label); objects[key] = dict(isa=isa, **values); return key
    files = []; builds = []
    for source in sources:
        name = str(source)
        ref = add(name, 'PBXFileReference', lastKnownFileType='sourcecode.swift', path=name, sourceTree='<absolute>')
        files.append(ref); builds.append(add(name + '-build', 'PBXBuildFile', fileRef=ref))
    resource = add('assets', 'PBXFileReference', lastKnownFileType='folder', path=str(assets), sourceTree='<absolute>')
    resource_build = add('assets-build', 'PBXBuildFile', fileRef=resource)
    dynamic = add('asr-dynamic', 'PBXFileReference', lastKnownFileType='compiled.mach-o.dylib', path=str(output / 'libeilo_trial_asr.dylib'), sourceTree='<absolute>')
    embed_build = add('asr-embed', 'PBXBuildFile', fileRef=dynamic, settings={'ATTRIBUTES': ['CodeSignOnCopy', 'RemoveHeadersOnCopy']})
    embed = add('embed', 'PBXCopyFilesBuildPhase', buildActionMask=2147483647, dstPath='', dstSubfolderSpec=10, files=[embed_build], name='Embed ASR runtime', runOnlyForDeploymentPostprocessing=0)
    source_phase = add('sources', 'PBXSourcesBuildPhase', buildActionMask=2147483647, files=builds, runOnlyForDeploymentPostprocessing=0)
    resources = add('resources', 'PBXResourcesBuildPhase', buildActionMask=2147483647, files=[resource_build], runOnlyForDeploymentPostprocessing=0)
    product = add('product', 'PBXFileReference', explicitFileType='wrapper.application', path='EiloForegroundTrial.app', sourceTree='BUILT_PRODUCTS_DIR')
    group = add('group', 'PBXGroup', children=[*files, resource, dynamic, product], sourceTree='<group>')
    settings = dict(PRODUCT_BUNDLE_IDENTIFIER=BUNDLE, PRODUCT_NAME='EiloForegroundTrial', INFOPLIST_FILE=str(output / 'Info.plist'),
        IPHONEOS_DEPLOYMENT_TARGET='18.0', SDKROOT='iphoneos', TARGETED_DEVICE_FAMILY='1', SWIFT_VERSION='5.0',
        SWIFT_ACTIVE_COMPILATION_CONDITIONS='DEBUG EILO_VAD_EVALUATION EILO_ASR_EVALUATION EILO_LLM_EVALUATION',
        SWIFT_TREAT_WARNINGS_AS_ERRORS='YES', SWIFT_OPTIMIZATION_LEVEL='-O', ENABLE_BITCODE='NO',
        SWIFT_INCLUDE_PATHS=['"'+str(HERE.parent / p / 'include')+'"' for p in ['vad-runtime', 'asr-runtime', 'llm-runtime']],
        OTHER_LDFLAGS=['"'+f+'"' if f.startswith('/') else f for f in flags], LD_RUNPATH_SEARCH_PATHS=['$(inherited)', '@executable_path/Frameworks'],
        FRAMEWORK_SEARCH_PATHS=['"'+str(framework)+'"'], ALWAYS_SEARCH_USER_PATHS='NO', CODE_SIGN_STYLE='Automatic', GENERATE_INFOPLIST_FILE='NO')
    configs = [add('target-' + n, 'XCBuildConfiguration', buildSettings=settings, name=n) for n in ['Debug', 'Release']]
    config_list = add('target-configs', 'XCConfigurationList', buildConfigurations=configs, defaultConfigurationIsVisible=0, defaultConfigurationName='Release')
    target = add('target', 'PBXNativeTarget', buildConfigurationList=config_list, buildPhases=[source_phase, resources, embed], buildRules=[], dependencies=[], name='EiloForegroundTrial', productName='EiloForegroundTrial', productReference=product, productType='com.apple.product-type.application')
    pc = [add('project-' + n, 'XCBuildConfiguration', buildSettings={}, name=n) for n in ['Debug', 'Release']]
    pcl = add('project-configs', 'XCConfigurationList', buildConfigurations=pc, defaultConfigurationIsVisible=0, defaultConfigurationName='Release')
    root = add('project', 'PBXProject', attributes={'LastUpgradeCheck': '2700'}, buildConfigurationList=pcl, compatibilityVersion='Xcode 14.0', developmentRegion='en', hasScannedForEncodings=0, knownRegions=['en','Base'], mainGroup=group, projectDirPath='', projectRoot='', targets=[target])
    def encode(value):
        if isinstance(value, dict): return '{\n' + ''.join(json.dumps(k) + ' = ' + encode(v) + ';\n' for k,v in value.items()) + '}'
        if isinstance(value, list): return '(' + ','.join(encode(v) for v in value) + ')'
        return str(value) if isinstance(value, int) else json.dumps(value)
    folder = output / 'EiloForegroundTrial.xcodeproj'; folder.mkdir()
    (folder / 'project.pbxproj').write_text('// !$*UTF8*$!\n' + encode(dict(archiveVersion=1, classes={}, objectVersion=56, objects=objects, rootObject=root)))
    return folder


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['asr-cache','vad-cache','vad-model','llm-cache','llm-model','output']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--operator-radio-off-attestation', action='store_true', help='Record the human operator declaration; never an OS/network verification.')
    a = p.parse_args()
    asr,vad,model,llm,gguf,output = [v.resolve() for v in (a.asr_cache,a.vad_cache,a.vad_model,a.llm_cache,a.llm_model,a.output)]
    verify(vad,model);asr_model,record=verified_asr(asr)
    llm_here=HERE.parent/'llm-runtime';prov=json.loads((llm_here/'provenance.json').read_text())
    require(gguf.is_file() and not gguf.is_symlink() and gguf.stat().st_size==prov['model']['bytes'] and sha256(gguf)==prov['model']['sha256'],'LLM model changed')
    source=llm/('llama.cpp-'+prov['runtime']['commit']);archive=llm/'llama-v0.6.0.tar.gz'
    require(sha256(archive)==prov['runtime']['source_archive_sha256'],'LLM archive changed')
    spec=importlib.util.spec_from_file_location('trial_llm_host',llm_here/'check_host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host);host.verify_tree(archive,source,source.name)
    require(not output.exists(),'refusing to overwrite lab build');output.mkdir(parents=True)
    build=output/'llm-build';options=json.loads((llm_here/'tests/ios-results.json').read_text())['builds'][1]['build_options']
    cmake=llm.parent/'model-build/venv/bin/cmake'
    with (output/'llm-build.log').open('w') as log:
        subprocess.run(list(map(str,[cmake,'-S',source,'-B',build,*['-D'+k+'='+str(v) for k,v in options.items()]])),stdout=log,stderr=log,check=True,timeout=180)
        subprocess.run(list(map(str,[cmake,'--build',build,'--target','llama','-j','3'])),stdout=log,stderr=log,check=True,timeout=600)
    libs=[build/'src/libllama.a',*[build/('ggml/src/lib'+n+'.a') for n in ['ggml','ggml-cpu','ggml-base']]]
    for library in libs:
        names={s.split()[-1] for s in run(['xcrun','nm','-u',library]).splitlines() if s.strip()}
        require(not names & {'_socket','_connect','_sendto','_getaddrinfo','_curl_easy_perform'},'network dependency in LLM')
    sdk=run(['xcrun','--sdk','iphoneos','--show-sdk-path']).strip();target=['-target','arm64-apple-ios18.0','-isysroot',sdk]
    moon=asr/'ios-0.1.5/Moonshine.xcframework/ios-arm64'
    obj=output/'eilo_asr.o'
    run(['xcrun','clang++',*target,'-std=c++17','-Wall','-Wextra','-Werror','-I',HERE.parent/'asr-runtime/include','-I',moon/'Headers','-c',HERE.parent/'asr-runtime/eilo_asr.cc','-o',obj])
    dynamic=output/'libeilo_trial_asr.dylib';exports=output/'asr.exports'
    names={'_eilo_asr_'+n for n in ['create','accept','text','destroy']};exports.write_text('\n'.join(sorted(names))+'\n')
    run(['xcrun','clang++',*target,'-dynamiclib',obj,moon/'libmoonshine.a','-framework','Accelerate','-framework','Foundation','-Wl,-twolevel_namespace','-Wl,-exported_symbols_list,'+str(exports),'-Wl,-install_name,@rpath/'+dynamic.name,'-o',dynamic])
    require(set(run(['xcrun','nm','-gUj',dynamic]).splitlines())==names and 'TWOLEVEL' in run(['xcrun','otool','-hv',dynamic]),'ASR isolation changed')
    headers=vad/'ios/onnxruntime.xcframework/ios-arm64/onnxruntime.framework/Headers';objects=[]
    for src in [HERE.parent/'vad-runtime/eilo_vad.cc',HERE.parent/'vad-runtime/eilo_vad_onnx.cc',llm_here/'eilo_llm.cc']:
        obj=output/(src.stem+'.o');objects.append(obj)
        run(['xcrun','clang++',*target,'-std=c++17','-Wall','-Wextra','-Werror','-I',HERE.parent/'vad-runtime/include','-I',headers,'-I',llm_here/'include','-I',source/'include','-I',source/'ggml/include','-c',src,'-o',obj])
    assets=output/'TrialAssets';assets.mkdir();pins=[]
    for i,r in enumerate(record['model']['files']):
        pins.append(dict(id='asr-'+str(i),filename=r['file'],sha256=r['local_sha256'],bytes=r['bytes']));shutil.copy2(asr_model/r['file'],assets/r['file'])
    pins += [dict(id='vad',filename='silero.onnx',sha256=sha256(model),bytes=model.stat().st_size),dict(id='llm',filename='model.gguf',sha256=prov['model']['sha256'],bytes=gguf.stat().st_size)]
    shutil.copy2(model,assets/'silero.onnx');shutil.copy2(gguf,assets/'model.gguf')
    for r in pins:require(sha256(assets/r['filename'])==r['sha256'],'staged model changed')
    (assets/'pins.json').write_text(json.dumps(pins))
    (assets/'operator.json').write_text(json.dumps(dict(schema_version=1,radio_off_attested=a.operator_radio_off_attestation,source='HUMAN_OPERATOR' if a.operator_radio_off_attestation else 'NOT_PROVIDED',recorded_utc=datetime.now(timezone.utc).isoformat())))
    info=dict(CFBundleIdentifier='$(PRODUCT_BUNDLE_IDENTIFIER)',CFBundleExecutable='$(EXECUTABLE_NAME)',CFBundleName='EiloForegroundTrial',CFBundleDisplayName='Eilo Foreground Trial',CFBundlePackageType='APPL',CFBundleShortVersionString='0.1',CFBundleVersion='1',LSRequiresIPhoneOS=True,NSMicrophoneUsageDescription='Run an explicitly started local foreground voice test. No recordings are saved.',UILaunchScreen={},UIApplicationSceneManifest={'UIApplicationSupportsMultipleScenes':False})
    (output/'Info.plist').write_bytes(plistlib.dumps(info))
    framework=vad/'ios/onnxruntime.xcframework/ios-arm64'
    flags=['$(inherited)',*map(str,objects),*map(str,libs),str(dynamic),'-framework','onnxruntime','-framework','Accelerate','-framework','CoreML','-lc++']
    sources=[*sorted((HERE.parent/'native-test-seam/Sources/NativeTestSeam').glob('*.swift')),HERE/'TrialApp.swift',HERE/'TrialEpoch.swift']
    proj=project(output,sources,assets,flags,framework)
    command=['xcodebuild','-project',str(proj),'-scheme','EiloForegroundTrial','-configuration','Release','-sdk','iphoneos','-destination','generic/platform=iOS','-derivedDataPath',str(output/'DerivedData'),'CODE_SIGNING_ALLOWED=NO','-jobs','3','build']
    with (output/'app-build.log').open('w') as log:subprocess.run(command,stdout=log,stderr=log,check=True,timeout=600)
    app=output/'DerivedData/Build/Products/Release-iphoneos/EiloForegroundTrial.app'
    require(app.is_dir(),'unsigned app missing')
    result=dict(schema_version=1,scope='UNSIGNED_INTERNAL_PHYSICAL_TRIAL_BUILD',bundle_identifier=BUNDLE,app_binary_sha256=sha256(app/'EiloForegroundTrial'),asr_dynamic_sha256=sha256(dynamic),operator_configuration_sha256=sha256(assets/'operator.json'),model_files=[{k:r[k] for k in ['filename','sha256','bytes']} for r in pins],source_sha256=[dict(path=str(s.relative_to(ROOT)),sha256=sha256(s)) for s in sources],signing='NOT_RUN',installation='NOT_RUN',physical_execution='NOT_RUN',production='NOT_ENABLED')
    (output/'build-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Unsigned separate physical-trial app build PASS. Signing, installation and physical execution NOT_RUN.')


if __name__=='__main__':main()
