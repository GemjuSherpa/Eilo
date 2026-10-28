"""Apply the unchanged private development calibrator to paired cached noise variants."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from calibrate import HERE,CORPUS,DATA,need,read,sha,canonical_digest,mapped_metrics,SOURCES,check_model
from calibration_report import validate as validate_clean,validate_freeze


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


suite_runner=module('calibrator_noise_suite',CORPUS/'noise_suite.py')
suite_report=module('calibrator_noise_suite_report',CORPUS/'noise_report.py')


def policy():return read(HERE/'noise-protocol.json')


def noise_pins():
    paths=[HERE/n for n in ('noise_pilot.py','noise-protocol.json','calibrate.py','freeze.json','results.json')]
    paths += [CORPUS/n for n in ('noise_suite.py','noise_report.py','run_android.py','diagnostics.py','main.cpp')]
    paths += [DATA/n for n in ('noise.py','audio.py','benchmark.py','manifests.py')]
    return {str(p.relative_to(HERE.parent)):sha(p) for p in paths}


def committed_protocol(commit):
    need(type(commit) is str and re.fullmatch('[0-9a-f]{40}',commit))
    root=HERE.parents[2]
    subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],cwd=root,capture_output=True,check=True)
    for name in ('noise-protocol.json','noise_pilot.py'):
        raw=subprocess.check_output(['git','show',commit+':Eilo/packages/asr-calibration/'+name],cwd=root)
        need(raw==(HERE/name).read_bytes())


def model(private_path):
    frozen=read(HERE/'freeze.json');validate_freeze(frozen)
    need(sha(private_path)==frozen['private_model_sha256'])
    value=read(private_path)
    need(set(value)=={'schema_version','protocol_sha256','source_pins','development_counts_sha256','models'})
    need(value['source_pins']==frozen['source_pins'] and value['development_counts_sha256']==frozen['development_counts_sha256'])
    need(value['protocol_sha256']==frozen['protocol_sha256'] and type(value['schema_version']) is int and value['schema_version']==1)
    need(set(value['models'])==set(SOURCES))
    for m in value['models'].values():check_model(m)
    return value['models']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('clean','noise','noisy-output','private-model','source','cache','build','ndk','android-sdk','cmake','raw-output','output'):
        p.add_argument('--'+n,required=True,type=Path)
    p.add_argument('--serial',choices=['emulator-5554'],required=True);p.add_argument('--protocol-commit',required=True)
    a=p.parse_args();committed_protocol(a.protocol_commit);before=noise_pins();config=policy()
    need(not a.output.exists() and not a.raw_output.exists() and not a.build.exists() and not a.noisy_output.exists())
    clean=read(a.clean);baseline=read(HERE/'results.json');validate_clean(baseline)
    need(canonical_digest(clean)==baseline['selection']['manifest_sha256'] and len(clean['cases'])==config['parents'])
    noise=read(a.noise)
    need(canonical_digest(noise)==read(CORPUS/'noise-results/suite.json')['noise_manifest_sha256'])
    models=model(a.private_model);model_hash=sha(a.private_model)
    # The existing mixer validates receipts, formats and input hashes; no source corpus is modified.
    from noise import variants
    noisy=variants(clean,a.clean.parent,noise,a.noise.parent,a.noisy_output,config['snrs'],config['seed'])
    groups=suite_runner.verify_audio(clean,a.clean.parent,noisy,a.noisy_output,noise,a.noise.parent)
    command=[sys.executable,str(CORPUS/'noise_suite.py'),'--clean',str(a.clean),'--noise',str(a.noise),
             '--noisy',str(a.noisy_output/'manifest.json'),'--output',str(a.raw_output),'--serial',a.serial]
    for n in ('source','cache','build','ndk','android_sdk','cmake'):command+=['--'+n.replace('_','-'),str(getattr(a,n))]
    subprocess.run(command,check=True)
    receipt=read(a.raw_output/'suite.json');reports={str(s):read(a.raw_output/f'snr{s}.json') for s in config['snrs']}
    suite_report.validate_suite(receipt,reports,baseline['native'])
    mapped={}
    for snr in config['snrs']:
        rows=read(a.build/f'snr{snr}/completed-private.json')
        need(set(rows)=={'status','cases'} and rows['status']=='COMPLETED')
        cases=rows['cases'];raw=reports[str(snr)]
        need([c['case_id'] for c in cases]==[c['id'] for c in groups[snr]])
        need(canonical_digest(cases)==raw['provenance']['case_counts_sha256'])
        need(sha(a.raw_output/f'snr{snr}.json')==receipt['reports'][str(snr)])
        mapped[str(snr)]=mapped_metrics(cases,models)
    need(before==noise_pins() and sha(a.private_model)==model_hash)
    result=dict(schema_version=1,purpose=config['purpose'],protocol_sha256=sha(HERE/'noise-protocol.json'),protocol_commit=a.protocol_commit,
        source_pins=before,calibrator_freeze_sha256=sha(HERE/'freeze.json'),clean_pilot_sha256=sha(HERE/'results.json'),
        private_model_sha256=model_hash,suite=receipt,reports=reports,mapped=mapped,pairing=config['pairing'],
        calibrator_refit='NOT_PERFORMED',threshold_fitting='NOT_PERFORMED',native_calibration='NOT_ESTABLISHED',
        threshold_authorization='NOT_GRANTED',production='NOT_ENABLED',physical='NOT_RUN')
    from noise_pilot_report import validate
    validate(result);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('Frozen calibrator applied to all ninety paired variants; no refit or production activation.')


if __name__=='__main__':main()
