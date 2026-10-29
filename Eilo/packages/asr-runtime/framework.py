"""Build/inspect unsigned ASR XCFramework and execute a relocated offline simulator client."""
import argparse
import array
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import wave

HERE=Path(__file__).resolve().parent
PACKAGES=HERE.parent
NAME='CEiloAsr'
EXPORTS=['_eilo_asr_accept','_eilo_asr_create','_eilo_asr_destroy','_eilo_asr_text']
INSTALL='@rpath/CEiloAsr.framework/CEiloAsr'
FLAGS=dict(signing='NOT_REVIEWED',distribution='NOT_APPROVED',ordinary_app='NOT_ENABLED',physical='NOT_RUN',release='HOLD',persistent_memory='DISABLED',pack_trust='SYNTHETIC_EVALUATOR_ONLY',confidence='NOT_EVALUATED',production_embedding='NOT_RUN')


def need(ok):
    if not ok:raise ValueError('invalid framework evidence')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    need(path.stat().st_size<=2*1024**2)
    def unique(pairs):
        obj={}
        for k,v in pairs:need(k not in obj);obj[k]=v
        return obj
    def invalid(_):raise ValueError('nonfinite JSON')
    return json.loads(path.read_text(),object_pairs_hook=unique,parse_constant=invalid)


def pins():
    paths=[HERE/n for n in ('framework.py','framework_probe.swift','eilo_asr.cc','include/eilo_asr.h','provenance.json','tests/fixtures.json')]
    llm=PACKAGES/'llm-runtime'
    paths += [llm/n for n in ('eilo_llm.cc','include/eilo_llm.h','include/module.modulemap','provenance.json','check_host.py','check_ios.py')]
    paths += sorted((PACKAGES/'native-test-seam/Sources/NativeTestSeam').glob('*.swift'))
    return {str(p.relative_to(PACKAGES)):sha(p) for p in paths}


def run(command,timeout=180):
    process=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=timeout)
    if process.returncode:print(process.stderr[-5000:],file=sys.stderr);process.check_returncode()
    return process.stdout


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def verify_asr(cache):
    record=read(HERE/'provenance.json');ios=record['ios']
    need(sha(cache/ios['archive'])==ios['publisher_sha256'])
    for item in ios['files']:need(sha(cache/item['path'])==item['sha256'])
    model=cache/record['model']['directory']
    for item in record['model']['files']:
        p=model/item['file'];need(p.stat().st_size==item['bytes'] and sha(p)==item['local_sha256'])
    return model,record


def metadata(sdk):
    return dict(CFBundleExecutable=NAME,CFBundleIdentifier='org.eilo.evaluation.asr',CFBundleName=NAME,
                CFBundlePackageType='FMWK',CFBundleShortVersionString='0.1.5',CFBundleVersion='1',MinimumOSVersion='18.0',
                CFBundleSupportedPlatforms=['iPhoneSimulator' if sdk=='iphonesimulator' else 'iPhoneOS'])


def inspect_binary(path,platform):
    need(not path.is_symlink() and path.is_file())
    exports=sorted(run(['xcrun','nm','-gUj',path]).splitlines());need(exports==EXPORTS)
    flags=run(['xcrun','otool','-hv',path]);need('TWOLEVEL' in flags)
    need(run(['xcrun','lipo','-archs',path]).strip()=='arm64')
    identity=run(['xcrun','otool','-D',path]).splitlines();need(identity[1:]==[INSTALL])
    load=run(['xcrun','vtool','-show-build',path]);need(re.search(r'platform\s+'+platform+r'\b',load) and re.search(r'minos\s+18\.0\b',load))
    dependencies=[line.strip().split(' (')[0] for line in run(['xcrun','otool','-L',path]).splitlines()[1:]]
    need(INSTALL in dependencies)
    need(all(d==INSTALL or d.startswith('/System/Library/Frameworks/') or d.startswith('/usr/lib/') for d in dependencies))
    signature=subprocess.run(['codesign','-dv','--verbose=2',str(path)],capture_output=True,text=True,timeout=30)
    if signature.returncode==0:
        need('Signature=adhoc' in signature.stderr and 'Authority=' not in signature.stderr)
        signing='TOOLCHAIN_AD_HOC'
    else:
        need('code object is not signed at all' in signature.stderr);signing='UNSIGNED'
    return dict(architecture='arm64',platform=platform,minimum_os='18.0',install_name=INSTALL,exports=exports,
                namespace='TWOLEVEL',code_signature=signing,dependencies=dependencies,sha256=sha(path),bytes=path.stat().st_size)


