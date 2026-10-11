#!/usr/bin/env python3
"""Explicit offline Android native ASR fixture evaluation. Restores a normal APK afterwards.
Requires the pinned downloaded runtime/model/fixtures and an existing API35 ARM64 emulator.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from check_host import CACHE,HERE,digest,verified_model

def run(args,timeout=120,env=None):
    return subprocess.run(list(map(str,args)),check=True,capture_output=True,text=True,timeout=timeout,env=env)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['ndk','java-home','android-sdk']:p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--serial',required=True);args=p.parse_args()
    if not args.serial.startswith('emulator-') or not args.serial[9:].isdigit():raise ValueError('explicit emulator required')
    adb=args.android_sdk/'platform-tools/adb'
    def device(*values,timeout=120):return run([adb,'-s',args.serial,*values],timeout=timeout)
    if device('shell','getprop','sys.boot_completed').stdout.strip()!='1' or device('shell','getprop','ro.build.version.sdk').stdout.strip()!='35' or device('shell','getprop','ro.product.cpu.abi').stdout.strip()!='arm64-v8a':raise ValueError('booted API35 ARM64 emulator required')
    model,record=verified_model();android=record['android']
    if digest(CACHE/'moonshine-voice-0.1.5.aar')!=android['publisher_sha256']:raise ValueError('Android archive integrity failed')
    for item in android['files']:
        if digest(CACHE/item['path'])!=item['sha256']:raise ValueError('Android extracted integrity failed')
    if 'Pkg.Revision = 27.1.12297006' not in (args.ndk/'source.properties').read_text():raise ValueError('unexpected NDK')
    tool=args.ndk/'toolchains/llvm/prebuilt/darwin-x86_64/bin'
    for abi,target in [('arm64-v8a','aarch64-linux-android26'),('armeabi-v7a','armv7a-linux-androideabi26'),('x86_64','x86_64-linux-android26')]:
        libs=CACHE/'android-0.1.5/jni'/abi;out=CACHE/'build'/abi;out.mkdir(exist_ok=True)
        run([tool/(target+'-clang++'),'-std=c++17','-Wall','-Wextra','-Werror','-fPIC','-shared','-static-libstdc++','-Wl,--no-undefined','-Wl,-z,max-page-size=16384','-I',HERE/'include','-I',CACHE/'moonshine-voice-macos-arm64/include',HERE/'eilo_asr.cc',HERE/'eilo_asr_jni.cc','-L',libs,'-Wl,-rpath-link,'+str(libs),'-lmoonshine','-o',out/'libeilo_asr_jni.so'])
    assets=CACHE/'device-assets/asr-evaluation';assets.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(HERE/'provenance.json',assets/'provenance.json');shutil.copyfile(HERE/'tests/fixtures.json',assets/'fixtures.json')
    for item in record['model']['files']:
        relative=Path(record['model']['directory'])/item['file'];(assets/relative).parent.mkdir(exist_ok=True);shutil.copyfile(CACHE/relative,assets/relative)
    fixtures=json.loads((HERE/'tests/fixtures.json').read_text())['cases']
    for item in fixtures:
        source=CACHE/'fixtures'/item['file']
        if digest(source)!=item['sha256']:raise ValueError('synthetic fixture integrity failed')
        (assets/'fixtures').mkdir(exist_ok=True);shutil.copyfile(source,assets/'fixtures'/item['file'])
    libs=CACHE/'package-jni/arm64-v8a';libs.mkdir(parents=True,exist_ok=True)
    for name in ['libmoonshine.so','libonnxruntime.so']:shutil.copyfile(CACHE/'android-0.1.5/jni/arm64-v8a'/name,libs/name)
    shutil.copyfile(CACHE/'build/arm64-v8a/libeilo_asr_jni.so',libs/'libeilo_asr_jni.so')
    manifest=CACHE/'device-manifest.xml'
    manifest.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android"><instrumentation android:name="com.eilo.foundation.AsrEvaluationInstrumentation" android:targetPackage="com.eilo" android:label="Eilo synthetic ASR evaluation" /></manifest>')
    init=CACHE/'device.init.gradle'
    init.write_text('gradle.afterProject { p ->\n if (p.path == ":app") {\n p.android.sourceSets.debug.java.srcDir('+json.dumps(str(HERE/'tests/android-device'))+')\n p.android.sourceSets.debug.assets.srcDir('+json.dumps(str(assets.parent))+')\n p.android.sourceSets.debug.jniLibs.srcDir('+json.dumps(str(libs.parent))+')\n p.android.sourceSets.debug.manifest.srcFile('+json.dumps(str(manifest))+')\n p.android.packagingOptions.jniLibs.useLegacyPackaging = true\n }\n}\n')
    project=HERE.parents[1]/'apps/mobile/android';env=dict(os.environ,JAVA_HOME=str(args.java_home),ANDROID_HOME=str(args.android_sdk))
    try:
        run([project/'gradlew','-p',project,'-I',init,':app:assembleDebug','--offline','--max-workers=2'],900,env)
        apk=project/'app/build/outputs/apk/debug/app-debug.apk';device('install','-r',apk)
        result=device('shell','am','instrument','-w','com.eilo/com.eilo.foundation.AsrEvaluationInstrumentation',timeout=900).stdout
        if 'eilo_asr_evaluation=PASS' not in result or 'INSTRUMENTATION_CODE: -1' not in result:raise ValueError('native Android evaluation failed')
        report=json.loads(device('exec-out','run-as','com.eilo','cat','files/asr-android-results.json').stdout)
        if len(report.get('cases',[]))!=len(fixtures) or any(c.get('stale_final_rejected') is not True for c in report['cases']):raise ValueError('native Android report failed')
        device('shell','run-as','com.eilo','test','!','-e','files/asr-evaluation')
        report.update({'runtime':record['version'],'temporary_assets_removed':True,'apk_sha256':digest(apk),'page_size':device('shell','getconf','PAGESIZE').stdout.strip()})
        device('shell','run-as','com.eilo','rm','files/asr-android-results.json')
        (CACHE/'android-results.json').write_text(json.dumps(report,indent=2)+'\n')
        print('Actual Android ART/JNI ASR: six frozen synthetic cases executed; stale/final checks PASS.')
    finally:
        # Finish the complete normal build before restoring the package. Preserve app data/consent.
        run([project/'gradlew','-p',project,':app:assembleDebug','--offline','--max-workers=2'],900,env)
        device('install','-r',project/'app/build/outputs/apk/debug/app-debug.apk')

if __name__=='__main__':main()
