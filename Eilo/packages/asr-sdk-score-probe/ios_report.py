"""Isolated iOS source score evidence; coverage gaps never count as passed paths."""
import argparse
from collections import Counter
import html
import json
import math
from pathlib import Path
import re
from check_ios import HERE,PACKAGES,FLAGS,f,pins


def need(value):
    if not value:raise ValueError('invalid isolated iOS score evidence')


def closed(value,keys):need(type(value) is dict and set(value)==set(keys.split()))


def digest(value):need(type(value) is str and re.fullmatch('[0-9a-f]{64}',value))


def number(value,low=0,high=1):need(type(value) in (int,float) and math.isfinite(value) and low<=value<=high)


def case_summary(cases):
    fixtures=f.read(PACKAGES/'asr-runtime/tests/fixtures.json')['cases']
    need(type(cases) is list and [c['case'] for c in cases]==[c['id'] for c in fixtures])
    usable=unavailable=faults=biased=missing=0;coverage=Counter();step_delta=prefix_delta=oracle=0
    modes=['greedy','accepted_draft','accepted_prefix','early_divergence','late_divergence','biased']
    for case in cases:
        need(set(case)=={'case','paths','shape_comparison','faults'})
        need(type(case['paths']) is list and [p['mode'] for p in case['paths']]==modes)
        for path in case['paths']:
            if path['status']=='NOT_EXERCISED':
                closed(path,'mode status reported_scores reason expected_verification_rows observed_verification_rows observed_redecoded observed_output_tokens')
                need(path['mode']=='accepted_draft' and path['reason']=='FIXTURE_DID_NOT_EXERCISE_FULL_ACCEPTED_DRAFT')
                need(type(path['reported_scores']) is int and path['reported_scores']==0)
                for k in ('expected_verification_rows','observed_verification_rows','observed_redecoded','observed_output_tokens'):
                    need(type(path[k]) is int and 0<=path[k]<128)
                need(path['expected_verification_rows']>0 and path['observed_output_tokens']>0 and path['observed_verification_rows']<=path['observed_output_tokens'])
                need(path['observed_verification_rows']!=path['expected_verification_rows'] or path['observed_redecoded']>0)
                missing+=1;continue
            if path['status']=='UNAVAILABLE':
                need(set(path)=={'mode','status','usable_partial_scores','reason'} and path['mode']=='biased')
                need(type(path['usable_partial_scores']) is int and path['usable_partial_scores']==0 and path['reason']=='NO_EOS_OR_OUTPUT_CAP')
                unavailable+=1;continue
            need(set(path)=={'mode','status','tokens','verification_row_scores','redecoded','mean_probability','minimum','oracle_max_error','baseline_tokens_equal','biased_choices'})
            need(path['status']=='DIAGNOSTIC_ONLY' and path['baseline_tokens_equal'] is True)
            for key in ['tokens','verification_row_scores','redecoded','biased_choices']:need(type(path[key]) is int and 0<=path[key]<128)
            need(path['tokens']>0 and path['verification_row_scores']<=path['tokens'])
            for key in ['mean_probability','minimum']:number(path[key]);need(path[key]>0)
            need(path['minimum']<=path['mean_probability']+1e-8)
            number(path['oracle_max_error'],0,1e-10);oracle=max(oracle,path['oracle_max_error'])
            mode=path['mode']
            if mode=='accepted_draft':need(path['verification_row_scores']==path['tokens'] and path['redecoded']==0)
            elif mode=='accepted_prefix':need(1<path['verification_row_scores']<=path['tokens'] and path['redecoded']==0)
            elif mode=='late_divergence':need(0<path['verification_row_scores']<path['tokens'] and path['redecoded']==1)
            elif mode=='early_divergence':need(path['verification_row_scores']==0 and path['redecoded']==1)
            else:need(path['verification_row_scores']==0 and path['redecoded']==0)
            if mode=='biased':need(path['biased_choices']>0);biased+=1
            else:need(path['biased_choices']==0)
            usable+=1;coverage[mode]+=1
        shape=case['shape_comparison']
        need(set(shape)=={'same_shape_repeat_delta','prefix_repeat_delta','batch_vs_step_delta','full_vs_prefix_delta','cause'})
        need(shape['cause']=='NOT_ESTABLISHED')
        for key in ['same_shape_repeat_delta','prefix_repeat_delta']:number(shape[key],0,1e-10)
        for key in ['batch_vs_step_delta','full_vs_prefix_delta']:number(shape[key])
        step_delta=max(step_delta,shape['batch_vs_step_delta']);prefix_delta=max(prefix_delta,shape['full_vs_prefix_delta'])
        bad=case['faults'];need(set(bad)=={'fault_cases_unavailable','usable_partial_scores','calibrated','policy_authorized'})
        need(type(bad['fault_cases_unavailable']) is int and bad['fault_cases_unavailable']==9)
        need(type(bad['usable_partial_scores']) is int and bad['usable_partial_scores']==0 and bad['calibrated'] is False and bad['policy_authorized'] is False)
        faults+=bad['fault_cases_unavailable']
    need(biased>0)
    need(all(coverage[m]>0 for m in modes))
    return dict(fixtures=len(cases),diagnostic_paths=usable,unavailable_paths=unavailable,not_exercised_paths=missing,
        path_coverage=dict(coverage),fault_cases_unavailable=faults,max_formula_error=oracle,batch_vs_step_delta=step_delta,
        full_vs_prefix_delta=prefix_delta,coverage='GAPS_RETAINED' if missing else 'ALL_PLANNED_PATHS_EXERCISED')


