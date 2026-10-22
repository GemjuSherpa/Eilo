"""Explicit existing-emulator SDK check; no model/package downloads or microphone."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'vad-runtime'))
from check_installer_android import serial, run, sha256, require
HERE=Path(__file__).resolve().parent


def profile(apk,aapt,evaluation):
    permissions=run([aapt,'dump','permissions',apk])
    for name in ('INTERNET','RECORD_AUDIO'):
        require(('android.permission.'+name in permissions) is not evaluation,'permission profile changed')
    manifest=run([aapt,'dump','xmltree',apk,'--file','AndroidManifest.xml'])
    require(('AndroidSpeechSdkInstrumentation' in manifest) is evaluation,'source set changed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True,type=serial)
    for name in ('output','java-home','android-sdk'):parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args();output=args.output.resolve();require(not output.exists(),'refusing evidence overwrite');output.mkdir(parents=True)
    sdk=args.android_sdk.resolve();adb=sdk/'platform-tools/adb';aapt=sdk/'build-tools/37.0.0/aapt2'
    def device(*values):return run([adb,'-s',args.serial,*values],timeout=120)
    for prop,value in [('sys.boot_completed','1'),('ro.build.version.sdk','35'),('ro.product.cpu.abi','arm64-v8a')]:
        require(device('shell','getprop',prop).strip()==value,'booted API35 ARM64 emulator required')
    project=HERE.parents[1]/'apps/mobile/android';apk=project/'app/build/outputs/apk/debug/app-debug.apk'
    env=dict(os.environ,JAVA_HOME=str(args.java_home.resolve()),ANDROID_HOME=str(sdk))
    manifest=output/'AndroidManifest.xml'
    manifest.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android" xmlns:tools="http://schemas.android.com/tools">'
        '<uses-permission android:name="android.permission.INTERNET" tools:node="remove"/>'
        '<uses-permission android:name="android.permission.RECORD_AUDIO" tools:node="remove"/>'
        '<instrumentation android:name="com.eilo.foundation.AndroidSpeechSdkInstrumentation" android:targetPackage="com.eilo"/></manifest>')
    init=output/'sdk.init.gradle';init.write_text('gradle.afterProject { p -> if(p.path == ":app") {\n'
        'p.android.sourceSets.debug.java.srcDir('+json.dumps(str(HERE/'tests/android-speech'))+')\n'
        'p.android.sourceSets.debug.manifest.srcFile('+json.dumps(str(manifest))+')\n}}\n')
    def build(extra,log):
        completed=subprocess.run([str(project/'gradlew'),'-p',str(project),*map(str,extra),':app:assembleDebug','--offline','--max-workers=2'],env=env,capture_output=True,text=True,timeout=900)
        (output/log).write_text(completed.stdout+completed.stderr);require(completed.returncode==0,'APK build failed')
    report='files/speech-sdk-results.json';owned=False;result=None
    try:
        build(['-I',init],'evaluation-build.log');profile(apk,aapt,True);evaluation_sha=sha256(apk)
        device('install','-r',apk)
        device('shell','run-as','com.eilo','test','!','-e',report);owned=True
        log=device('shell','am','instrument','-w','com.eilo/com.eilo.foundation.AndroidSpeechSdkInstrumentation')
        (output/'instrumentation.log').write_text(log)
        require('eilo_speech_sdk=PASS' in log and 'INSTRUMENTATION_CODE: -1' in log,'SDK evaluator failed')
        result=json.loads(device('exec-out','run-as','com.eilo','cat',report))
    finally:
        try:
            device('shell','am','force-stop','com.eilo')
            if owned:device('shell','run-as','com.eilo','rm','-f',report);device('shell','run-as','com.eilo','test','!','-e',report)
        finally:
            build([],'normal-restore-build.log');profile(apk,aapt,False);device('install','-r',apk)
    require(result is not None,'SDK evidence unavailable')
    result.update(schema_version=1,android_api=35,abi='arm64-v8a',internet_permission='ABSENT',microphone_permission='ABSENT',
                  temporary_files_removed=True,normal_app_restored=True,evaluation_apk_sha256=evaluation_sha,normal_apk_sha256=sha256(apk))
    (output/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status']+'; physical/acoustic/network NOT_RUN; normal APK restored.')


if __name__=='__main__':main()
