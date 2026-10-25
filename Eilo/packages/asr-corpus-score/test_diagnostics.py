import copy
import json
import unittest
from diagnostics import SOURCES,metrics,score_response,summarize,validate_response


def path(source,confidence=.75,text='hello world'):
    return dict(source=source,status='AVAILABLE',transcript=text,tokens=2,confidence=confidence,
                geometric_mean=confidence,minimum=confidence,oracle_error=0,
                origins=dict(greedy=2,verification=0,redecode=0) if source==SOURCES[0] else dict(greedy=0,verification=2,redecode=0))


def response():return dict(schema_version=1,paths=[path(s) for s in SOURCES])


def case():return dict(id='0'*24,slice='test',task='asr',samples=16000,reference='Hello, WORLD!')


class DiagnosticsTests(unittest.TestCase):
    def test_normalized_labels_and_content_dropped(self):
        rows=score_response(case(),response(),1)
        self.assertTrue(all(row['exact_match'] for row in rows['paths']))
        encoded=json.dumps(rows)
        for token in ['Hello','hello','transcript','reference"','speaker']:self.assertNotIn(token,encoded)
        self.assertNotIn('case_id',json.dumps(summarize([rows])))

    def test_unavailable_cannot_be_zero_score_or_improve_denominator(self):
        r=response();r['paths'][1]=dict(source=SOURCES[1],status='UNAVAILABLE',reason='INCOMPLETE_DECODE')
        row=score_response(case(),r,1);other=copy.deepcopy(row);other['case_id']='1'*24
        other['paths'][0]=dict(source=SOURCES[0],status='UNAVAILABLE',reason='COLLECTOR_ERROR')
        result=summarize([row,other])[0]
        self.assertEqual(result['status'],'INCOMPLETE_SCORES')
        self.assertEqual(result['metrics']['available'],1)
        self.assertEqual(result['metrics']['score_coverage'],.5)
        self.assertEqual(result['metrics']['coverage_curve'][0]['coverage_all_cases'],.5)
        self.assertIsNone(result['metrics']['coverage_curve'][100]['risk'])
        r['paths'][1]['confidence']=0
        with self.assertRaises(ValueError):validate_response(r)

    def test_hand_calculated_brier_ece_auc_and_threshold_ties(self):
        c=case();r=response();one=score_response(c,r,1)['paths'][0]
        r=response();r['paths'][0]=path(SOURCES[0],.25,'wrong')
        two=score_response(c,r,1)['paths'][0];m=metrics([one,two],3)
        self.assertEqual(m['brier_score'],.0625);self.assertEqual(m['ece_10_bins'],.25)
        self.assertEqual(m['correctness_auroc'],1);self.assertEqual(m['correctness_pairs'],dict(higher=1,tied=0,lower=0))
        self.assertEqual(m['coverage_curve'][0]['coverage_all_cases'],2/3)
        one=dict(one,confidence=.85);two=dict(two,confidence=.85);m=metrics([one,two],3)
        self.assertEqual(m['correctness_auroc'],.5);self.assertEqual(m['policy_0_85_diagnostic']['accepted'],2)
        self.assertEqual(m['policy_0_85_diagnostic']['risk'],.5)

    def test_one_class_and_empty_scores_are_unavailable_not_quality_passes(self):
        row=score_response(case(),response(),1)['paths'][0]
        self.assertIsNone(metrics([row],1)['correctness_auroc'])
        m=metrics([],2);self.assertIsNone(m['brier_score']);self.assertIsNone(m['wer_available'])
        r=dict(case_id='0'*24,paths=[dict(source=s,status='UNAVAILABLE',reason='COLLECTOR_ERROR') for s in SOURCES])
        self.assertTrue(all(s['status']=='NO_AVAILABLE_SCORES' for s in summarize([r])))

    def test_source_identity_missing_duplicate_and_extra_content_rejected(self):
        for change in [lambda r:r['paths'].pop(),lambda r:r['paths'].reverse(),lambda r:r['paths'].append(r['paths'][0]),lambda r:r['paths'][0].update(speaker='forbidden'),lambda r:r.update(reference='forbidden')]:
            r=response();change(r)
            with self.assertRaises(ValueError):validate_response(r)

    def test_bad_numbers_counts_and_origin_misalignment_rejected(self):
        for field,value in [('confidence',float('nan')),('confidence',True),('confidence',1.1),('tokens',True),('oracle_error',1e-3),('transcript','')]:
            r=response();r['paths'][0][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):validate_response(r)
        r=response();r['paths'][0]['origins']['verification']=1
        with self.assertRaises(ValueError):validate_response(r)
        r=response();r['paths'][0]['origins']['greedy']=True
        with self.assertRaises(ValueError):validate_response(r)

if __name__=='__main__':unittest.main()
