#!/usr/bin/env python3
"""Frozen word-error measurement of synthetic references, with visible failures/slice counts."""
import json
import re
from check_host import HERE

def words(text):
    # Frozen normalization: lowercase ASCII words/digits, ignore punctuation. Do not expand
    # numbers or repair names after looking at hypotheses. WER can exceed1 from insertions.
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?",text.lower())

def edits(reference,hypothesis):
    a,b=words(reference),words(hypothesis)
    if not a:raise ValueError('empty reference cannot define WER')
    row=[(j,0,0,j) for j in range(len(b)+1)]
    for i,x in enumerate(a,1):
        new=[(i,0,i,0)]
        for j,y in enumerate(b,1):
            if x==y:new.append(row[j-1]);continue
            c,s,d,n=row[j-1];sub=(c+1,s+1,d,n)
            c,s,d,n=row[j];delete=(c+1,s,d+1,n)
            c,s,d,n=new[j-1];insert=(c+1,s,d,n+1)
            new.append(min([sub,delete,insert],key=lambda z:z[0]))
        row=new
    errors,s,d,i=row[-1]
    return {'reference_words':len(a),'substitutions':s,'deletions':d,'insertions':i,'errors':errors,'wer':errors/len(a)}

def summarize(report,manifest):
    cases=report['cases'];expected=manifest['cases']
    if len(cases)!=len(expected):raise ValueError('missing ASR cases')
    values=[];slices={}
    for actual,fixture in zip(cases,expected):
        if actual['id']!=fixture['id'] or actual['reference']!=fixture['reference'] or actual['slice']!=fixture['slice'] or not isinstance(actual['transcript'],str) or len(actual['transcript'].encode())>4096:raise ValueError('mismatched ASR case')
        value=edits(actual['reference'],actual['transcript'])
        values.append({'id':fixture['id'],'slice':fixture['slice'],**value,'exact_normalized_match':value['errors']==0})
        group=slices.setdefault(fixture['slice'],{'cases':0,'reference_words':0,'errors':0})
        group['cases']+=1;group['reference_words']+=value['reference_words'];group['errors']+=value['errors']
    for group in slices.values():group['wer']=group['errors']/group['reference_words'] if group['reference_words'] else None
    total=sum(v['reference_words'] for v in values);errors=sum(v['errors'] for v in values)
    return {'platform':report['platform'],'case_count':len(values),'reference_words':total,'errors':errors,'wer':errors/total if total else None,
        'cases':values,'slices':slices,'failed_exact_match_cases':[v['id'] for v in values if not v['exact_normalized_match']],
        'accent_diversity':'NOT RUN; one installed US-English synthetic voice','physical_quality':'NOT RUN','quality_release_gate':'NOT ESTABLISHED'}

def main():
    manifest=json.loads((HERE/'tests/fixtures.json').read_text())
    platforms=[summarize(json.loads((HERE/'tests'/f'{name}-results.json').read_text()),manifest) for name in ['host','android','ios']]
    report={'normalization':'lowercase ASCII words/digits; punctuation ignored; no number/name rewriting','kind':'frozen synthetic file evaluation','platforms':platforms}
    (HERE/'tests/quality-results.json').write_text(json.dumps(report,indent=2)+'\n')
    for item in platforms:print(item['platform'],str(item['errors'])+'/'+str(item['reference_words']),str(round(item['wer']*100,2))+'% WER','nonexact cases:'+','.join(item['failed_exact_match_cases']))

if __name__=='__main__':main()
