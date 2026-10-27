import copy
import itertools
import math
from pathlib import Path
import random
import unittest
from unittest.mock import patch
import calibrate as c
import select_test as s
import calibration_report as report


class CalibrationTests(unittest.TestCase):
    def test_pava_matches_exhaustive_monotone_squared_loss(self):
        grid=sorted({k/n for n in range(1,5) for k in range(n+1)})
        candidates=list(itertools.combinations_with_replacement(grid,4))
        for labels in itertools.product([False,True],repeat=4):
            pairs=list(zip([.1,.3,.6,.9],labels));model=c.fit(pairs)
            loss=sum((c.predict(model,x)-y)**2 for x,y in pairs)
            oracle=min(sum((p-y)**2 for p,y in zip(values,labels)) for values in candidates)
            self.assertAlmostEqual(loss,oracle,places=12)

    def test_ties_are_weighted_and_order_independent(self):
        pairs=[(.1,True),(.1,True),(.1,False),(.2,False)]
        expected=c.fit(pairs)
        for perm in itertools.permutations(pairs):self.assertEqual(c.fit(list(perm)),expected)
        self.assertEqual(c.predict(expected,.1),.5);self.assertEqual(c.predict(expected,.2),.5)

    def test_right_closed_steps_and_endpoint_clamping(self):
        model=c.fit([(.2,False),(.7,True)])
        for score,value in [(0,0),(.2,0),(.200001,1),(.7,1),(1,1)]:self.assertEqual(c.predict(model,score),value)
        self.assertEqual(c.predict(c.fit([(0,False),(1,False)]),.5),0)

    def test_invalid_fit_data_and_models_rejected(self):
        for pairs in [[],[(float('nan'),True)],[(-.1,True)],[(1.1,False)],[(True,True)],[(.5,1)]]:
            with self.subTest(pairs=pairs),self.assertRaises(ValueError):c.fit(pairs)
        model=c.fit([(.1,False),(.9,True)])
        for mutate in [lambda m:m.update(raw_audio='bad'),lambda m:m['blocks'].reverse(),lambda m:m['blocks'][0].update(count=0),lambda m:m['blocks'][0].update(correct=2),lambda m:m.update(maximum=.8)]:
            changed=copy.deepcopy(model);mutate(changed)
            with self.assertRaises(ValueError):c.predict(changed,.5)

    def test_unavailable_rows_keep_denominator_and_zero_is_real_score(self):
        models={name:c.fit([(.1,False),(.9,True)]) for name in c.SOURCES}
        def path(name,status):return dict(source=name,status=status,reason='COLLECTOR_ERROR') if status=='UNAVAILABLE' else dict(source=name,status=status,confidence=.1,exact_match=False,word_errors=1,reference_words=1,character_errors=1,reference_characters=1)
        cases=[dict(paths=[path(n,'AVAILABLE') for n in c.SOURCES]),dict(paths=[path(n,'UNAVAILABLE') for n in c.SOURCES])]
        results=c.mapped_metrics(cases,models);report.comparisons(results,2)
        for result in results:
            self.assertEqual(result['mapped']['score_coverage'],.5)
            self.assertEqual(result['mapped']['brier_score'],0)
            self.assertIsNone(result['mapped']['policy_0_85_diagnostic']['risk'])


