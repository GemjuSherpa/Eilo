"""Closed aggregate calibration diagnostics, without acceptance authority."""
import argparse
import html
import json
from pathlib import Path
from calibrate import HERE,FRESH,need,read,sha,pins,policy,SOURCES,corpus_report


def closed(value,keys):need(type(value) is dict and set(value)==set(keys.split()))


def comparisons(rows,total):
    need(type(rows) is list and len(rows)==2 and [r['source'] for r in rows]==list(SOURCES))
    for r in rows:
        closed(r,'source raw mapped outside_development_score_range')
        for m in ('raw','mapped'):corpus_report.validate_metrics(r[m],total)
        for k in ('available','unavailable','correct','word_errors','reference_words','character_errors','reference_characters'):
            need(r['raw'][k]==r['mapped'][k])
        corpus_report.integer(r['outside_development_score_range'],r['raw']['available'])


def validate_freeze(f):
    closed(f,'schema_version purpose protocol_sha256 source_pins prior_results_sha256 development_manifest_sha256 development_counts_sha256 private_model_sha256 development_cases development test_use native_calibration production')
    need(type(f['schema_version']) is int and f['schema_version']==1 and f['purpose']==policy()['purpose'])
    need(f['protocol_sha256']==sha(HERE/'protocol.json') and f['source_pins']==pins())
    prior=read(FRESH/'results.json')
    need(f['prior_results_sha256']==sha(FRESH/'results.json') and f['development_manifest_sha256']==prior['selection']['partitions']['dev']['manifest_sha256'])
    need(f['development_counts_sha256']==prior['partitions']['dev']['private_counts_sha256'])
    corpus_report.digest(f['private_model_sha256']);need(type(f['development_cases']) is int and f['development_cases']==30)
    comparisons(f['development'],30)
    need(all(r['raw']==p['metrics'] for r,p in zip(f['development'],prior['partitions']['dev']['sources'])))
    need(f['test_use']==policy()['test_use'] and f['native_calibration']=='NOT_ESTABLISHED' and f['production']=='NOT_ENABLED')


def validate_selection(s):
    closed(s,'schema_version source_pins protocol_sha256 excluded_manifest_sha256 excluded_cases test_cases test_speakers manifest_sha256 development_speaker_overlap prior_speaker_overlap speaker_scope utterance_overlap encoded_overlap pcm_overlap model_training_overlap')
    need(type(s['schema_version']) is int and s['schema_version']==1 and s['source_pins']==pins() and s['protocol_sha256']==sha(HERE/'protocol.json'))
    p=read(FRESH/'results.json')['selection'];expected=[p['prior_manifest_sha256']]+[p['partitions'][k]['manifest_sha256'] for k in ('dev','test')]
    need(s['excluded_manifest_sha256']==expected and type(s['excluded_cases']) is int and s['excluded_cases']==90)
    need(type(s['test_cases']) is int and s['test_cases']==30 and type(s['test_speakers']) is int and 15<=s['test_speakers']<=30)
    corpus_report.digest(s['manifest_sha256']);need(s['manifest_sha256'] not in expected)
    need(s['speaker_scope']==policy()['speaker_holdout']);corpus_report.integer(s['prior_speaker_overlap'],s['test_speakers'])
    for k in ('development_speaker_overlap','utterance_overlap','encoded_overlap','pcm_overlap'):need(type(s[k]) is int and s[k]==0)
    need(s['model_training_overlap']=='UNKNOWN')


def validate(r):
    closed(r,'schema_version purpose freeze_sha256 freeze_commit source_pins selection native test test_use threshold_fitting model_training_overlap native_calibration threshold_authorization production physical')
    need(type(r['schema_version']) is int and r['schema_version']==1 and r['purpose']=='OFFLINE_CALIBRATOR_HELD_OUT_DIAGNOSTIC')
    validate_freeze(read(HERE/'freeze.json'));need(r['freeze_sha256']==sha(HERE/'freeze.json') and r['source_pins']==pins())
    need(type(r['freeze_commit']) is str and len(r['freeze_commit'])==40 and all(c in '0123456789abcdef' for c in r['freeze_commit']))
    validate_selection(r['selection']);corpus_report.validate(r['native'])
    need(r['native']['provenance']['manifest_sha256']==r['selection']['manifest_sha256'] and r['native']['cases_total']==30)
    comparisons(r['test'],30)
    need(all(a['raw']==b['metrics'] for a,b in zip(r['test'],r['native']['sources'])))
    for k,v in dict(test_use='EVALUATION_ONLY_NO_REFITTING',threshold_fitting='NOT_PERFORMED',model_training_overlap='UNKNOWN',native_calibration='NOT_ESTABLISHED',threshold_authorization='NOT_GRANTED',production='NOT_ENABLED',physical='NOT_RUN').items():need(r[k]==v)
    return dict(test_cases=30,excluded_prior_cases=90,development_cases=30,paths=[dict(source=s['source'],raw_brier=s['raw']['brier_score'],mapped_brier=s['mapped']['brier_score'],raw_acceptance=s['raw']['policy_0_85_diagnostic'],mapped_acceptance=s['mapped']['policy_0_85_diagnostic'],outside_development_range=s['outside_development_score_range']) for s in r['test']],native_calibration='NOT_ESTABLISHED',production='NOT_ENABLED',physical='NOT_RUN')


def export(r,output):
    summary=validate(r);need(not output.exists());output.mkdir(parents=True)
    (output/'summary.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    (output/'summary.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Offline calibrator pilot</title><h1>Frozen development calibrator: held-out pilot</h1>'
        '<p>Thirty previously examined development clips fit separate isotonic step functions. Thirty new curator-test utterances exclude all ninety prior clips; earlier test speakers are reused and reported, with development speakers excluded. '
        'Small correlated cohorts, exact-transcription proxy labels and unknown model-training overlap prevent qualification. '
        'Fixed 0.85 is descriptive; no test refitting, threshold selection, production activation or physical acceptance.</p><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre></html>\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,default=HERE/'results.json');p.add_argument('--output',type=Path)
    a=p.parse_args();r=read(a.report);print(json.dumps(export(r,a.output) if a.output else validate(r),indent=2))
