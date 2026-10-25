"""Privacy-reduced corpus diagnostics; curator test partition is not training independence."""
from collections import Counter
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'dataset-evaluation'))
from benchmark import score_case
from confidence import auc

SOURCES=('GREEDY_PREBIAS_MEAN_V1','SELF_DRAFT_PREBIAS_MEAN_V1')
REASONS={'INCOMPLETE_DECODE','NO_EOS_OR_OUTPUT_CAP','EOS_WITHOUT_USABLE_SCORES','GREEDY_UNAVAILABLE','COLLECTOR_ERROR'}


def need(value):
    if not value:raise ValueError('invalid corpus score evidence')


def number(value,lo=0,hi=1):
    need(type(value) in (int,float) and math.isfinite(value) and lo<=value<=hi)


def validate_response(value):
    need(type(value) is dict and set(value)=={'schema_version','paths'} and type(value['schema_version']) is int and value['schema_version']==1)
    need(type(value['paths']) is list and len(value['paths'])==2)
    need(all(type(p) is dict and 'source' in p and 'status' in p for p in value['paths']))
    need([p['source'] for p in value['paths']]==list(SOURCES))
    for path in value['paths']:
        if path['status']=='UNAVAILABLE':
            need(set(path)=={'source','status','reason'} and path['reason'] in REASONS);continue
        need(set(path)=={'source','status','transcript','tokens','confidence','geometric_mean','minimum','oracle_error','origins'})
        need(path['status']=='AVAILABLE' and type(path['transcript']) is str and 0<len(path['transcript'].encode())<=4096)
        need(type(path['tokens']) is int and 1<=path['tokens']<=128)
        for key in ['confidence','geometric_mean','minimum']:number(path[key]);need(path[key]>0)
        need(path['minimum']<=path['geometric_mean']+1e-12<=path['confidence']+2e-12)
        number(path['oracle_error'],0,1e-10)
        origins=path['origins'];need(type(origins) is dict and set(origins)=={'greedy','verification','redecode'})
        need(all(type(n) is int and 0<=n<=128 for n in origins.values()) and sum(origins.values())==path['tokens'])
        need(origins['redecode']<=1)
        if path['source']==SOURCES[0]:need(origins['greedy']==path['tokens'])
        else:need(origins['verification']>0 or origins['redecode']==1)
    return value['paths']


def score_response(case,value,seconds):
    """No reference is exposed to collector; text is dropped immediately after scoring."""
    number(seconds,0,1e6);rows=[]
    for path in validate_response(value):
        if path['status']=='UNAVAILABLE':rows.append(dict(source=path['source'],status='UNAVAILABLE',reason=path['reason']));continue
        counts=score_case(case,dict(transcript=path['transcript'],seconds=seconds))
        rows.append(dict(source=path['source'],status='AVAILABLE',tokens=path['tokens'],confidence=path['confidence'],
                         geometric_mean=path['geometric_mean'],minimum=path['minimum'],oracle_error=path['oracle_error'],origins=path['origins'],
                         exact_match=counts['word_errors']==0 and counts['character_errors']==0,
                         **{key:counts[key] for key in ['word_errors','reference_words','character_errors','reference_characters']}))
    return dict(case_id=case['id'],paths=rows)


def metrics(rows,total):
    need(type(total) is int and total>0 and 0<=len(rows)<=total)
    count=len(rows);correct=sum(row['exact_match'] for row in rows)
    bins=[]
    for i in range(10):
        selected=[row for row in rows if min(int(row['confidence']*10),9)==i];n=len(selected)
        bins.append(dict(lower=i/10,upper=(i+1)/10,upper_inclusive=i==9,count=n,
                         mean_confidence=math.fsum(row['confidence'] for row in selected)/n if n else None,
                         accuracy=sum(row['exact_match'] for row in selected)/n if n else None))
    curve=[]
    for i in range(101):
        accepted=[row for row in rows if row['confidence']>=i/100];n=len(accepted);errors=sum(not row['exact_match'] for row in accepted)
        curve.append(dict(threshold=i/100,accepted=n,errors=errors,coverage_all_cases=n/total,risk=errors/n if n else None))
    words=sum(row['reference_words'] for row in rows);chars=sum(row['reference_characters'] for row in rows)
    variation=len({row['exact_match'] for row in rows})
    positive=[row for row in rows if row['exact_match']];negative=[row for row in rows if not row['exact_match']]
    pairs=dict(higher=0,tied=0,lower=0)
    for a in positive:
        for b in negative:pairs['higher' if a['confidence']>b['confidence'] else 'tied' if a['confidence']==b['confidence'] else 'lower']+=1
    return dict(cases_total=total,available=count,unavailable=total-count,score_coverage=count/total,correct=correct,
                word_errors=sum(row['word_errors'] for row in rows),reference_words=words,character_errors=sum(row['character_errors'] for row in rows),reference_characters=chars,
                wer_available=sum(row['word_errors'] for row in rows)/words if words else None,
                cer_available=sum(row['character_errors'] for row in rows)/chars if chars else None,
                metrics_population='AVAILABLE_SCORES_ONLY',label_variation=variation,constant_signal=bool(count) and len({row['confidence'] for row in rows})==1,
                correctness_pairs=pairs,score_moments=dict(sum_probability=math.fsum(row['confidence'] for row in rows),sum_squared_probability=math.fsum(row['confidence']**2 for row in rows),sum_probability_correct=math.fsum(row['confidence'] for row in rows if row['exact_match'])),
                brier_score=math.fsum((row['confidence']-int(row['exact_match']))**2 for row in rows)/count if count else None,
                ece_10_bins=math.fsum(b['count']*abs(b['mean_confidence']-b['accuracy']) for b in bins if b['count'])/count if count else None,
                correctness_auroc=auc(rows),reliability_bins=bins,coverage_curve=curve,policy_0_85_diagnostic=curve[85])


def summarize(cases):
    need(type(cases) is list and 0<len(cases)<=30)
    need(len({row['case_id'] for row in cases})==len(cases))
    results=[]
    for index,source in enumerate(SOURCES):
        available=[];reasons=Counter();origin_cases=Counter()
        for case in cases:
            need(len(case['paths'])==2 and case['paths'][index]['source']==source)
            path=case['paths'][index]
            if path['status']=='UNAVAILABLE':need(path['reason'] in REASONS);reasons[path['reason']]+=1;continue
            need(path['status']=='AVAILABLE');available.append(path)
            for name,n in path['origins'].items():origin_cases[name]+=int(n>0)
        results.append(dict(source=source,status='NO_AVAILABLE_SCORES' if not available else 'INCOMPLETE_SCORES' if len(available)<len(cases) else 'DIAGNOSTIC_ONLY',scope='CURATOR_TEST_DIAGNOSTIC_ONLY',unavailable_reasons=dict(sorted(reasons.items())),origin_case_counts=dict(sorted(origin_cases.items())),metrics=metrics(available,len(cases))))
    return results
