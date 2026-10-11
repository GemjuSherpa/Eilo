#!/usr/bin/env python3
"""Aggregate frozen synthetic results. Physical trials are never inferred from a file test."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent

def summarize(report,manifest):
    fixtures=manifest['fixtures'];cases=report['cases']
    if len(cases)!=len(fixtures):raise ValueError('missing trial cases')
    wake=detected=negative=false=diagnostic=multiple=0
    for actual,expected in zip(cases,fixtures):
        if actual['file']!=expected['file'] or actual['kind']!=expected['kind'] or type(actual['detections']) is not int or actual['detections']<0:raise ValueError('mismatched frozen trial')
        if actual['kind']=='wake':wake+=1;detected+=int(actual['detections']>=1);multiple+=int(actual['detections']>1)
        elif actual['kind']=='nonwake':negative+=1;false+=actual['detections']
        else:diagnostic+=1
    return {'kind':'frozen-synthetic-file-evaluation','positive_cases':wake,'detected_positive_cases':detected,
        'missed_positive_cases':wake-detected,'multiple_positive_cases':multiple,'negative_cases':negative,'false_activation_events':false,
        'excluded_diagnostics':diagnostic,'unique_audio_files':len({i['sha256'] for i in fixtures}),
        'detection_fraction':detected/wake if wake else None,'physical_quiet':'NOT RUN','physical_8h_ambient':'NOT RUN',
        'physical_false_activations_per_hour':None,'speaker_headphone_microphone_trials':'NOT RUN'}

def main():
    manifest=json.loads((HERE/'tests/fixtures/manifest.json').read_text())
    report=json.loads((HERE/'tests/android-device-results.json').read_text())
    result=summarize(report,manifest)
    (HERE/'tests/wake-trial-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
