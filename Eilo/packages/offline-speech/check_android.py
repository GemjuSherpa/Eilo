#!/usr/bin/env python3
"""Explicit generic SDK speech evaluation; restores the normal APK on every exit."""
import argparse,json,os,re,subprocess,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CACHE=ROOT/'.local/offline-speech'
def main():
    p=argparse.ArgumentParser();p.add_argument('--serial',required=True);p.add_argument('--android-sdk',type=Path,required=True);p.add_argument('--java-home',type=Path,required=True);a=p.parse_args()
    if not re.fullmatch('emulator-[0-9]+',a.serial):raise ValueError('explicit emulator required')
    CACHE.mkdir(parents=True,exist_ok=True);project=ROOT/'apps/mobile/android';apk=project/'app/build/outputs/apk/debug/app-debug.apk'
    env=dict(os.environ,JAVA_HOME=str(a.java_home),ANDROID_HOME=str(a.android_sdk));adb=a.android_sdk/'platform-tools/adb'
    def device(*args):return subprocess.run([str(adb),'-s',a.serial,*map(str,args)],check=True,capture_output=True,text=True,timeout=120)
    if device('shell','getprop','ro.build.version.sdk').stdout.strip()!='35':raise ValueError('API35 emulator required')
    manifest=CACHE/'manifest.xml';manifest.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android"><instrumentation android:name="com.eilo.foundation.OfflineSpeechEvaluationInstrumentation" android:targetPackage="com.eilo" /></manifest>')
    init=CACHE/'eval.init.gradle';init.write_text('gradle.afterProject { p -> if (p.path == ":app") {\np.android.sourceSets.debug.java.srcDir('+json.dumps(str(HERE/'tests/android-device'))+')\np.android.sourceSets.debug.manifest.srcFile('+json.dumps(str(manifest))+')\n}}\n')
    def build(evaluation):
        cmd=[str(project/'gradlew'),'-p',str(project)]
        if evaluation:cmd+=['-I',str(init)]
        cmd+=[':app:assembleDebug','--offline','--max-workers=2']
        with (CACHE/('evaluation-build.log' if evaluation else 'normal-build.log')).open('w') as out:subprocess.run(cmd,env=env,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=900)
    result=None
    try:
        build(True);device('install','-r',apk)
        run=device('shell','am','instrument','-w','com.eilo/com.eilo.foundation.OfflineSpeechEvaluationInstrumentation').stdout
        (CACHE/'instrumentation.log').write_text(run)
        if 'eilo_offline_speech=PASS' not in run or 'INSTRUMENTATION_CODE: -1' not in run:raise ValueError('SDK speech evaluation failed')
        result=json.loads(device('exec-out','run-as','com.eilo','cat','files/offline-speech-evaluation.json').stdout)
        device('shell','run-as','com.eilo','rm','files/offline-speech-evaluation.json')
    finally:
        device('shell','am','force-stop','com.eilo');build(False)
        with zipfile.ZipFile(apk) as z:
            if any(b'OfflineSpeechEvaluationInstrumentation' in z.read(n) for n in z.namelist() if re.fullmatch('classes[0-9]*\\.dex',n)):raise ValueError('evaluator remains in normal APK')
        device('install','-r',apk)
        if 'OfflineSpeechEvaluationInstrumentation' in device('shell','dumpsys','package','com.eilo').stdout:raise ValueError('evaluator remains installed')
    if result is None:raise ValueError('no verified result')
    result['normal_APK_restored']='PASS';(CACHE/'android-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Actual Android SDK voice registry/gate checks PASS; normal APK restored. Physical offline/traffic/quality evidence NOT RUN.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,subprocess.SubprocessError) as e:raise SystemExit('Offline speech check unavailable ('+type(e).__name__+'); see ignored logs.') from None
