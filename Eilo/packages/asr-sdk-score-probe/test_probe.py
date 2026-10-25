import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import report
from overlay import once,generate

HERE=Path(__file__).resolve().parent

class SDKScoreTests(unittest.TestCase):
    def setUp(self):self.data=json.loads((HERE/'android-results.json').read_text())
    def test_actual_native_paths(self):
        result=report.validate(self.data);self.assertEqual(result['fixtures'],6);self.assertEqual(result['fault_cases_unavailable'],54)
    def test_cannot_promote_diagnostics(self):
        for key,value in [('physical','PASS'),('calibrated',True),('policy_authorized',True),('transcript','forbidden')]:
            r=copy.deepcopy(self.data);r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):report.validate(r)
    def test_stale_overlay_source_model_fixtures_rejected(self):
        for key in ['binary_sha256','ort_sha256','model_provenance_sha256','fixtures_sha256','upstream_inventory_sha256']:
            r=copy.deepcopy(self.data);r[key]='broken'
            with self.subTest(key=key),self.assertRaises(ValueError):report.validate(r)
        r=copy.deepcopy(self.data);r['source_pins']['overlay.py']='0'*64
        with self.assertRaises(ValueError):report.validate(r)
        r=copy.deepcopy(self.data);r['overlay_pins']['moonshine-streaming-model.cpp']='0'*64
        with self.assertRaises(ValueError):report.validate(r)
    def test_missing_duplicate_and_reordered_paths_rejected(self):
        for change in [lambda r:r['cases'].pop(),lambda r:r['cases'].reverse(),lambda r:r['cases'][0]['paths'].pop(),lambda r:r['cases'][0]['paths'].append(r['cases'][0]['paths'][0])]:
            r=copy.deepcopy(self.data);change(r)
            with self.assertRaises(ValueError):report.validate(r)
    def test_alignment_and_rejected_draft_claims_checked(self):
        for key,value in [('baseline_tokens_equal',False),('verification_row_scores',1),('redecoded',0),('tokens',True),('token_ids',[])]:
            r=copy.deepcopy(self.data);r['cases'][0]['paths'][3][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):report.validate(r)
    def test_accepted_prefix_requires_start_token_verification_score(self):
        r=copy.deepcopy(self.data);path=r['cases'][0]['paths'][2]
        self.assertEqual(path['mode'],'accepted_prefix')
        path['verification_row_scores']=1
        with self.assertRaises(ValueError):report.validate(r)

    def test_invalid_probability_and_oracle_errors(self):
        for value in [float('nan'),float('inf'),-0.01,1.1,True,'0.9']:
            r=copy.deepcopy(self.data);r['cases'][0]['paths'][0]['mean_probability']=value
            with self.subTest(value=value),self.assertRaises(ValueError):report.validate(r)
        r=copy.deepcopy(self.data);r['cases'][0]['paths'][0]['oracle_max_error']=1e-3
        with self.assertRaises(ValueError):report.validate(r)
    def test_fault_or_shape_failures_cannot_produce_usable_scores(self):
        for change in [lambda r:r['cases'][0]['faults'].update(usable_partial_scores=1),lambda r:r['cases'][0]['faults'].update(fault_cases_unavailable=8),lambda r:r['cases'][0]['shape_comparison'].update(same_shape_repeat_delta=0.01),lambda r:r['cases'][0]['shape_comparison'].update(cause='PROVEN')]:
            r=copy.deepcopy(self.data);change(r)
            with self.assertRaises(ValueError):report.validate(r)
    def test_unverified_source_and_nonunique_anchors_rejected(self):
        for value in ['', 'anchor anchor']:
            with self.assertRaises(ValueError):once(value,'anchor','replacement')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);output=root/'overlay'
            with self.assertRaises(ValueError):generate(root/'missing',output)
            self.assertFalse(output.exists())
    def test_native_prebias_oracle_bounds_and_partial_discard(self):
        code=r'''
#include "score_trace.h"
#include <cassert>
int main(){
 EiloScoreTrace trace;trace.begin();
 std::vector<float> raw{1000,1000},biased=raw;biased[1]+=10;
 int chosen=int(std::max_element(biased.begin(),biased.end())-biased.begin());
 auto score=trace.measure(raw,chosen,EiloScoreTrace::DRAFT);assert(chosen==1 && score.probability==0.5);
 {EiloScoreTrace::Guard guard{&trace};trace.accept(chosen,score,8,9,2);}assert(trace.tokens.empty() && trace.scores.empty() && !trace.available);
 trace.begin();bool rejected=false;try{trace.measure({NAN},0,EiloScoreTrace::GREEDY);}catch(...){rejected=true;}assert(rejected);
 rejected=false;try{trace.measure(raw,2,EiloScoreTrace::GREEDY);}catch(...){rejected=true;}assert(rejected);
 rejected=false;try{trace.accept(8,score,8,9,2);}catch(...){rejected=true;}assert(rejected);
 trace.accept(1,score,8,9,1);rejected=false;try{trace.accept(2,score,8,9,1);}catch(...){rejected=true;}assert(rejected);
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);source=folder/'test.cpp';source.write_text(code)
            subprocess.run(['c++','-std=c++20','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(HERE),str(source),'-o',str(folder/'test')],check=True,capture_output=True)
            subprocess.run([str(folder/'test')],check=True,capture_output=True)

if __name__=='__main__':unittest.main()
