#!/usr/bin/env python3
"""Generic simulator SDK speech probe; synthetic offline evidence, no app activation."""
import argparse,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--udid',required=True);a=p.parse_args()
    devices=json.loads(subprocess.run(['xcrun','simctl','list','devices','--json'],check=True,capture_output=True,text=True).stdout)
    if not any(d['udid']==a.udid and d['state']=='Booted' for group in devices['devices'].values() for d in group):raise ValueError('explicit booted simulator required')
    cache=ROOT/'.local/offline-speech';cache.mkdir(parents=True,exist_ok=True)
    sdk=subprocess.run(['xcrun','--sdk','iphonesimulator','--show-sdk-path'],check=True,capture_output=True,text=True).stdout.strip()
    sources=sorted((ROOT/'packages/native-test-seam/Sources/NativeTestSeam').glob('*.swift'));binary=cache/'ios-speech-probe'
    with (cache/'ios-compile.log').open('w') as out:subprocess.run(['xcrun','--sdk','iphonesimulator','swiftc','-swift-version','5','-warnings-as-errors','-target','arm64-apple-ios18.0-simulator','-sdk',sdk,'-parse-as-library',*map(str,sources),str(HERE/'tests/ios_probe.swift'),'-framework','AVFoundation','-framework','Foundation','-framework','CryptoKit','-o',str(binary)],stdout=out,stderr=subprocess.STDOUT,check=True,timeout=120)
    with (cache/'ios-probe.log').open('w') as out:subprocess.run(['xcrun','simctl','spawn',a.udid,str(binary)],stdout=out,stderr=subprocess.STDOUT,check=True,timeout=60)
    rows=[l.removeprefix('EILO_SPEECH_RESULT\t') for l in (cache/'ios-probe.log').read_text().splitlines() if l.startswith('EILO_SPEECH_RESULT\t')]
    if len(rows)!=1:raise ValueError('no verified SDK report')
    report=json.loads(rows[0]);assert report['default_unknown_offline_gate']=='PASS'
    (cache/'ios-results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('iOS simulator SDK probe PASS; offline evidence is synthetic, physical/traffic/intelligibility NOT RUN.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,subprocess.SubprocessError) as e:raise SystemExit('Offline iOS speech check unavailable ('+type(e).__name__+'); see ignored logs.') from None
