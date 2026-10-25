"""Validate aggregate-only corpus evidence; no inference, corpus download or authorization."""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'dataset-evaluation'))
from manifests import canonical_digest
from diagnostics import SOURCES,REASONS,need,number
from confidence import unique

HERE=Path(__file__).resolve().parent
SDK=HERE.parent/'asr-sdk-score-probe'
PINS=('main.cpp','CMakeLists.txt','run_android.py','diagnostics.py')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def digest(value):need(type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value))
def integer(value,maximum=1000000):need(type(value) is int and 0<=value<=maximum)
def equal(a,b):need(type(a) in (int,float) and math.isfinite(a) and abs(a-b)<=1e-9*max(1,abs(b)))

def validate_metrics(m,total):
    need(type(m) is dict and set(m)=={'cases_total','available','unavailable','score_coverage','correct','word_errors','reference_words','character_errors','reference_characters','wer_available','cer_available','metrics_population','label_variation','constant_signal','correctness_pairs','score_moments','brier_score','ece_10_bins','correctness_auroc','reliability_bins','coverage_curve','policy_0_85_diagnostic'})
    for key in ['cases_total','available','unavailable','correct','word_errors','reference_words','character_errors','reference_characters','label_variation']:integer(m[key])
    n=m['available'];correct=m['correct'];need(m['cases_total']==total and n+m['unavailable']==total and correct<=n)
    equal(m['score_coverage'],n/total);need(m['metrics_population']=='AVAILABLE_SCORES_ONLY')
    need(m['label_variation']==(0 if not n else 1 if correct in [0,n] else 2) and type(m['constant_signal']) is bool)
    for metric,errors,denom in [('wer_available','word_errors','reference_words'),('cer_available','character_errors','reference_characters')]:
        if not n:need(m[metric] is None and m[errors]==0 and m[denom]==0)
        else:need(m[denom]>0);equal(m[metric],m[errors]/m[denom])
    moments=m['score_moments'];need(type(moments) is dict and set(moments)=={'sum_probability','sum_squared_probability','sum_probability_correct'})
    for value in moments.values():number(value,0,n)
    p=moments['sum_probability'];p2=moments['sum_squared_probability'];py=moments['sum_probability_correct']
    need(p2<=p+1e-9 and py<=min(p,correct)+1e-9 and py>=p-(n-correct)-1e-9)
    if n:need(p2>=p*p/n-1e-9);equal(m['brier_score'],(p2-2*py+correct)/n);number(m['brier_score'])
    else:need(m['brier_score'] is None and not m['constant_signal'])
    bins=m['reliability_bins'];need(type(bins) is list and len(bins)==10)
    count=0;truth=0;confidence=0;ece=0
    for i,b in enumerate(bins):
        need(type(b) is dict and set(b)=={'lower','upper','upper_inclusive','count','mean_confidence','accuracy'})
        equal(b['lower'],i/10);equal(b['upper'],(i+1)/10);need(b['upper_inclusive'] is (i==9));integer(b['count'],n)
        c=b['count'];count+=c
        if c:
            number(b['mean_confidence'],i/10-1e-12,(i+1)/10+1e-12);number(b['accuracy'])
            equal(b['accuracy']*c,round(b['accuracy']*c));truth+=b['accuracy']*c;confidence+=b['mean_confidence']*c;ece+=c*abs(b['mean_confidence']-b['accuracy'])
        else:need(b['mean_confidence'] is None and b['accuracy'] is None)
    need(count==n);equal(truth,correct);equal(confidence,p)
    if n:equal(m['ece_10_bins'],ece/n)
    else:need(m['ece_10_bins'] is None)
    pairs=m['correctness_pairs'];need(type(pairs) is dict and set(pairs)=={'higher','tied','lower'})
    for value in pairs.values():integer(value,total*total)
    pair_total=correct*(n-correct);need(sum(pairs.values())==pair_total)
    if pair_total:equal(m['correctness_auroc'],(pairs['higher']+.5*pairs['tied'])/pair_total)
    else:need(m['correctness_auroc'] is None)
    curve=m['coverage_curve'];need(type(curve) is list and len(curve)==101)
    previous=(n,n-correct,correct)
    for i,row in enumerate(curve):
        need(type(row) is dict and set(row)=={'threshold','accepted','errors','coverage_all_cases','risk'})
        equal(row['threshold'],i/100);integer(row['accepted'],n);integer(row['errors'],n-correct)
        a=row['accepted'];e=row['errors'];need(e<=a and a<=previous[0] and e<=previous[1] and a-e<=previous[2]);previous=(a,e,a-e)
        equal(row['coverage_all_cases'],a/total)
        if a:equal(row['risk'],e/a)
        else:need(row['risk'] is None)
    need(curve[0]['accepted']==n and curve[0]['errors']==n-correct and m['policy_0_85_diagnostic']==curve[85])
    return m


