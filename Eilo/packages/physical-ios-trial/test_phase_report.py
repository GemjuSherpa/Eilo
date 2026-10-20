import copy
import json
from pathlib import Path
import unittest
from phase_report import FIXED, KEYS, validate, validate_pair, summarize


def synthetic():
    # Explicitly synthetic unit fixture, never physical evidence.
    base=json.loads(Path(__file__).with_name('tests').joinpath('cpu-model-device-results.json').read_text())[0]
    r={**FIXED,**{k:base[k] for k in ('process_id','model_sha256','model_bytes','os_build','physical_memory_bytes','updated_utc')},'phase':'COMPLETED','cases':[]}
    for index in range(18):
        env=dict(battery_level=0.8,battery_state=2,thermal_state=0,low_power_mode=False,system_uptime_s=index+1)
        r['cases'].append(dict(fixture_id=f'compare-{index%6+1:02d}',round=index//6+1,sample_index=index+1,prompt_tokens=300,
                              native_piece_count=3,output_bytes=6,verified_open_and_load_ms=10,sample_wall_ms=50,
                              native_phases=dict(zip(KEYS,[5,1,1,10,1,14,16])),environment_before=env,
                              environment_after={**env,'system_uptime_s':index+1.1},
                              memory=dict(current_phys_footprint_bytes=100,process_lifetime_peak_bytes=200)))
    return r


class PhaseReportTests(unittest.TestCase):
    def test_completed_and_partial_failure_with_unknown_battery(self):
        r=synthetic();validate(r);self.assertEqual(summarize(r)['sample_count'],18)
        self.assertTrue(all(f['sample_count']==3 for f in summarize(r)['fixture_medians']))
        for phase in ('RUNNING','CANCELLED','INFERENCE_FAILED'):
            q=copy.deepcopy(r);q['phase']=phase;q['cases']=q['cases'][:4];q['cases'][0]['environment_before']['battery_level']=None
            validate(q)

    def test_content_scope_pins_order_counts_and_types_rejected(self):
        for key,value in [('cold_cache','PASS'),('resident_model_warm','PASS'),('model_sha256','0'*64),('raw_text_exported',0),('answer','private'),('physical_gate_acceptance','PASS')]:
            r=synthetic();r[key]=value
            with self.assertRaises(ValueError):validate(r)
        for key,value in [('round',True),('sample_index',2),('fixture_id','compare-06'),('output_bytes',0),('sample_wall_ms',float('nan')),('answer','private')]:
            r=synthetic();r['cases'][0][key]=value
            with self.assertRaises(ValueError):validate(r)
        r=synthetic();r['cases'].pop()
        with self.assertRaises(ValueError):validate(r)

    def test_native_boundaries_and_environment_consistency(self):
        for key,value in [('prefill_ms',100),('first_sample_ms',True),('begin_to_first_piece_ms',1),('model_load_ms',11),('extra',1)]:
            r=synthetic();r['cases'][0]['native_phases'][key]=value
            with self.assertRaises(ValueError):validate(r)
        for key,value in [('battery_level',2),('battery_state',True),('thermal_state',4),('low_power_mode',1),('system_uptime_s',0)]:
            r=synthetic();r['cases'][0]['environment_after'][key]=value
            with self.assertRaises(ValueError):validate(r)
        r=synthetic();r['cases'][1]['memory']['process_lifetime_peak_bytes']=100
        with self.assertRaises(ValueError):validate(r)

    def test_pair_requires_both_pinned_models_and_distinct_sessions(self):
        r=synthetic();q=copy.deepcopy(r)
        with self.assertRaises(ValueError):validate_pair([r,q])
        pins=json.loads(Path(__file__).with_name('tests').joinpath('model-comparison-pins.json').read_text())
        other=next(p for p in pins if p['sha256']!=r['model_sha256'])
        q.update(model_sha256=other['sha256'],model_bytes=other['bytes'],process_id='00000000-0000-0000-0000-000000000001')
        validate_pair([r,q]);q['phase']='RUNNING'
        with self.assertRaises(ValueError):validate_pair([r,q])


if __name__=='__main__':unittest.main()
