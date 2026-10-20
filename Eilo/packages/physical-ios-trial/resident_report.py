"""Validate aggregate alternating resident-weight trials; full physical acceptance stays NOT_RUN."""
import argparse
import json
from pathlib import Path
import statistics
from phase_report import FIXED as PHASE_FIXED, KEYS, finite, validate as validate_phase
from model_diagnostic_report import require, integer
from resident_wrapper import CANDIDATES

MODEL_PINS=[dict(candidate_index=i,model_sha256=digest,model_bytes=size) for i,(_,size,digest) in enumerate(CANDIDATES)]
FIXED={**PHASE_FIXED,'scope':'IOS_RESIDENT_MODEL_COMPARISON','model_pins':MODEL_PINS,
       'model_open':'EXPLICIT_SCOPED_MODEL_WEIGHTS_RESIDENCY_THREE_FRESH_GENERATIONS',
       'cold_start_scope':'MODEL_UNLOADED_AT_GROUP_START_OS_CACHES_UNCONTROLLED_PROCESS_REUSED',
       'warm_scope':'GENERIC_MODEL_WEIGHTS_ONLY_FRESH_CONTEXT_KV_SAMPLER_EACH_GENERATION',
       'candidate_order':'1P7_THEN_0P6_ODD_FIXTURES_REVERSED_EVEN_FIXTURES',
       'thermal_policy':'WAIT_FOR_NOMINAL_GROUP_START_MAX_300S_REFUSE_SERIOUS_SAMPLE_START'}
for key in ['cold_cache','resident_model_warm']:del FIXED[key]
VARIABLE={'phase','process_id','os_build','physical_memory_bytes','updated_utc','cases'}
COMMON={'prompt_tokens','native_piece_count','output_bytes','verified_open_and_load_ms','sample_wall_ms','native_phases','environment_before','environment_after','memory'}
ROW=COMMON|{'fixture_id','group_index','candidate_index','repetition','sample_index','condition','cooldown_before_group_ms','residency'}


def schedule():
    return [(f'compare-{fixture:02d}',(fixture-1)*2+offset+1,candidate,rep)
            for fixture in range(1,7) for offset,candidate in enumerate([0,1] if fixture%2 else [1,0]) for rep in range(3)]


def exact(value,expected):
    return type(value) is type(expected) and json.dumps(value,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False)


def validate(report):
    require(type(report) is dict and set(report)==set(FIXED)|VARIABLE,'report fields')
    for key,value in FIXED.items():require(exact(report[key],value),'fixed field: '+key)
    require(report['phase'] in ('RUNNING','COMPLETED','CANCELLED','INFERENCE_FAILED','THERMAL_LIMIT'),'phase')
    rows=report['cases'];require(type(rows) is list and len(rows)<=36,'sample count')
    require(report['phase']!='COMPLETED' or len(rows)==36,'complete sample count')
    metadata={k:report[k] for k in VARIABLE-{'phase','cases'}}
    validate_phase({**PHASE_FIXED,**metadata,**{k:MODEL_PINS[0][k] for k in ['model_sha256','model_bytes']},'phase':'RUNNING','cases':[]})
    peak=0;previous=0;counts={}
    for index,(row,expected) in enumerate(zip(rows,schedule())):
        require(type(row) is dict and set(row)==ROW,'row fields')
        fixture,group,candidate,rep=expected
        require(row['fixture_id']==fixture and all(integer(row[k],0,36) and row[k]==v for k,v in [('group_index',group),('candidate_index',candidate),('repetition',rep),('sample_index',index+1)]),'alternating group/repetition order')
        require(row['condition']==('MODEL_UNLOADED' if rep==0 else 'MODEL_WEIGHTS_RESIDENT'),'condition')
        stats=dict(vendor_model_loads=1,generation_loads=rep+1,resident_models=1,live_handles=0,candidate_index=candidate)
        require(exact(row['residency'],stats),'native residency counters')
        require(finite(row['cooldown_before_group_ms'],0,305000) and (rep==0 or row['cooldown_before_group_ms']==0),'cooldown')
        # Reuse strict common numeric/OS/pin validation, then enforce the real
        # resident schedule and cross-sample constraints here. No report is promoted.
        common={k:row[k] for k in COMMON}
        common.update(fixture_id='compare-01',round=1,sample_index=1)
        validate_phase({**PHASE_FIXED,**metadata,**{k:MODEL_PINS[candidate][k] for k in ['model_sha256','model_bytes']},'phase':'RUNNING','cases':[common]})
        require((row['native_phases']['model_load_ms']>0) if rep==0 else row['native_phases']['model_load_ms']==0,'actual cold load / warm no-load')
        before,after=row['environment_before'],row['environment_after']
        require(before['thermal_state']==0 if rep==0 else before['thermal_state']<2,'thermal start policy')
        require(before['system_uptime_s']>=previous,'sample time order');previous=after['system_uptime_s']
        require(row['memory']['process_lifetime_peak_bytes']>=peak,'process peak monotonicity');peak=row['memory']['process_lifetime_peak_bytes']
        key=(fixture,candidate)
        require(key not in counts or counts[key]==row['prompt_tokens'],'same frozen prompt budget across warm runs');counts[key]=row['prompt_tokens']
    return report


def summarize(report):
    validate(report);rows=report['cases']
    return dict(scope=FIXED['scope'],phase=report['phase'],sample_count=len(rows),physical_gate_acceptance='NOT_RUN',
                cold_start_scope=FIXED['cold_start_scope'],warm_scope=FIXED['warm_scope'],
                fixture_conditions=[dict(fixture_id=f'compare-{fixture:02d}',candidate_index=candidate,condition=condition,sample_count=len(selected),
                    native_phases_ms={k:statistics.median(r['native_phases'][k] for r in selected) for k in KEYS})
                    for fixture in range(1,7) for candidate in [0,1] for condition in ['MODEL_UNLOADED','MODEL_WEIGHTS_RESIDENT']
                    if (selected:=[r for r in rows if r['fixture_id']==f'compare-{fixture:02d}' and r['candidate_index']==candidate and r['condition']==condition])])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('report',type=Path);args=parser.parse_args()
    print(json.dumps(summarize(json.loads(args.report.read_text())),sort_keys=True))
