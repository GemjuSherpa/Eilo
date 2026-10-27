"""Require a committed candidate hash before new held-out native inference."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from calibrate import HERE,CORPUS,need,read,sha,canonical_digest,pins,mapped_metrics,check_model,SOURCES
from select_test import verify


def committed_freeze(commit):
    need(type(commit) is str and re.fullmatch('[0-9a-f]{40}',commit))
    root=HERE.parents[2]
    subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],cwd=root,check=True,capture_output=True)
    raw=subprocess.check_output(['git','show',commit+':Eilo/packages/asr-calibration/freeze.json'],cwd=root)
    need(raw==(HERE/'freeze.json').read_bytes())
    return read(HERE/'freeze.json')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('cohort','prior','development','previous-test','private-model','source','cache','build','ndk','android-sdk','cmake','output'):
        parser.add_argument('--'+n,required=True,type=Path)
    parser.add_argument('--serial',choices=['emulator-5554'],required=True)
    parser.add_argument('--freeze-commit',required=True)
    a=parser.parse_args()
    from calibration_report import validate_freeze,validate_selection,validate
    frozen=committed_freeze(a.freeze_commit);validate_freeze(frozen)
    need(not a.output.exists() and not a.build.exists())
    private=read(a.private_model)
    need(set(private)=={'schema_version','protocol_sha256','source_pins','development_counts_sha256','models'})
    need(sha(a.private_model)==frozen['private_model_sha256'] and private['schema_version']==1 and private['source_pins']==pins())
    need(private['protocol_sha256']==frozen['protocol_sha256'] and private['development_counts_sha256']==frozen['development_counts_sha256'])
    need(set(private['models'])==set(SOURCES))
    for m in private['models'].values():check_model(m)
    paths=[a.prior,a.development,a.previous_test]
    manifest=verify(a.cohort,paths);selection=read(a.cohort/'selection.json');validate_selection(selection)
    need(selection['manifest_sha256']==canonical_digest(manifest))
    before=pins();raw_output=a.output.with_name(a.output.stem+'-native.json');need(not raw_output.exists())
    command=[sys.executable,str(CORPUS/'run_android.py'),'--manifest',str(a.cohort/'test/manifest.json'),'--output',str(raw_output),'--serial',a.serial]
    for n in ('source','cache','build','ndk','android_sdk','cmake'):command+=['--'+n.replace('_','-'),str(getattr(a,n))]
    subprocess.run(command,check=True)
    native=read(raw_output)
    rows=read(a.build/'completed-private.json');need(set(rows)=={'status','cases'} and rows['status']=='COMPLETED')
    cases=rows['cases'];need([r['case_id'] for r in cases]==[c['id'] for c in manifest['cases']])
    need(canonical_digest(cases)==native['provenance']['case_counts_sha256'])
    need(before==pins() and sha(a.private_model)==frozen['private_model_sha256'])
    result=dict(schema_version=1,purpose='OFFLINE_CALIBRATOR_HELD_OUT_DIAGNOSTIC',freeze_sha256=sha(HERE/'freeze.json'),freeze_commit=a.freeze_commit,
        source_pins=before,selection=selection,native=native,test=mapped_metrics(cases,private['models']),
        test_use='EVALUATION_ONLY_NO_REFITTING',threshold_fitting='NOT_PERFORMED',model_training_overlap='UNKNOWN',
        native_calibration='NOT_ESTABLISHED',threshold_authorization='NOT_GRANTED',production='NOT_ENABLED',physical='NOT_RUN')
    validate(result);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('Frozen development candidate evaluated once on held-out test; no refit or runtime activation.')


if __name__=='__main__':main()
