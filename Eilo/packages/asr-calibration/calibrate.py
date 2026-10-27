"""Development-only isotonic pilot; private model, no production confidence activation."""
import argparse
import bisect
import importlib.util
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
FRESH=HERE.parent/'asr-fresh-split'
sys.path.insert(0,str(FRESH))
from shared import CORPUS,DATA,SDK,need,sha,read,canonical_digest,normalize,validate_manifest,source_pins as previous_pins,corpus_report,SOURCES
from diagnostics import metrics,summarize
spec=importlib.util.spec_from_file_location('calibration_fresh_report',FRESH/'fresh_report.py')
fresh_report=importlib.util.module_from_spec(spec);spec.loader.exec_module(fresh_report)


def policy(): return read(HERE/'protocol.json')


def pins():
    result=previous_pins()
    for path in [HERE/n for n in ('calibrate.py','select_test.py','evaluate.py','protocol.json')]+[CORPUS/'run_android.py']:
        result[str(path.relative_to(HERE.parent))]=sha(path)
    return result


def fit(pairs):
    need(type(pairs) is list and 0<len(pairs)<=10000)
    grouped={}
    for score,label in pairs:
        need(type(score) in (int,float) and math.isfinite(score) and 0<=score<=1 and type(label) is bool)
        count,correct=grouped.get(score,(0,0));grouped[score]=(count+1,correct+int(label))
    blocks=[]
    for score,(count,correct) in sorted(grouped.items()):
        blocks.append(dict(upper=score,count=count,correct=correct))
        while len(blocks)>=2 and blocks[-2]['correct']*blocks[-1]['count']>blocks[-1]['correct']*blocks[-2]['count']:
            b=blocks.pop();a=blocks.pop();blocks.append(dict(upper=b['upper'],count=a['count']+b['count'],correct=a['correct']+b['correct']))
    return dict(minimum=min(grouped),maximum=max(grouped),blocks=blocks)


def check_model(model):
    need(type(model) is dict and set(model)=={'minimum','maximum','blocks'})
    for v in (model['minimum'],model['maximum']):need(type(v) in (int,float) and math.isfinite(v) and 0<=v<=1)
    need(model['minimum']<=model['maximum'])
    blocks=model['blocks'];need(type(blocks) is list and 0<len(blocks)<=10000)
    upper=-1;value=-1
    for b in blocks:
        need(type(b) is dict and set(b)=={'upper','count','correct'})
        need(type(b['upper']) in (int,float) and math.isfinite(b['upper']) and model['minimum']<=b['upper']<=model['maximum'] and b['upper']>upper)
        need(type(b['count']) is int and 1<=b['count']<=10000 and type(b['correct']) is int and 0<=b['correct']<=b['count'])
        need(b['correct']/b['count']>=value);upper=b['upper'];value=b['correct']/b['count']
    need(upper==model['maximum'] and sum(b['count'] for b in blocks)<=10000)


def predict(model,score):
    check_model(model);need(type(score) in (int,float) and math.isfinite(score) and 0<=score<=1)
    i=min(bisect.bisect_left([b['upper'] for b in model['blocks']],score),len(model['blocks'])-1)
    b=model['blocks'][i];return b['correct']/b['count']


def mapped_metrics(cases,models):
    result=[]
    for index,source in enumerate(SOURCES):
        model=models[source];check_model(model);raw=[];mapped=[];outside=0
        for case in cases:
            row=case['paths'][index];need(row['source']==source)
            if row['status']=='UNAVAILABLE':continue
            need(row['status']=='AVAILABLE')
            p=row['confidence'];raw.append(row);mapped.append(dict(row,confidence=predict(model,p)))
            outside+=int(p<model['minimum'] or p>model['maximum'])
        result.append(dict(source=source,raw=metrics(raw,len(cases)),mapped=metrics(mapped,len(cases)),outside_development_score_range=outside))
    return result


def freeze(private_counts,private_output,public_output):
    need(not private_output.exists() and not public_output.exists())
    prior=read(FRESH/'results.json');fresh_report.validate(prior)
    # Load only the development rows for fitting; the previously examined test cohort is not fitted.
    dev=read(private_counts)['dev']
    need(canonical_digest(dev)==prior['partitions']['dev']['private_counts_sha256'])
    need(len(dev)==policy()['development_cases'] and len({r['case_id'] for r in dev})==len(dev))
    models={}
    for i,source in enumerate(SOURCES):
        available=[r['paths'][i] for r in dev if r['paths'][i]['status']=='AVAILABLE']
        need(len(available)>=10 and {r['exact_match'] for r in available}=={True,False} and all(r['source']==source for r in available))
        models[source]=fit([(r['confidence'],r['exact_match']) for r in available])
    value=dict(schema_version=1,protocol_sha256=sha(HERE/'protocol.json'),source_pins=pins(),development_counts_sha256=canonical_digest(dev),models=models)
    private_output.parent.mkdir(parents=True,exist_ok=True);private_output.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    evidence=dict(schema_version=1,purpose=policy()['purpose'],protocol_sha256=sha(HERE/'protocol.json'),source_pins=pins(),
        prior_results_sha256=sha(FRESH/'results.json'),development_manifest_sha256=prior['selection']['partitions']['dev']['manifest_sha256'],
        development_counts_sha256=canonical_digest(dev),private_model_sha256=sha(private_output),development_cases=len(dev),
        development=mapped_metrics(dev,models),test_use=policy()['test_use'],native_calibration='NOT_ESTABLISHED',production='NOT_ENABLED')
    public_output.write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')
    return evidence


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('private-counts','private-output','public-output'):p.add_argument('--'+n,required=True,type=Path)
    a=p.parse_args();freeze(a.private_counts,a.private_output,a.public_output)
    print('Development-only candidate frozen locally; commit its public hash before test inference.')
