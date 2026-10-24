"""Validate isolated SDK-path evidence; never authorize calibrated/production confidence."""
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
PINS=['main.cpp','score_trace.h','overlay.py','CMakeLists.txt','check_android.py','overlay-expected.json']


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(r):
    def need(value):
        if not value:raise ValueError('invalid or stale SDK-path diagnostic')
    def number(value,low=0,high=1):need(type(value) in [int,float] and math.isfinite(value) and low<=value<=high)
    need(type(r) is dict and set(r)=={'version','status','platform','calibrated','policy_authorized','physical','source_commit','source_pins','overlay_pins','upstream_inventory_sha256','binary_sha256','ort_sha256','cxx_sha256','model_provenance_sha256','fixtures_sha256','rejected_inputs','cases'})
    need(type(r['version']) is int and r['version']==1 and r['status']=='SDK_PATH_DIAGNOSTIC_ONLY')
    need(r['calibrated'] is False and r['policy_authorized'] is False and r['physical']=='NOT_RUN')
    need(r['platform']=='Android API35 ARM64 emulator')
    inventory=HERE.parent/'asr-confidence-probe/source-manifest.json'
    need(r['source_commit']==json.loads(inventory.read_text())['commit'] and r['upstream_inventory_sha256']==digest(inventory))
    need(type(r['source_pins']) is dict and set(r['source_pins'])==set(PINS))
    for name in PINS:need(r['source_pins'][name]==digest(HERE/name))
    need(r['overlay_pins']==json.loads((HERE/'overlay-expected.json').read_text()))
    for key in ['binary_sha256','ort_sha256','cxx_sha256']:
        value=r[key];need(type(value) is str and len(value)==64 and all(x in '0123456789abcdef' for x in value))
    need(r['ort_sha256']=='86e85022fc539963177e478c8e9a8a8219bc3b0d7515bf5297a62986dbc45e7a')
    need(r['model_provenance_sha256']==digest(HERE.parent/'asr-runtime/provenance.json'))
    fixtures=HERE.parent/'asr-runtime/tests/fixtures.json';need(r['fixtures_sha256']==digest(fixtures))
    need(r['rejected_inputs']==['empty','unaligned','nan','out_of_range'])
    need(type(r['cases']) is list and [c['case'] for c in r['cases']]==[c['id'] for c in json.loads(fixtures.read_text())['cases']])
    usable=unavailable=faults=biased=0;step_delta=prefix_delta=oracle=0
    modes=['greedy','accepted_draft','early_divergence','late_divergence','biased']
    for case in r['cases']:
        need(set(case)=={'case','paths','shape_comparison','faults'})
        need(type(case['paths']) is list and [p['mode'] for p in case['paths']]==modes)
        for path in case['paths']:
            if path['status']=='UNAVAILABLE':
                need(set(path)=={'mode','status','usable_partial_scores','reason'} and path['mode']=='biased')
                need(type(path['usable_partial_scores']) is int and path['usable_partial_scores']==0 and path['reason']=='NO_EOS_OR_OUTPUT_CAP')
                unavailable+=1;continue
            need(set(path)=={'mode','status','tokens','accepted_draft','redecoded','mean_probability','minimum','oracle_max_error','baseline_tokens_equal','biased_choices'})
            need(path['status']=='DIAGNOSTIC_ONLY' and path['baseline_tokens_equal'] is True)
            for key in ['tokens','accepted_draft','redecoded','biased_choices']:need(type(path[key]) is int and 0<=path[key]<128)
            need(path['tokens']>0 and path['accepted_draft']<=path['tokens'])
            for key in ['mean_probability','minimum']:number(path[key]);need(path[key]>0)
            need(path['minimum']<=path['mean_probability']+1e-8)
            number(path['oracle_max_error'],0,1e-10);oracle=max(oracle,path['oracle_max_error'])
            mode=path['mode']
            if mode=='accepted_draft':need(path['accepted_draft']==path['tokens'] and path['redecoded']==0)
            elif mode=='late_divergence':need(0<path['accepted_draft']<path['tokens'] and path['redecoded']==1)
            elif mode=='early_divergence':need(path['accepted_draft']==0 and path['redecoded']==1)
            else:need(path['accepted_draft']==0 and path['redecoded']==0)
            if mode=='biased':need(path['biased_choices']>0);biased+=1
            else:need(path['biased_choices']==0)
            usable+=1
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
    return dict(status='SDK_PATH_DIAGNOSTIC_ONLY',fixtures=len(r['cases']),usable_paths=usable,unavailable_paths=unavailable,
                fault_cases_unavailable=faults,max_oracle_error=oracle,batch_vs_step_delta=step_delta,full_vs_prefix_delta=prefix_delta,
                calibrated=False,policy_authorized=False,physical='NOT_RUN')


if __name__=='__main__':print(json.dumps(validate(json.loads((HERE/'android-results.json').read_text())),indent=2))
