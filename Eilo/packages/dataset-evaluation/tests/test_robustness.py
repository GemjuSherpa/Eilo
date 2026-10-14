import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from audio import RATE, write_wav
from benchmark import report
from manifests import canonical_digest, sha256
from noise import variants
from robustness import export, summarize, verify_pairs


class RobustnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        def manifest(name, task, samples):
            path = self.root/(name+'.wav')
            pcm = write_wav(path, samples)
            case = {'id': ('a' if name == 'clean' else 'b')*24, 'task': task,
                    'samples': len(samples), 'slice': name, 'split': 'test',
                    'path': path.name, 'sha256': sha256(path), 'pcm_sha256': pcm}
            case.update({'vad': []} if task == 'vad' else {'reference': 'yes stop'})
            return {'schema_version': 1, 'rate': RATE, 'kind': 'synthetic',
                    'dataset': 'synthetic', 'release': '1', 'cases': [case]}
        self.clean = manifest('clean','asr',[int(8000*math.sin(i*.1)) for i in range(1600)])
        self.pool = manifest('noise','vad',[500,-500,1000,-1000]*400)
        self.noisy_root = self.root/'noisy'
        self.noisy = variants(self.clean,self.root,self.pool,self.root,self.noisy_root)
        self.adapter = {'name':'Synthetic fixture; no recognition','kind':'synthetic',
                        'binary_sha256':'c'*64,'model_sha256':'d'*64,'config_sha256':'e'*64}
        def measured(manifest, text):
            return report(manifest, {'schema_version':1,'manifest_sha256':canonical_digest(manifest),
                                    'adapter':self.adapter,'cases':[{'id':c['id'],'transcript':text,'seconds':.01}
                                                                  for c in manifest['cases']]})
        self.clean_report = measured(self.clean, 'yes stop')
        self.noisy_report = measured(self.noisy, 'yes')

    def result(self, noisy=None, noisy_report=None):
        return summarize(self.clean,self.root,self.pool,self.root,noisy or self.noisy,self.noisy_root,
                         self.clean_report,noisy_report or self.noisy_report)

    def test_hand_computed_paired_deltas_and_privacy(self):
        self.adapter['private_note']='PRIVATE_ADAPTER_NOTE'
        result = self.result()
        self.assertEqual(result['status'],'MEASURED_DIAGNOSTIC')
        self.assertEqual(result['quality_acceptance'],'NOT_ASSESSED')
        self.assertEqual(len(result['comparisons']),6)
        for row in result['comparisons']:
            self.assertEqual(row['clean']['count'],row['noisy']['count'])
            self.assertEqual(row['absolute_metric_delta']['wer'],.5)
        payload = json.dumps(result)
        for private in ('yes stop', str(self.root), self.clean['cases'][0]['id'], 'PRIVATE_ADAPTER_NOTE'):
            self.assertNotIn(private,payload)
        self.assertTrue(all(v=='NOT_RUN' for v in result['physical_gates'].values()))
        output=self.root/'summary'; export(result,output)
        self.assertIn('NOT_ASSESSED',(output/'summary.html').read_text())
        with self.assertRaises(ValueError): export(result,output)

    def test_changed_parent_pool_and_recipe_rejected(self):
        for field in ('parent_manifest_sha256','noise_manifest_sha256','recipe'):
            value=copy.deepcopy(self.noisy);value[field]='changed'
            with self.subTest(field=field),self.assertRaises(ValueError): self.result(value)

    def test_complete_unique_pair_grid_required(self):
        missing=copy.deepcopy(self.noisy);missing['cases'].pop()
        with self.assertRaises(ValueError): self.result(missing)
        duplicate=copy.deepcopy(self.noisy);duplicate['cases'][1]=copy.deepcopy(duplicate['cases'][0])
        with self.assertRaises(ValueError): self.result(duplicate)

    def test_changed_pair_truth_or_recipe_rejected(self):
        for field,value in [('reference','wrong truth'),('parent_id','f'*24),('noise_id','f'*24),
                            ('slice','wrong'),('split','validation')]:
            changed=copy.deepcopy(self.noisy);changed['cases'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError): self.result(changed)
        changed=copy.deepcopy(self.noisy);changed['cases'][0]['mix']['achieved_snr_db']+=.1
        with self.assertRaises(ValueError): self.result(changed)

    def test_audio_and_backend_changes_rejected(self):
        for field in ('adapter','normalization','scoring','production_readiness'):
            changed=copy.deepcopy(self.noisy_report)
            if field == 'adapter': changed[field]['model_sha256']='f'*64
            else: changed[field]='changed'
            with self.subTest(field=field),self.assertRaises(ValueError): self.result(noisy_report=changed)
        path=self.noisy_root/self.noisy['cases'][0]['path']
        write_wav(path,[1]*1600)
        with self.assertRaises(ValueError): self.result()

    def test_consistently_rehashed_wrong_pcm_still_fails_recipe(self):
        changed=copy.deepcopy(self.noisy);case=changed['cases'][0]
        path=self.noisy_root/case['path']
        case['pcm_sha256']=write_wav(path,[1]*1600);case['sha256']=sha256(path)
        with self.assertRaisesRegex(ValueError,'mixed PCM not reproducible'):
            verify_pairs(self.clean,self.root,self.pool,self.root,changed,self.noisy_root)

    def test_synthetic_adapter_cannot_establish_public_evidence(self):
        self.clean['kind']=self.noisy['kind']='public_corpus'
        self.clean_report['kind']=self.noisy_report['kind']='public_corpus'
        self.clean_report['manifest_sha256']=canonical_digest(self.clean)
        self.noisy_report['manifest_sha256']=canonical_digest(self.noisy)
        # Corpus bytes are covered by verify_pairs tests; isolate cached-report trust here.
        with patch('robustness.verify_pairs'), self.assertRaisesRegex(ValueError,'synthetic adapter'):
            self.result()