def validate(r):
    need(type(r) is dict and set(r)=={'schema_version','purpose','status','dataset','release','cases_total','partition','model_training_overlap','native_calibration','threshold_authorization','production','physical','score','draft','normalization','platform','provenance','sources','rejected_inputs'})
    need(type(r['schema_version']) is int and r['schema_version']==1 and r['purpose']=='CURATOR_TEST_SCORE_DIAGNOSTIC')
    need(r['dataset']=='common_voice' and r['partition']=='CURATOR_TEST' and r['model_training_overlap']=='UNKNOWN')
    need(r['native_calibration']=='NOT_ESTABLISHED' and r['threshold_authorization']=='NOT_GRANTED' and r['production']=='NOT_ENABLED' and r['physical']=='NOT_RUN')
    need(r['score']=='ARITHMETIC_MEAN_ACCEPTED_NON_EOS_TOKEN_PREBIAS_PROBABILITY' and r['draft']=='SAME_UTTERANCE_GREEDY_HYPOTHESIS_NO_REFERENCE')
    need(r['normalization']=='nfkc-casefold-alnum-v1' and r['platform']=='Android API35 ARM64 emulator')
    integer(r['cases_total'],30);need(r['cases_total']>0)
    registry=HERE.parent/'dataset-evaluation/registry.json';cv=next(d for d in json.loads(registry.read_text())['datasets'] if d['id']=='common_voice');need(r['release']==cv['version'])
    p=r['provenance'];need(type(p) is dict and set(p)=={'manifest_sha256','registry_sha256','runtime_sha256','ort_sha256','cxx_sha256','model_bundle_sha256','model_provenance_sha256','source_pins','sdk_pins','overlay_pins','case_counts_sha256'})
    for key in ['manifest_sha256','registry_sha256','runtime_sha256','ort_sha256','cxx_sha256','model_bundle_sha256','model_provenance_sha256','case_counts_sha256']:digest(p[key])
    need(p['registry_sha256']==sha(registry) and p['ort_sha256']=='86e85022fc539963177e478c8e9a8a8219bc3b0d7515bf5297a62986dbc45e7a')
    model=HERE.parent/'asr-runtime/provenance.json';need(p['model_provenance_sha256']==sha(model) and p['model_bundle_sha256']==canonical_digest(json.loads(model.read_text())['model']))
    need(type(p['source_pins']) is dict and set(p['source_pins'])==set(PINS))
    for name in PINS:need(p['source_pins'][name]==sha(HERE/name))
    need(type(p['sdk_pins']) is dict and set(p['sdk_pins'])=={'score_trace.h','overlay.py','overlay-expected.json'})
    for name in p['sdk_pins']:need(p['sdk_pins'][name]==sha(SDK/name))
    need(p['overlay_pins']==json.loads((SDK/'overlay-expected.json').read_text()))
    need(r['rejected_inputs']==['empty','unaligned','nan','out_of_range'])
    need(type(r['sources']) is list and len(r['sources'])==2 and [s['source'] for s in r['sources']]==list(SOURCES))
    for source in r['sources']:
        need(type(source) is dict and set(source)=={'source','status','scope','unavailable_reasons','origin_case_counts','metrics'})
        need(source['scope']=='CURATOR_TEST_DIAGNOSTIC_ONLY');m=validate_metrics(source['metrics'],r['cases_total'])
        need(source['status']==('NO_AVAILABLE_SCORES' if not m['available'] else 'INCOMPLETE_SCORES' if m['unavailable'] else 'DIAGNOSTIC_ONLY'))
        reasons=source['unavailable_reasons'];need(type(reasons) is dict and set(reasons)<=REASONS)
        for value in reasons.values():integer(value,r['cases_total']);need(value>0)
        need(sum(reasons.values())==m['unavailable'])
        origins=source['origin_case_counts'];need(type(origins) is dict and set(origins)<={'greedy','verification','redecode'})
        for value in origins.values():integer(value,m['available'])
        need(sum(origins.values())>=m['available'])
        if source['source']==SOURCES[0]:need(origins.get('greedy',0)==m['available'] and origins.get('verification',0)==0 and origins.get('redecode',0)==0)
        else:need(origins.get('verification',0)+origins.get('redecode',0)>=m['available'])
    need(r['status']==('DIAGNOSTIC_ONLY' if all(s['status']=='DIAGNOSTIC_ONLY' for s in r['sources']) else 'INCOMPLETE_SCORES'))
    return {'status':r['status'],'cases_total':r['cases_total'],'source_counts':[{k:s['metrics'][k] for k in ['available','unavailable','correct']} for s in r['sources']],
            'native_calibration':'NOT_ESTABLISHED','threshold_authorization':'NOT_GRANTED','physical':'NOT_RUN'}


