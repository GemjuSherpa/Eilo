import copy
import unittest
from test_phase_report import synthetic as phase_synthetic
from resident_report import FIXED, VARIABLE, schedule, validate, summarize


def synthetic():
    base=phase_synthetic()
    report={**copy.deepcopy(FIXED),**{k:base[k] for k in VARIABLE-{'cases'}},'cases':[]}
    for index,(fixture,group,candidate,rep) in enumerate(schedule()):
        row=copy.deepcopy(base['cases'][0]);row.pop('round')
        row.update(fixture_id=fixture,group_index=group,candidate_index=candidate,repetition=rep,sample_index=index+1,
                   condition='MODEL_UNLOADED' if rep==0 else 'MODEL_WEIGHTS_RESIDENT',cooldown_before_sample_ms=0,
                   residency=dict(vendor_model_loads=1,generation_loads=rep+1,resident_models=1,live_handles=0,candidate_index=candidate))
        row['environment_before']['system_uptime_s']=index+1;row['environment_after']['system_uptime_s']=index+1.1
        if rep:row['native_phases']['model_load_ms']=0
        report['cases'].append(row)
    return report


class ResidentReportTests(unittest.TestCase):
    def test_complete_and_partial_preserve_real_counts(self):
        r=synthetic();validate(r);self.assertEqual(summarize(r)['sample_count'],36)
        self.assertEqual(len(summarize(r)['fixture_conditions']),24)
        for phase in ['RUNNING','CANCELLED','INFERENCE_FAILED','THERMAL_LIMIT']:
            q=copy.deepcopy(r);q['phase']=phase;q['cases']=q['cases'][:7];validate(q)

    def test_order_residency_and_generation_data_rejected(self):
        for key,value in [('candidate_index',1),('repetition',True),('group_index',2),('condition','WARM'),('answer','private')]:
            r=synthetic();r['cases'][0][key]=value
            with self.assertRaises(ValueError):validate(r)
        for key,value in [('vendor_model_loads',2),('resident_models',True),('live_handles',1),('generation_loads',2),('extra',1)]:
            r=synthetic();r['cases'][0]['residency'][key]=value
            with self.assertRaises(ValueError):validate(r)
        r=synthetic();r['cases'][1]['native_phases']['model_load_ms']=1
        with self.assertRaises(ValueError):validate(r)
        r=synthetic();r['cases'][1]['prompt_tokens']+=1
        with self.assertRaises(ValueError):validate(r)

    def test_types_content_provenance_and_thermal_policy(self):
        for key,value in [('physical_gate_acceptance','PASS'),('raw_text_exported',0),('answer','private'),('cold_start_scope','OS_CACHE_FLUSHED')]:
            r=synthetic();r[key]=value
            with self.assertRaises(ValueError):validate(r)
        r=synthetic();r['model_pins'][0]['candidate_index']=False
        with self.assertRaises(ValueError):validate(r)
        for index,value in [(0,2),(1,2)]:
            r=synthetic();r['cases'][index]['environment_before']['thermal_state']=value
            with self.assertRaises(ValueError):validate(r)
        r=synthetic();r['cases'][1]['cooldown_before_sample_ms']=-1
        with self.assertRaises(ValueError):validate(r)
        r=synthetic();r['cases'][0]['environment_before']['thermal_state']=1;validate(r)
        r['cases'][1]['cooldown_before_sample_ms']=5000;validate(r)
        r=synthetic();r['cases'].pop()
        with self.assertRaises(ValueError):validate(r)


if __name__=='__main__':unittest.main()