def inspect_bundle(path,sdk):
    need(path.name==NAME+'.framework' and path.is_dir() and not path.is_symlink())
    need(not any(p.is_symlink() for p in path.rglob('*')))
    need(plistlib.loads((path/'Info.plist').read_bytes())==metadata(sdk))
    need((path/'Headers/eilo_asr.h').read_bytes()==(HERE/'include/eilo_asr.h').read_bytes())
    need((path/'Modules/module.modulemap').read_text()=='framework module CEiloAsr { umbrella header "eilo_asr.h" export * }\n')
    result=inspect_binary(path/NAME,'IOSSIMULATOR' if sdk=='iphonesimulator' else 'IOS')
    result.update(header_sha256=sha(path/'Headers/eilo_asr.h'),module_sha256=sha(path/'Modules/module.modulemap'),info_sha256=sha(path/'Info.plist'))
    return result


def build_framework(cache,out,sdk):
    target='arm64-apple-ios18.0'+('-simulator' if sdk=='iphonesimulator' else '')
    sysroot=run(['xcrun','--sdk',sdk,'--show-sdk-path']).strip()
    vendor=cache/'ios-0.1.5/Moonshine.xcframework'/('ios-arm64_x86_64-simulator' if sdk=='iphonesimulator' else 'ios-arm64')
    directory=out/sdk;directory.mkdir();bundle=directory/(NAME+'.framework')
    (bundle/'Headers').mkdir(parents=True);(bundle/'Modules').mkdir()
    shutil.copyfile(HERE/'include/eilo_asr.h',bundle/'Headers/eilo_asr.h')
    (bundle/'Modules/module.modulemap').write_text('framework module CEiloAsr { umbrella header "eilo_asr.h" export * }\n')
    (bundle/'Info.plist').write_bytes(plistlib.dumps(metadata(sdk)))
    symbols=directory/'exports.txt';symbols.write_text('\n'.join(EXPORTS)+'\n')
    common=['xcrun','--sdk',sdk,'clang++','-target',target,'-isysroot',sysroot,'-std=c++17','-Wall','-Wextra','-Werror']
    run([*common,'-I',HERE/'include','-I',vendor/'Headers','-c',HERE/'eilo_asr.cc','-o',directory/'asr.o'])
    run([*common,'-dynamiclib',directory/'asr.o',vendor/'libmoonshine.a','-framework','Accelerate','-framework','Foundation',
         '-Wl,-twolevel_namespace','-Wl,-exported_symbols_list,'+str(symbols),'-Wl,-install_name,'+INSTALL,'-o',bundle/NAME])
    return bundle,inspect_bundle(bundle,sdk)


def xcframework_entries(path):
    need(path.is_dir() and not path.is_symlink() and not any(p.is_symlink() for p in path.rglob('*')))
    info=plistlib.loads((path/'Info.plist').read_bytes());entries=info['AvailableLibraries']
    need(info['CFBundlePackageType']=='XFWK' and info['XCFrameworkFormatVersion']=='1.0' and len(entries)==2)
    result={}
    for row in entries:
        sdk='iphonesimulator' if row.get('SupportedPlatformVariant')=='simulator' else 'iphoneos'
        need(sdk not in result and row['SupportedPlatform']=='ios' and row['SupportedArchitectures']==['arm64'])
        need(row.get('SupportedPlatformVariant') in (None,'simulator') and row['LibraryPath']==NAME+'.framework')
        identifier=row['LibraryIdentifier'];need(re.fullmatch('[A-Za-z0-9_-]+',identifier))
        bundle=path/identifier/row['LibraryPath'];result[sdk]=(bundle,inspect_bundle(bundle,sdk))
    need(set(result)=={'iphoneos','iphonesimulator'});return result


