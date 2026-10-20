"""Closed aggregate-only repeated reload measurements; never accepts the full comparison gate."""
import argparse
import json
import math
from pathlib import Path
import statistics
from model_diagnostic_report import FIXED as CPU_FIXED, integer, require, validate as validate_cpu
from phase_wrapper import KEYS

FIXED = {**CPU_FIXED, 'scope':'IOS_NATIVE_PHASE_RELOAD_DIAGNOSTIC',
         'model_open':'FRESH_HANDLE_EVERY_SAMPLE_THREE_ROUNDS_OS_CACHES_UNCONTROLLED',
         'cold_cache':'NOT_ESTABLISHED', 'resident_model_warm':'NOT_RUN',
         'timing_clock':'std::chrono::steady_clock',
         'battery_scope':'OS_LEVEL_BEFORE_AFTER_USB_CONNECTED_NOT_ENERGY_MEASUREMENT'}
del FIXED['timing_scope']
VARIABLE = {'phase','process_id','model_sha256','model_bytes','os_build','physical_memory_bytes','updated_utc','cases'}
ROW = {'fixture_id','round','sample_index','prompt_tokens','native_piece_count','output_bytes',
       'verified_open_and_load_ms','sample_wall_ms','native_phases','environment_before','environment_after','memory'}


def finite(value, low, high):
    return type(value) in (int,float) and math.isfinite(value) and low <= value <= high


def validate(report):
    require(type(report) is dict and set(report)==set(FIXED)|VARIABLE, 'report fields')
    for key,value in FIXED.items():
        require(type(report[key]) is type(value) and report[key]==value,'fixed field: '+key)
    # Reuse closed pinned model/OS/session/date/RAM validation without promoting any metrics.
    base = {**CPU_FIXED, **{k:report[k] for k in VARIABLE}, 'phase':'RUNNING', 'cases':[]}
    validate_cpu(base)
    require(report['phase'] in ('RUNNING','COMPLETED','CANCELLED','INFERENCE_FAILED'),'phase')
    rows=report['cases'];require(type(rows) is list and len(rows)<=18,'case count')
    require(report['phase']!='COMPLETED' or len(rows)==18,'complete count')
    peak=0;previous=0
    for index,row in enumerate(rows):
        require(type(row) is dict and set(row)==ROW,'row fields')
        require(row['fixture_id']==f'compare-{index%6+1:02d}' and integer(row['round'],1,3) and row['round']==index//6+1 and integer(row['sample_index'],1,18) and row['sample_index']==index+1,'sample order')
        require(integer(row['prompt_tokens'],1,3840) and integer(row['native_piece_count'],1,256),'tokens')
        require(integer(row['output_bytes'],row['native_piece_count'],row['native_piece_count']*1024),'bytes')
        require(finite(row['verified_open_and_load_ms'],0.000001,1800000) and finite(row['sample_wall_ms'],0.000001,1800000),'wall timing')
        phases=row['native_phases'];require(type(phases) is dict and set(phases)==set(KEYS),'native phase fields')
        require(all(finite(v,0,1800000) for v in phases.values()),'native timings')
        require(phases['begin_to_first_token_ms']+1e-6>=sum(phases[k] for k in KEYS[1:5]),'phase sum/order')
        require(phases['begin_to_first_piece_ms']>=phases['begin_to_first_token_ms'],'piece order')
        require(row['verified_open_and_load_ms']+1e-6>=phases['model_load_ms'] and row['sample_wall_ms']+1e-6>=row['verified_open_and_load_ms']+phases['begin_to_first_piece_ms'],'sample timing order')
        for key in ('environment_before','environment_after'):
            env=row[key]
            require(type(env) is dict and set(env)=={'battery_level','battery_state','thermal_state','low_power_mode','system_uptime_s'},'environment fields')
            require(env['battery_level'] is None or finite(env['battery_level'],0,1),'battery level')
            require(integer(env['battery_state'],0,3) and integer(env['thermal_state'],0,3) and type(env['low_power_mode']) is bool,'environment state')
            require(finite(env['system_uptime_s'],0,1e10) and env['system_uptime_s']>=previous,'environment time order')
            previous=env['system_uptime_s']
        require((row['environment_after']['system_uptime_s']-row['environment_before']['system_uptime_s'])*1000+1>=row['sample_wall_ms'],'environment/sample timing')
        memory=row['memory'];require(type(memory) is dict and set(memory)=={'current_phys_footprint_bytes','process_lifetime_peak_bytes'},'memory fields')
        current,high=memory['current_phys_footprint_bytes'],memory['process_lifetime_peak_bytes']
        require(integer(current,1,report['physical_memory_bytes']) and integer(high,current,report['physical_memory_bytes']) and high>=peak,'memory peak')
        peak=high
    return report


def validate_pair(reports):
    require(type(reports) is list and len(reports)==2,'two reports')
    for report in reports:
        validate(report);require(report['phase']=='COMPLETED','both complete')
    require(reports[0]['model_sha256']!=reports[1]['model_sha256'] and reports[0]['process_id']!=reports[1]['process_id'],'distinct pinned candidates/processes')
    require(all(reports[0][k]==reports[1][k] for k in ('os_build','physical_memory_bytes')),'device metadata differs')
    return reports


def summarize(report):
    validate(report)
    rows=report['cases']
    return dict(scope=FIXED['scope'], model_sha256=report['model_sha256'], phase=report['phase'], sample_count=len(rows),
                cold_cache='NOT_ESTABLISHED',resident_model_warm='NOT_RUN',physical_gate_acceptance='NOT_RUN',
                fixture_medians=[dict(fixture_id=f'compare-{i:02d}',sample_count=len(selected),
                                     phases_ms={k:statistics.median(r['native_phases'][k] for r in selected) for k in KEYS})
                                 for i in range(1,7) if (selected:=[r for r in rows if r['fixture_id']==f'compare-{i:02d}'])])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path);parser.add_argument('--pair',action='store_true');args=parser.parse_args()
    data=json.loads(args.report.read_text())
    (validate_pair if args.pair else validate)(data)
    print(json.dumps([summarize(r) for r in data] if args.pair else summarize(data),sort_keys=True))
