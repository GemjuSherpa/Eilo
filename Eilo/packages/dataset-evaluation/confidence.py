"""Offline reliability diagnostics for declared held-out labelled scores; never authorizes policy.
No models, audio, transcript content, network, threshold fitting or native calibration.
"""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import re
from manifests import require, canonical_digest

MAX_BYTES=4*1024*1024
MAX_CASES=10000
PINS={'dataset_manifest_sha256','asr_report_sha256','runtime_sha256','model_sha256'}
KINDS={'MODEL_PROBABILITY','PLACEHOLDER','SYNTHETIC'}


def unique(pairs):
    result={}
    for key,value in pairs:
        require(key not in result,'duplicate JSON key');result[key]=value
    return result


def read(path):
    with Path(path).open('rb') as stream:raw=stream.read(MAX_BYTES+1)
    require(len(raw)<=MAX_BYTES,'input too large')
    try:value=json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=lambda _:None)
    except (UnicodeError,json.JSONDecodeError) as error:raise ValueError('invalid score JSON') from error
    return value,hashlib.sha256(raw).hexdigest()


def digest(value):
    require(type(value) is str and re.fullmatch('[a-f0-9]{64}',value) is not None,'invalid digest')


def validate(value):
    require(type(value) is dict and set(value)=={'schema_version','signal_kind','partition','provenance','cases'},'input schema changed')
    require(type(value['schema_version']) is int and value['schema_version']==1,'unsupported version')
    require(type(value['signal_kind']) is str and value['signal_kind'] in KINDS and value['partition']=='DECLARED_HELD_OUT','signal/partition missing')
    pins=value['provenance'];require(type(pins) is dict and set(pins)==PINS,'provenance schema changed')
    for item in pins.values():digest(item)
    cases=value['cases'];require(type(cases) is list and 1<=len(cases)<=MAX_CASES,'case count invalid')
    ids=set()
    for case in cases:
        require(type(case) is dict and set(case)=={'case_sha256','confidence','exact_match'},'case schema changed')
        digest(case['case_sha256']);require(case['case_sha256'] not in ids,'duplicate case');ids.add(case['case_sha256'])
        score=case['confidence']
        require(type(score) in (float,int) and math.isfinite(score) and 0<=score<=1,'invalid confidence')
        require(type(case['exact_match']) is bool,'exact-match label must be boolean')
    return cases



def bind_labels(value,manifest,benchmark):
    """Consistency binding, not authentication of scores, audio, labels or training exclusion."""
    from baseline import bind
    cases=validate(value);bind(manifest,benchmark)
    require(all(c['task']=='asr' and c.get('split')=='test' for c in manifest['cases']), 'ASR test partition required')
    expected={'dataset_manifest_sha256':canonical_digest(manifest),'asr_report_sha256':canonical_digest(benchmark),
              'runtime_sha256':benchmark['adapter']['binary_sha256'],'model_sha256':benchmark['adapter']['model_sha256']}
    require(value['provenance']==expected,'source report/manifest/model/runtime changed')
    require(benchmark['adapter']['kind']!='synthetic' or value['signal_kind']=='SYNTHETIC','synthetic source mislabelled')
    truth={canonical_digest({'manifest_sha256':expected['dataset_manifest_sha256'],'case_id':c['id']}):
           c['word_errors']==0 and c['character_errors']==0 for c in benchmark['cases']}
    require(len(cases)==len(truth) and {c['case_sha256'] for c in cases}==set(truth),'missing/extra source scores')
    require(all(c['exact_match']==truth[c['case_sha256']] for c in cases),'exact-match labels changed')


def auc(cases):
    """Correctness is positive; all tied pairs contribute one half, order independent."""
    ordered=sorted(cases,key=lambda c:c['confidence']);positive=sum(c['exact_match'] for c in ordered)
    negative=len(ordered)-positive
    if not positive or not negative:return None
    lower_negative=0;numerator=0.;index=0
    while index<len(ordered):
        end=index+1
        while end<len(ordered) and ordered[end]['confidence']==ordered[index]['confidence']:end+=1
        p=sum(c['exact_match'] for c in ordered[index:end]);n=end-index-p
        numerator+=p*(lower_negative+n/2);lower_negative+=n;index=end
    return numerator/(positive*negative)