def build_llm(cache,cmake,out):
    directory=PACKAGES/'llm-runtime';record=read(directory/'provenance.json');source=cache/('llama.cpp-'+record['runtime']['commit'])
    archive=cache/'llama-v0.6.0.tar.gz';need(sha(archive)==record['runtime']['source_archive_sha256'])
    host=module('framework_llm_source',directory/'check_host.py');host.verify_tree(archive,source,source.name)
    sys.path.insert(0,str(directory))
    try:options=module('framework_llm_options',directory/'check_ios.py').options('iphonesimulator')
    finally:sys.path.pop(0)
    need(options['GGML_CPU']=='ON' and options['BUILD_SHARED_LIBS']=='OFF')
    build=out/'llm-build';run([cmake,'-S',source,'-B',build,*['-D'+k+'='+v for k,v in options.items()]])
    run([cmake,'--build',build,'--target','llama','-j','3'],timeout=900)
    libraries=[build/'src/libllama.a',*[build/('ggml/src/lib'+name+'.a') for name in ('ggml','ggml-cpu','ggml-base')]]
    sdk=run(['xcrun','--sdk','iphonesimulator','--show-sdk-path']).strip()
    obj=out/'eilo_llm.o'
    run(['xcrun','--sdk','iphonesimulator','clang++','-target','arm64-apple-ios18.0-simulator','-isysroot',sdk,'-std=c++17','-Wall','-Wextra','-Werror',
         '-I',directory/'include','-I',source/'include','-I',source/'ggml/include','-c',directory/'eilo_llm.cc','-o',obj])
    return obj,libraries


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('asr-cache','llm-cache','cmake','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--udid',required=True);args=p.parse_args()
    cache=args.asr_cache.resolve();out=args.output.resolve();need(not out.exists())
    devices=json.loads(run(['xcrun','simctl','list','devices','--json']))['devices']
    need(any(d['udid']==args.udid and d['state']=='Booted' and d.get('isAvailable') for ds in devices.values() for d in ds))
    before=pins();model,provenance=verify_asr(cache);out.mkdir(parents=True)
    bundles={};observations={}
    for sdk in ('iphoneos','iphonesimulator'):bundles[sdk],observations[sdk]=build_framework(cache,out,sdk)
    product=out/(NAME+'.xcframework')
    run(['xcodebuild','-create-xcframework','-framework',bundles['iphoneos'],'-framework',bundles['iphonesimulator'],'-output',product])
    entries=xcframework_entries(product)
    need(all(entries[sdk][1]==observations[sdk] for sdk in entries))
    llm_obj,llm_libraries=build_llm(args.llm_cache.resolve(),args.cmake.resolve(),out)
    original=out/'original/FrameworkEvaluation.app';(original/'Frameworks').mkdir(parents=True)
    shutil.copytree(entries['iphonesimulator'][0],original/'Frameworks'/bundles['iphonesimulator'].name)
    sources=sorted((PACKAGES/'native-test-seam/Sources/NativeTestSeam').glob('*.swift'))
    sdk=run(['xcrun','--sdk','iphonesimulator','--show-sdk-path']).strip()
    run(['xcrun','--sdk','iphonesimulator','swiftc','-swift-version','5','-warnings-as-errors','-target','arm64-apple-ios18.0-simulator','-sdk',sdk,
         '-parse-as-library','-D','DEBUG','-D','EILO_ASR_EVALUATION','-I',PACKAGES/'llm-runtime/include','-F',original/'Frameworks',
         *sources,HERE/'framework_probe.swift',llm_obj,*llm_libraries,'-framework',NAME,'-framework','Accelerate','-framework','Foundation','-framework','AVFoundation','-framework','CryptoKit','-lc++',
         '-Xlinker','-rpath','-Xlinker','@executable_path/Frameworks','-o',original/'FrameworkProbe'])
    relocated=out/'relocated/FrameworkEvaluation.app';relocated.parent.mkdir();original.rename(relocated);need(not original.exists())
    client=relocated/'FrameworkProbe';loads=run(['xcrun','otool','-L',client]).splitlines()[1:]
    need(any(line.strip().split(' (')[0]==INSTALL for line in loads) and all(str(out) not in line for line in loads))
    rpaths=run(['xcrun','otool','-l',client]);need('path @executable_path/Frameworks ' in rpaths)
    need(inspect_bundle(relocated/'Frameworks'/bundles['iphonesimulator'].name,'iphonesimulator')==observations['iphonesimulator'])
    fixture=next(r for r in read(HERE/'tests/fixtures.json')['cases'] if r['id']=='question');audio=cache/'fixtures'/fixture['file'];need(sha(audio)==fixture['sha256'])
    with tempfile.TemporaryDirectory(prefix='eilo-framework-fixture-') as temp:
        raw=Path(temp)/'input.f32'
        with wave.open(str(audio),'rb') as w:
            need((w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())==(1,2,16000,fixture['samples']))
            pcm=array.array('h',w.readframes(w.getnframes()))
        raw.write_bytes(array.array('f',(v/32768 for v in pcm)).tobytes())
        try:log=run(['xcrun','simctl','spawn',args.udid,client,model,raw],timeout=180)
        finally:raw.write_bytes(bytes(raw.stat().st_size));raw.unlink()
    lines=[line.split('\t',1)[1] for line in log.splitlines() if line.startswith('EILO_FRAMEWORK_RESULT\t')];need(len(lines)==1)
    execution=json.loads(lines[0]);need(before==pins());verify_asr(cache)
    need(sum(f.stat().st_size for f in out.rglob('*') if f.is_file())<5*1024**3)
    report=dict(schema_version=1,purpose='UNSIGNED_IOS_ASR_FRAMEWORK_EVALUATION',source_pins=before,asr_provenance_sha256=sha(HERE/'provenance.json'),
                llm_provenance_sha256=sha(PACKAGES/'llm-runtime/provenance.json'),frameworks=observations,xcframework='TWO_ARM64_SLICES',
                relocation='EXECUTED_WITH_ORIGINAL_CLIENT_DIRECTORY_ABSENT',framework_client_sha256=sha(client),fixture_sha256=fixture['sha256'],execution=execution,
                llm_static_archives=[dict(name=f.name,sha256=sha(f)) for f in llm_libraries],compiler=run(['xcrun','clang++','--version']).splitlines()[0],**FLAGS)
    from framework_report import validate
    validate(report);(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Device/simulator framework build and relocated simulator ASR/LLM coexistence PASS; production/physical NOT_RUN.')


if __name__=='__main__':main()
