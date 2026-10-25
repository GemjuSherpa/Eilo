import copy
import json
from pathlib import Path
import tempfile
import unittest
from report import validate,read,export

HERE=Path(__file__).resolve().parent

class ReportTests(unittest.TestCase):
    def setUp(self):self.data=json.loads((HERE/'corpus-results.json').read_text())
    def test_actual_evidence_keeps_both_sources_and_missing_case(self):
        result=validate(self.data);self.assertEqual(result['cases_total'],30)
        self.assertEqual(result['source_counts'],[dict(available=29,unavailable=1,correct=14)]*2)
        self.assertEqual(self.data['sources'][0]['unavailable_reasons'],{'EOS_WITHOUT_USABLE_SCORES':1})
        self.assertEqual(self.data['sources'][1]['unavailable_reasons'],{'GREEDY_UNAVAILABLE':1})
    def test_no_training_independence_or_threshold_promotion(self):
        for key,value in [('status','PASS'),('partition','HELD_OUT'),('model_training_overlap','EXCLUDED'),('native_calibration','PASS'),('threshold_authorization','GRANTED'),('production','ENABLED'),('physical','PASS')]:
            r=copy.deepcopy(self.data);r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_all_export_levels_are_closed(self):
        for location in ['root','provenance','source','metrics','bin','curve']:
            r=copy.deepcopy(self.data)
            target={'root':r,'provenance':r['provenance'],'source':r['sources'][0],'metrics':r['sources'][0]['metrics'],'bin':r['sources'][0]['metrics']['reliability_bins'][0],'curve':r['sources'][0]['metrics']['coverage_curve'][0]}[location]
            target['transcript']='forbidden'
            with self.subTest(location=location),self.assertRaises(ValueError):validate(r)
    def test_stale_sources_runtime_model_and_overlay_rejected(self):
        for field in ['ort_sha256','registry_sha256','model_bundle_sha256','model_provenance_sha256']:
            r=copy.deepcopy(self.data);r['provenance'][field]='0'*64
            with self.subTest(field=field),self.assertRaises(ValueError):validate(r)
        r=copy.deepcopy(self.data);r['provenance']['source_pins']['main.cpp']='0'*64
        with self.assertRaises(ValueError):validate(r)
        r=copy.deepcopy(self.data);r['provenance']['sdk_pins']['score_trace.h']='0'*64
        with self.assertRaises(ValueError):validate(r)
    def test_denominator_missing_counts_and_risk_tampering_rejected(self):
        for change in [lambda r:r['sources'][0]['metrics'].update(cases_total=29),lambda r:r['sources'][0]['metrics']['coverage_curve'][0].update(coverage_all_cases=1),lambda r:r['sources'][0].update(unavailable_reasons={}),lambda r:r['sources'][0]['metrics']['coverage_curve'][85].update(risk=0),lambda r:r['sources'].reverse()]:
            r=copy.deepcopy(self.data);change(r)
            with self.assertRaises(ValueError):validate(r)
    def test_brier_ece_auc_must_match_sufficient_statistics(self):
        for key in ['brier_score','ece_10_bins','correctness_auroc']:
            r=copy.deepcopy(self.data);r['sources'][0]['metrics'][key]=0
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
        r=copy.deepcopy(self.data);r['sources'][0]['metrics']['correctness_pairs']['higher']+=1
        with self.assertRaises(ValueError):validate(r)
        r=copy.deepcopy(self.data);r['sources'][0]['metrics']['score_moments']['sum_probability']=float('nan')
        with self.assertRaises(ValueError):validate(r)
    def test_privacy_export_no_overwrite_and_duplicate_json_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'report';export(self.data,folder)
            page=(folder/'summary.html').read_text();self.assertIn('model training overlap UNKNOWN',page)
            for field in ['"transcript"','"reference"','"speaker"','"case_id"']:self.assertNotIn(field,(folder/'summary.json').read_text())
            with self.assertRaises(ValueError):export(self.data,folder)
            bad=Path(tmp)/'duplicate.json';bad.write_text('{"status":1,"status":2}')
            with self.assertRaises(ValueError):read(bad)
            bad.write_text('{"value":NaN}')
            with self.assertRaises(ValueError):read(bad)

if __name__=='__main__':unittest.main()