def validate(r):
    closed(r,'schema_version purpose platform source_commit source_pins overlay_pins ort_version ort_origin ort_archive_sha256 ort_binary_sha256 binary_sha256 relocation custom_dynamic_dependencies rpaths rejected_inputs cases numeric '+' '.join(FLAGS))
    need(type(r['schema_version']) is int and r['schema_version']==1 and r['purpose']=='IOS_SOURCE_SDK_SCORE_DIAGNOSTIC_ONLY')
    need(r['platform']=='ARM64_IOS_SIMULATOR_18_MINIMUM' and r['source_pins']==pins())
    for k,v in FLAGS.items():need(r[k] is v if type(v) is bool else r[k]==v)
    need(r['source_commit']==f.read(PACKAGES/'asr-confidence-probe/source-manifest.json')['commit'])
    need(r['overlay_pins']==f.read(HERE/'overlay-expected.json'))
    need(r['ort_origin']=='vendor-prelinked' and r['ort_version']=='1.23.2')
    need(r['ort_archive_sha256']==f.read(PACKAGES/'asr-runtime/provenance.json')['ios']['publisher_sha256'])
    for k in ('ort_binary_sha256','binary_sha256'):digest(r[k])
    need(r['relocation']=='EXECUTED_WITH_ORIGINAL_BINARY_ABSENT' and r['custom_dynamic_dependencies']=='NONE' and r['rpaths']==[])
    need(r['rejected_inputs']==['empty','unaligned','nan','out_of_range'])
    n=r['numeric'];closed(n,'double_mantissa_bits long_double_mantissa_bits')
    need(type(n['double_mantissa_bits']) is int and type(n['long_double_mantissa_bits']) is int and n['double_mantissa_bits']==n['long_double_mantissa_bits']==53)
    result=case_summary(r['cases'])
    from ios_math import validate as validate_math
    math_controls=validate_math(f.read(HERE/'ios-math-results.json'))
    return dict(purpose=r['purpose'],ort_version=r['ort_version'],ort_origin=r['ort_origin'],numeric=n,
        formula_oracle='SAME_PRECISION_FORMULA_CHECK_NOT_EXTENDED_PRECISION',independent_math_controls=math_controls,initial_fixture_failure='RETAINED',
        calibration='NOT_ESTABLISHED',threshold='NOT_GRANTED',**result,**FLAGS)


def export(r,out):
    result=validate(r);need(not out.exists());out.mkdir(parents=True)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'summary.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Isolated iOS score diagnostic</title><h1>Isolated iOS score diagnostic</h1><p>Actual-row checks and deliberate fault cases; absent fixture branches remain NOT_EXERCISED. Darwin long double has the same precision as double here. No extended-precision, calibrated confidence, ordinary-runtime, physical or release acceptance.</p><pre>'+html.escape(json.dumps(result,indent=2))+'</pre></html>\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,default=HERE/'ios-results.json');p.add_argument('--output',type=Path)
    a=p.parse_args();r=f.read(a.report);print(json.dumps(export(r,a.output) if a.output else validate(r),indent=2))