class SelectionTests(unittest.TestCase):
    def tables(self):
        rows=[dict(client_id='s'+str(i),sentence='phrase '+str(i)+' '+str(j),path=f'clip-{i}-{j}.mp3') for i in range(16) for j in range(3)]
        return dict(train=[dict(client_id='train',sentence='training',path='train.mp3')],dev=[dict(client_id='dev',sentence='development',path='dev.mp3')],test=rows)

    def test_selection_excludes_speakers_and_text_with_two_clip_cap(self):
        tables=self.tables();old=[dict(cases=[]),dict(cases=[dict(speaker=s.opaque('s0'),reference='phrase 1 0')]),dict(cases=[])]
        chosen=s.choose(tables,old)
        self.assertEqual(len(chosen),30);self.assertNotIn('s0',{r['client_id'] for r in chosen})
        self.assertNotIn('phrase 1 0',{r['sentence'] for r in chosen})
        self.assertTrue(all(sum(r['client_id']==name for r in chosen)<=2 for name in {r['client_id'] for r in chosen}))
        random.Random(12).shuffle(tables['test']);self.assertEqual(s.choose(tables,old),chosen)

    def test_cross_curator_overlap_unsafe_paths_and_insufficient_data_fail(self):
        for mutate in [lambda t:t['train'][0].update(client_id='s1'),lambda t:t['test'][0].update(path='../clip.mp3'),lambda t:t.update(test=t['test'][:10])]:
            tables=self.tables();mutate(tables)
            with self.assertRaises(ValueError):s.choose(tables,[dict(cases=[]) for _ in range(3)])

    def test_prior_test_speaker_reuse_is_allowed_but_development_is_not(self):
        old=[dict(cases=[dict(speaker=s.opaque('s0'),reference='earlier test utterance')]),
             dict(cases=[dict(speaker=s.opaque('s1'),reference='earlier development utterance')]),dict(cases=[])]
        chosen=s.choose(self.tables(),old);speakers={r['client_id'] for r in chosen}
        self.assertIn('s0',speakers);self.assertNotIn('s1',speakers)

    def test_independent_verifier_rejects_every_overlap_dimension(self):
        old=[dict(receipt={},cases=[]),dict(receipt={},cases=[dict(speaker='old',source_sha256='old',pcm_sha256='old',reference='old reference')]),dict(receipt={},cases=[])]
        case=dict(split='test',task='asr',samples=16000)
        manifest=dict(receipt={},cases=[dict(case,speaker='s'+str(i//2),source_sha256='source'+str(i),pcm_sha256='pcm'+str(i),reference='phrase '+str(i)) for i in range(30)])
        with patch.object(s,'exclusions',return_value=old),patch.object(s,'validate_manifest'),patch.object(s,'read',return_value=manifest):s.verify(Path('/fixture'),[])
        for key in ('speaker','source_sha256','pcm_sha256','reference'):
            changed=copy.deepcopy(manifest);changed['cases'][0][key]=old[1]['cases'][0][key]
            with patch.object(s,'exclusions',return_value=old),patch.object(s,'validate_manifest'),patch.object(s,'read',return_value=changed),self.assertRaises(ValueError):s.verify(Path('/fixture'),[])


class AggregateTests(unittest.TestCase):
    def test_commit_guard_rejects_invalid_or_changed_freeze_before_inference(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('calibration_evaluate_guard',c.HERE/'evaluate.py')
        evaluate=importlib.util.module_from_spec(spec);spec.loader.exec_module(evaluate)
        with self.assertRaises(ValueError):evaluate.committed_freeze('not-a-commit')
        with patch.object(evaluate.subprocess,'run') as command,patch.object(evaluate.subprocess,'check_output',return_value=b'changed freeze'),self.assertRaises(ValueError):
            evaluate.committed_freeze('a'*40)
        self.assertEqual(command.call_args.args[0][:3],['git','merge-base','--is-ancestor'])

    def test_metric_tampering_is_detected(self):
        m=c.fit([(.1,False),(.9,True)]);models={name:m for name in c.SOURCES}
        cases=[dict(paths=[dict(source=name,status='AVAILABLE',confidence=.1,exact_match=False,word_errors=1,reference_words=1,character_errors=1,reference_characters=1) for name in c.SOURCES])]
        result=c.mapped_metrics(cases,models);report.comparisons(result,1)
        for mutate in [lambda r:r[0]['mapped'].update(brier_score=.5),lambda r:r[0]['mapped'].update(available=0),lambda r:r[0].update(outside_development_score_range=2)]:
            changed=copy.deepcopy(result);mutate(changed)
            with self.assertRaises(ValueError):report.comparisons(changed,1)

    @unittest.skipUnless((c.HERE/'freeze.json').exists(),'candidate not frozen yet')
    def test_development_freeze_provenance_and_promotion_guards(self):
        f=c.read(c.HERE/'freeze.json');report.validate_freeze(f)
        for mutate in [lambda v:v.update(native_calibration='ESTABLISHED'),lambda v:v.update(production='ENABLED'),lambda v:v['source_pins'].clear(),lambda v:v.update(development_counts_sha256='0'*64)]:
            changed=copy.deepcopy(f);mutate(changed)
            with self.assertRaises(ValueError):report.validate_freeze(changed)

    @unittest.skipUnless((c.HERE/'results.json').exists(),'held-out test not evaluated yet')
    def test_recorded_result_and_no_overwrite(self):
        import tempfile
        r=c.read(c.HERE/'results.json');report.validate(r)
        for field,value in [('test_use','FIT'),('production','ENABLED'),('native_calibration','ESTABLISHED')]:
            changed=copy.deepcopy(r);changed[field]=value
            with self.assertRaises(ValueError):report.validate(changed)
        for field,value in [('development_speaker_overlap',1),('speaker_scope','UNSEEN_SPEAKERS')]:
            changed=copy.deepcopy(r);changed['selection'][field]=value
            with self.assertRaises(ValueError):report.validate(changed)
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'out';report.export(r,target)
            self.assertNotIn('/Users/',(target/'summary.json').read_text())
            with self.assertRaises(ValueError):report.export(r,target)


if __name__=='__main__':unittest.main()