def export(r,directory):
    validate(r);need(not directory.exists());directory.mkdir(parents=True)
    (directory/'summary.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    def fmt(value):return 'unavailable' if value is None else f'{value:.4f}'
    rows=[]
    for s in r['sources']:
        m=s['metrics'];rows.append('<tr><th>'+html.escape(s['source'])+'</th>'+''.join('<td>'+html.escape(str(value))+'</td>' for value in [m['available'],m['unavailable'],m['correct'],fmt(m['wer_available']),fmt(m['brier_score']),fmt(m['ece_10_bins']),fmt(m['correctness_auroc']),fmt(m['policy_0_85_diagnostic']['risk'])])+'</tr>')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><title>Common Voice score diagnostics</title><style>body{font:16px system-ui;margin:2rem;max-width:90rem}table{border-collapse:collapse}th,td{border:1px solid #aaa;padding:.6rem;text-align:right}th:first-child{text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Common Voice score diagnostics</h1><p>Curator test partition; model training overlap UNKNOWN. No calibrated confidence, threshold authorization or production readiness. Physical tests NOT_RUN.</p><p>Missing scores remain in the full-corpus coverage denominator. WER, calibration metrics and risk are conditional on available/accepted scores. The 0.85 row is descriptive, not a recommended threshold.</p><table><caption>Separate source identities; no pooled score</caption><tr><th>Source</th><th>Available</th><th>Unavailable</th><th>Exact matches</th><th>WER available</th><th>Brier</th><th>ECE</th><th>AUROC</th><th>Risk at 0.85</th></tr>'+''.join(rows)+'</table><details><summary>Aggregate JSON</summary><pre>'+html.escape(json.dumps(r,indent=2,allow_nan=False))+'</pre></details></html>'
    (directory/'summary.html').write_text(page)

def read(path):
    need(path.stat().st_size<=1024*1024)
    def reject(_):raise ValueError('invalid nonfinite aggregate')
    return json.loads(path.read_text(),object_pairs_hook=unique,parse_constant=reject)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',type=Path,default=HERE/'corpus-results.json');parser.add_argument('--output',type=Path);args=parser.parse_args()
    value=read(args.report);print(json.dumps(validate(value),indent=2))
    if args.output:export(value,args.output)
