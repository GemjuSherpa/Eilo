"""Closed paired-noise calibration aggregates; no new holdout or release acceptance."""
import argparse
import html
import json
from pathlib import Path
import re
from calibrate import HERE,need,read,sha,canonical_digest
from calibration_report import closed,comparisons,validate as validate_clean
from noise_pilot import policy,noise_pins,suite_report


def validate(r):
    closed(r,'schema_version purpose protocol_sha256 protocol_commit source_pins calibrator_freeze_sha256 clean_pilot_sha256 private_model_sha256 suite reports mapped pairing calibrator_refit threshold_fitting native_calibration threshold_authorization production physical')
    config=policy();need(type(r['schema_version']) is int and r['schema_version']==1 and r['purpose']==config['purpose'])
    need(type(r['protocol_commit']) is str and re.fullmatch('[0-9a-f]{40}',r['protocol_commit']))
    need(r['protocol_sha256']==sha(HERE/'noise-protocol.json') and r['source_pins']==noise_pins())
    need(r['calibrator_freeze_sha256']==sha(HERE/'freeze.json') and r['clean_pilot_sha256']==sha(HERE/'results.json'))
    need(r['private_model_sha256']==read(HERE/'freeze.json')['private_model_sha256'])
    clean=read(HERE/'results.json');validate_clean(clean)
    suite_report.validate_suite(r['suite'],r['reports'],clean['native'])
    need(r['suite']['noise_manifest_sha256']==read(HERE.parent/'asr-corpus-score/noise-results/suite.json')['noise_manifest_sha256'])
    need(r['suite']['parents']==config['parents']==30 and r['suite']['variants']==config['variants']==90)
    need(type(r['mapped']) is dict and set(r['mapped'])=={'20','10','0'})
    rows=[]
    for condition,values in [('clean',clean['test'])]+[(str(s),r['mapped'][str(s)]) for s in config['snrs']]:
        comparisons(values,30)
        if condition!='clean':
            need(r['suite']['reports'][condition]==canonical_file_hash(r['reports'][condition]))
            need(all(a['raw']==b['metrics'] for a,b in zip(values,r['reports'][condition]['sources'])))
        for value in values:
            raw,mapped=value['raw'],value['mapped']
            rows.append(dict(condition=condition,source=value['source'],available=raw['available'],total=30,
                wer_available=raw['wer_available'],raw_brier=raw['brier_score'],mapped_brier=mapped['brier_score'],
                raw_accepted=raw['policy_0_85_diagnostic']['accepted'],raw_errors=raw['policy_0_85_diagnostic']['errors'],
                mapped_accepted=mapped['policy_0_85_diagnostic']['accepted'],mapped_errors=mapped['policy_0_85_diagnostic']['errors'],
                mapped_coverage=mapped['policy_0_85_diagnostic']['coverage_all_cases'],outside_development_range=value['outside_development_score_range']))
    need(r['pairing']==config['pairing'])
    for k,v in dict(calibrator_refit='NOT_PERFORMED',threshold_fitting='NOT_PERFORMED',native_calibration='NOT_ESTABLISHED',threshold_authorization='NOT_GRANTED',production='NOT_ENABLED',physical='NOT_RUN').items():need(r[k]==v)
    return dict(rows=rows,pairing=config['pairing'],native_calibration='NOT_ESTABLISHED',production='NOT_ENABLED',physical='NOT_RUN')


def canonical_file_hash(value):
    import hashlib
    return hashlib.sha256((json.dumps(value,indent=2,allow_nan=False)+'\n').encode()).hexdigest()


def export(r,output):
    summary=validate(r);need(not output.exists());output.mkdir(parents=True)
    (output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    keys=list(summary['rows'][0]);table='<tr>'+''.join('<th>'+html.escape(k)+'</th>' for k in keys)+'</tr>'
    table+=''.join('<tr>'+''.join('<td>'+html.escape(str(row[k]))+'</td>' for k in keys)+'</tr>' for row in summary['rows'])
    (output/'summary.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Frozen calibrator noise pilot</title><h1>Frozen calibrator: paired noise robustness</h1>'
        '<p>Same thirty known-speaker parents at 20, 10 and 0 dB; correlated variants, not new holdout evidence. No refit, threshold selection, streaming/physical validation or production qualification. '
        'Coverage retains thirty cases per condition. Error/calibration metrics are conditional on available scores.</p><table border="1">'+table+'</table></html>\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,default=HERE/'noise-results.json');p.add_argument('--output',type=Path)
    a=p.parse_args();r=read(a.report);print(json.dumps(export(r,a.output) if a.output else validate(r),indent=2))
