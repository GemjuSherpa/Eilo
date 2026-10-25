import copy
import random
import unittest
from unittest.mock import patch
from pathlib import Path
from select_split import choose
from evaluate import verify_cohorts
from shared import opaque, protocol, source_pins, canonical_digest, sha, HERE


def fixture():
    tables={split:[dict(client_id=split+str(i//2),sentence=split+' words '+str(i),path=split+str(i)+'.mp3') for i in range(8)] for split in ['train','dev','test']}
    prior=dict(cases=[dict(speaker=opaque('old'),reference='previous words',split='test')])
    p=dict(protocol(),development_count=3,test_count=3)
    return tables,prior,p


class SelectionTests(unittest.TestCase):
    def test_deterministic_under_metadata_reordering(self):
        t,old,p=fixture();expected=choose(t,old,p)
        for rows in t.values():random.Random(42).shuffle(rows)
        self.assertEqual(choose(t,old,p),expected)

    def test_hashed_prior_speaker_and_normalized_text_exclusion(self):
        t,old,p=fixture()
        t['dev'] += [dict(client_id='old',sentence='new words',path='old.mp3'),
                     dict(client_id='new',sentence='PREVIOUS, words!',path='same.mp3')]
        result=choose(t,old,p)
        for r in result['dev']:
            self.assertNotEqual(r['client_id'],'old');self.assertNotEqual(r['path'],'same.mp3')

    def test_cross_partition_speaker_overlap_rejected_even_if_not_selected(self):
        t,old,p=fixture();t['test'][0]['client_id']=t['dev'][0]['client_id']
        with self.assertRaises(ValueError):choose(t,old,p)
        t,old,p=fixture();t['train'][0]['client_id']=t['dev'][0]['client_id']
        with self.assertRaises(ValueError):choose(t,old,p)

    def test_duplicate_utterances_and_speaker_cap_cannot_fill_count(self):
        t,old,p=fixture()
        for r in t['dev']:r['sentence']='same words'
        with self.assertRaises(ValueError):choose(t,old,p)
        t,old,p=fixture()
        for r in t['dev']:r['client_id']='single'
        with self.assertRaises(ValueError):choose(t,old,p)

    def test_cross_utterance_excluded_and_limit_enforced(self):
        t,old,p=fixture();p.update(development_count=5,test_count=5)
        selected=choose(t,old,p)
        self.assertEqual(len(selected['dev']),5)
        from collections import Counter
        self.assertLessEqual(max(Counter(r['client_id'] for r in selected['dev']).values()),2)
        t['test'][0]['sentence']=selected['dev'][0]['sentence'].upper()+'!'
        selected=choose(t,old,p)
        self.assertNotIn(t['test'][0],selected['test'])

    def test_unsafe_duplicate_or_missing_metadata_rejected(self):
        for mutation in [lambda t:t['dev'][0].update(path='../escape.mp3'),lambda t:t['dev'][0].update(path='a\\b.mp3'),
                         lambda t:t['dev'].append(copy.deepcopy(t['dev'][0])),lambda t:t['dev'][0].update(sentence='')]:
            t,old,p=fixture();mutation(t)
            with self.assertRaises(ValueError):choose(t,old,p)


def cohort_fixture():
    old=dict(receipt={},cases=[dict(speaker='prior',reference='old words',source_sha256='prior-source',pcm_sha256='prior-pcm')])
    manifests={}
    for split in ('dev','test'):
        manifests[split]=dict(dataset='common_voice',receipt={},cases=[dict(task='asr',split='validation' if split=='dev' else 'test',speaker=split+str(i),reference=split+' words '+str(i),source_sha256=split+'src'+str(i),pcm_sha256=split+'pcm'+str(i)) for i in range(30)])
    e=dict(source_pins=source_pins(),prior_manifest_sha256=canonical_digest(old),protocol_sha256=sha(HERE/'protocol.json'),
           partitions={s:dict(cases=30,speakers=30,manifest_sha256=canonical_digest(m)) for s,m in manifests.items()})
    return old,manifests,e


class CohortTests(unittest.TestCase):
    def check(self,old,manifests,e):
        def load(path):
            return old if path.name=='prior.json' else e if path.name=='selection.json' else manifests[path.parent.name]
        with patch('evaluate.read',side_effect=load),patch('evaluate.validate_manifest'):
            return verify_cohorts(Path('/synthetic'),Path('/prior.json'))

    def test_correct_partitions_pass_and_actual_overlap_fails(self):
        old,m,e=cohort_fixture();self.check(old,m,e)
        for key,value in [('speaker','prior'),('reference','OLD, words!'),('source_sha256','prior-source'),('pcm_sha256','prior-pcm'),('split','test')]:
            old,m,e=cohort_fixture();m['dev']['cases'][0][key]=value;e['partitions']['dev']['manifest_sha256']=canonical_digest(m['dev'])
            with self.subTest(key=key),self.assertRaises(ValueError):self.check(old,m,e)

    def test_stale_cohort_source_or_missing_case_is_rejected(self):
        old,m,e=cohort_fixture();m['test']['cases'].pop()
        with self.assertRaises(ValueError):self.check(old,m,e)
        old,m,e=cohort_fixture();e['source_pins']['asr-fresh-split/evaluate.py']='0'*64
        with self.assertRaises(ValueError):self.check(old,m,e)


if __name__=='__main__':unittest.main()