def summarize(value,input_sha256):
    cases=validate(value);digest(input_sha256);total=len(cases)
    bins=[]
    for index in range(10):
        rows=[c for c in cases if min(int(c['confidence']*10),9)==index]
        count=len(rows)
        bins.append({'lower':index/10,'upper':(index+1)/10,'upper_inclusive':index==9,'count':count,
                     'mean_confidence':math.fsum(c['confidence'] for c in rows)/count if count else None,
                     'accuracy':sum(c['exact_match'] for c in rows)/count if count else None})
    curve=[]
    for index in range(101):
        threshold=index/100
        rows=[c for c in cases if c['confidence']>=threshold];count=len(rows)
        errors=sum(not c['exact_match'] for c in rows)
        curve.append({'threshold':threshold,'accepted':count,'errors':errors,'coverage':count/total,
                      'risk':errors/count if count else None})
    constant=len({c['confidence'] for c in cases})==1
    classes=len({c['exact_match'] for c in cases})
    status=('UNUSABLE_DECLARED_SIGNAL' if value['signal_kind']!='MODEL_PROBABILITY' else
            'UNINFORMATIVE_CONSTANT_SIGNAL' if constant else
            'INSUFFICIENT_LABEL_VARIATION' if classes<2 else 'DIAGNOSTIC_ONLY')
    return {'schema_version':1,'purpose':'ASR_CONFIDENCE_DIAGNOSTIC','status':status,
            'input_sha256':input_sha256,'provenance':dict(value['provenance']),'signal_kind':value['signal_kind'],
            'partition':'DECLARED_HELD_OUT','provenance_authentication':'NOT_ESTABLISHED',
            'native_calibration':'NOT_RUN','threshold_authorization':'NOT_GRANTED','production_readiness':'NOT_ENABLED',
            'physical_gates':'NOT_RUN','quality_acceptance':'NOT_ASSESSED','counts':{'cases':total,'correct':sum(c['exact_match'] for c in cases)},
            'brier_score':math.fsum((c['confidence']-int(c['exact_match']))**2 for c in cases)/total,
            'ece_10_bins':math.fsum(b['count']/total*abs(b['mean_confidence']-b['accuracy']) for b in bins if b['count']),
            'correctness_auroc':auc(cases),'reliability_bins':bins,'coverage_curve':curve,
            'policy_0_85_diagnostic':curve[85]}


def export(value,input_sha256,directory,manifest=None,benchmark=None):
    require((manifest is None)==(benchmark is None),"both source inputs required")
    if manifest is not None:bind_labels(value,manifest,benchmark)
    report=summarize(value,input_sha256)
    report["label_binding"]="CONSISTENCY_CHECKED_BENCHMARK_LABELS" if manifest is not None else "DECLARED_ONLY"
    directory=Path(directory)
    # One newly owned directory prevents partial overwrite or replacement of evidence.
    directory.mkdir(parents=True,exist_ok=False)
    encoded=json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n'
    (directory/'summary.json').write_text(encoded)
    metric_rows=''.join('<tr><th>'+html.escape(key)+'</th><td>'+html.escape(str(report[key]))+'</td></tr>'
                        for key in ('status','brier_score','ece_10_bins','correctness_auroc','label_binding'))
    bin_rows=''.join('<tr>'+''.join('<td>'+html.escape(str(row[key]))+'</td>' for key in
                    ('lower','upper','upper_inclusive','count','mean_confidence','accuracy'))+'</tr>' for row in report['reliability_bins'])
    document='''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>ASR confidence diagnostics</title><style>body{font:16px system-ui;max-width:1000px;margin:2rem auto;padding:1rem}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{border-collapse:collapse;margin:1rem 0}th,td{border:1px solid #ccc;padding:.5rem;text-align:left}</style>
<h1>ASR confidence diagnostics</h1><p>Diagnostic only. Input provenance and held-out status are declarations, not authenticated observations. No threshold fitting or authorization; native calibration and physical gates NOT_RUN. Production NOT_ENABLED.</p>'''+ '<table><caption>Diagnostic metrics</caption>'+metric_rows+'</table><table><caption>Reliability bins</caption><tr><th>Lower</th><th>Upper</th><th>Upper inclusive</th><th>Cases</th><th>Mean confidence</th><th>Accuracy</th></tr>'+bin_rows+'</table><details><summary>Full aggregate report</summary><pre>'+html.escape(encoded)+'</pre></details></html>'
    (directory/'summary.html').write_text(document)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scores',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--manifest',type=Path);parser.add_argument('--asr-report',type=Path)
    args=parser.parse_args();require((args.manifest is None)==(args.asr_report is None),'both source inputs required')
    value,pin=read(args.scores)
    manifest=read(args.manifest)[0] if args.manifest is not None else None
    benchmark=read(args.asr_report)[0] if args.asr_report is not None else None
    report=export(value,pin,args.output,manifest,benchmark)
    print(report['status']+'; native calibration NOT_RUN, policy NOT_GRANTED.')


if __name__=='__main__':main()
