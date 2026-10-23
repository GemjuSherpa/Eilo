import hashlib
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from confidence import summarize,read,export,bind_labels,MAX_BYTES,MAX_CASES
from benchmark import report
from test_benchmark import fixture as benchmark_fixture
from manifests import canonical_digest
import copy
import subprocess


def fixture(scores=(.9,.8,.2,.1),labels=(True,True,False,False),kind='MODEL_PROBABILITY'):
    return {'schema_version':1,'signal_kind':kind,'partition':'DECLARED_HELD_OUT',
            'provenance':{key:'a'*64 for key in ('dataset_manifest_sha256','asr_report_sha256','runtime_sha256','model_sha256')},
            'cases':[{'case_sha256':hashlib.sha256(str(i).encode()).hexdigest(),'confidence':score,'exact_match':label}
                     for i,(score,label) in enumerate(zip(scores,labels))]}


class ConfidenceTests(unittest.TestCase):
    def summary(self,value):return summarize(value,'b'*64)
    def test_known_metrics_and_no_acceptance(self):
        r=self.summary(fixture());self.assertAlmostEqual(r['brier_score'],.025);self.assertAlmostEqual(r['ece_10_bins'],.15)
        self.assertEqual(r['correctness_auroc'],1);self.assertEqual(r['status'],'DIAGNOSTIC_ONLY')
        self.assertEqual(r['policy_0_85_diagnostic'],{'threshold':.85,'accepted':1,'errors':0,'coverage':.25,'risk':0.})
        for key,value in [('native_calibration','NOT_RUN'),('threshold_authorization','NOT_GRANTED'),('quality_acceptance','NOT_ASSESSED'),('production_readiness','NOT_ENABLED')]:self.assertEqual(r[key],value)
    def test_inverted_and_tied_auc(self):
        self.assertEqual(self.summary(fixture((.1,.2,.8,.9)))['correctness_auroc'],0)
        self.assertEqual(self.summary(fixture((.5,)*4))['correctness_auroc'],.5)
        value=fixture((.8,.8,.4,.4),(True,False,True,False));expected=self.summary(value)
        random.Random(7).shuffle(value['cases']);self.assertEqual(self.summary(value),expected)
    def test_auc_matches_pairwise_definition_with_ties(self):
        rng=random.Random(17)
        for _ in range(50):
            scores=[rng.choice((0.,.3,.7,1.)) for _ in range(16)]
            labels=[bool(rng.randrange(2)) for _ in scores]
            positives=[s for s,label in zip(scores,labels) if label];negatives=[s for s,label in zip(scores,labels) if not label]
            expected=(sum(float(p>n)+.5*float(p==n) for p in positives for n in negatives)/(len(positives)*len(negatives))) if positives and negatives else None
            self.assertEqual(self.summary(fixture(scores,labels))['correctness_auroc'],expected)
    def test_placeholder_and_all_ones_do_not_authorize(self):
        for kind in ('SYNTHETIC','PLACEHOLDER'):
            self.assertEqual(self.summary(fixture(kind=kind))['status'],'UNUSABLE_DECLARED_SIGNAL')
        r=self.summary(fixture((1.,)*4));self.assertEqual(r['status'],'UNINFORMATIVE_CONSTANT_SIGNAL');self.assertEqual(r['brier_score'],.5)
    def test_one_class_auc_unavailable_and_zero_coverage_undefined(self):
        r=self.summary(fixture((0.,.2),(True,True)));self.assertIsNone(r['correctness_auroc'])
        self.assertEqual(r['status'],'INSUFFICIENT_LABEL_VARIATION');self.assertIsNone(r['coverage_curve'][-1]['risk'])
    def test_endpoints_belong_to_single_bin(self):
        r=self.summary(fixture((0.,.1,.9,1.)));self.assertEqual(sum(b['count'] for b in r['reliability_bins']),4)
        self.assertEqual(r['reliability_bins'][9]['count'],2);self.assertEqual(r['coverage_curve'][100]['accepted'],1)
    def test_unknown_fields_and_unbounded_cases_reject(self):
        for field in ('transcript','audio_path','speaker_id','policy_authorization'):
            value=fixture();value[field]='private-marker'
            with self.subTest(field=field),self.assertRaises(ValueError):self.summary(value)
        for cases in ([],fixture()['cases']*(MAX_CASES//4+1)):
            v=fixture();v['cases']=cases
            with self.assertRaises(ValueError):self.summary(v)
        v=fixture();v['cases'][0]['audio']='private-marker'
        with self.assertRaises(ValueError):self.summary(v)
    def test_nonfinite_booleans_ranges_and_duplicates_reject(self):
        for score in (True,None,-.1,1.1,float('nan'),float('inf'),'0.8'):
            v=fixture();v['cases'][0]['confidence']=score
            with self.subTest(score=score),self.assertRaises(ValueError):self.summary(v)
        v=fixture();v['cases'][0]['exact_match']=1
        with self.assertRaises(ValueError):self.summary(v)
        v=fixture();v['cases'][1]['case_sha256']=v['cases'][0]['case_sha256']
        with self.assertRaises(ValueError):self.summary(v)
    def test_digest_partition_and_provenance_reject(self):
        for key,value in [('schema_version',True),('partition','TRAINING'),('signal_kind','CALIBRATED')]:
            v=fixture();v[key]=value
            with self.assertRaises(ValueError):self.summary(v)
        v=fixture();v['provenance']['runtime_sha256']='bad'
        with self.assertRaises(ValueError):self.summary(v)
    def test_bounded_unique_strict_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'input.json'
            for raw in (b'{"cases":[],"cases":[]}',b' '* (MAX_BYTES+1),b'\xff',b'{'):
                path.write_bytes(raw)
                with self.assertRaises(ValueError):read(path)
            v=fixture();v['cases'][0]['confidence']=float('nan');path.write_text(json.dumps(v));value,_=read(path)
            with self.assertRaises(ValueError):self.summary(value)
    def bound(self,correct=False):
        manifest,predictions=benchmark_fixture()
        if correct:predictions["cases"][0]["transcript"]="yes stop"
        benchmark=report(manifest,predictions)
        value=fixture((.4,),(correct,),kind='SYNTHETIC')
        value['provenance']={'dataset_manifest_sha256':canonical_digest(manifest),'asr_report_sha256':canonical_digest(benchmark),
            'runtime_sha256':benchmark['adapter']['binary_sha256'],'model_sha256':benchmark['adapter']['model_sha256']}
        value['cases'][0]['case_sha256']=canonical_digest({'manifest_sha256':canonical_digest(manifest),'case_id':manifest['cases'][0]['id']})
        return value,manifest,benchmark
    def test_benchmark_label_binding_requires_complete_same_evidence(self):
        value,manifest,benchmark=self.bound();bind_labels(value,manifest,benchmark)
        for mutation in ('label','missing','case','model','report','synthetic'):
            v=copy.deepcopy(value)
            if mutation=='label':v['cases'][0]['exact_match']=True
            elif mutation=='missing':v['cases']=[]
            elif mutation=='case':v['cases'][0]['case_sha256']='a'*64
            elif mutation=='model':v['provenance']['model_sha256']='a'*64
            elif mutation=='report':v['provenance']['asr_report_sha256']='a'*64
            else:v['signal_kind']='MODEL_PROBABILITY'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):bind_labels(v,manifest,benchmark)
    def test_correct_label_and_extra_valid_score(self):
        value,manifest,benchmark=self.bound(True);bind_labels(value,manifest,benchmark)
        value['cases'].append({'case_sha256':'e'*64,'confidence':.8,'exact_match':False})
        with self.assertRaises(ValueError):bind_labels(value,manifest,benchmark)
    def test_cli_bound_export_and_partial_sources(self):
        value,manifest,benchmark=self.bound(True)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name,item in [('scores',value),('manifest',manifest),('benchmark',benchmark)]:
                (root/(name+'.json')).write_text(json.dumps(item))
            command=[sys.executable,*(['-O'] if sys.flags.optimize else []),str(Path(__file__).resolve().parents[1]/'confidence.py'),
                '--scores',str(root/'scores.json'),'--output',str(root/'out'),'--manifest',str(root/'manifest.json')]
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertFalse((root/'out').exists())
            result=subprocess.run(command+['--asr-report',str(root/'benchmark.json')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            r=json.loads((root/'out/summary.json').read_text());self.assertEqual(r['status'],'UNUSABLE_DECLARED_SIGNAL')
            self.assertEqual(r['label_binding'],'CONSISTENCY_CHECKED_BENCHMARK_LABELS')
    def test_binding_cannot_relabel_training_or_non_asr_cases(self):
        for field,new in [('split','train'),('task','commands')]:
            value,manifest,benchmark=self.bound();manifest['cases'][0][field]=new
            with self.assertRaises(ValueError):bind_labels(value,manifest,benchmark)
    def test_bound_export_is_still_not_calibration_acceptance(self):
        value,manifest,benchmark=self.bound()
        with tempfile.TemporaryDirectory() as folder:
            r=export(value,'b'*64,Path(folder)/'report',manifest,benchmark)
            self.assertEqual(r['label_binding'],'CONSISTENCY_CHECKED_BENCHMARK_LABELS')
            self.assertEqual(r['native_calibration'],'NOT_RUN');self.assertEqual(r['threshold_authorization'],'NOT_GRANTED')
    def test_privacy_export_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'report';r=export(fixture(),'b'*64,root);raw=(root/'summary.json').read_text()
            self.assertEqual(json.loads(raw),r)
            for case in fixture()['cases']:self.assertNotIn(case['case_sha256'],raw)
            document=(root/'summary.html').read_text();self.assertNotIn('<script',document);self.assertNotIn('src=',document)
            with self.assertRaises(FileExistsError):export(fixture(),'b'*64,root)


if __name__=='__main__':unittest.main()
