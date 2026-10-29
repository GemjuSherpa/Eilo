import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import negative as n
import negative_report as report


def fixture():
    baseline=n.read(n.HERE/'results.json')['native']['provenance'];rows=[]
    for group,count in zip(n.GROUPS,(12,3,3)):
        for _ in range(count):rows.append(dict(group=group,paths=[dict(source=s,status='AVAILABLE',word_bearing=True,raw=.9,mapped=.5,outside=False) for s in n.SOURCES]))
    return dict(schema_version=1,purpose=n.policy()['purpose'],protocol_commit='a'*40,source_pins=n.pins(),controls_sha256='1'*64,
                musan_manifest_sha256=n.read(n.CORPUS/'noise-results/suite.json')['noise_manifest_sha256'],private_counts_sha256='2'*64,
                private_model_sha256=n.read(n.HERE/'freeze.json')['private_model_sha256'],
                **{k:baseline[k] for k in ('model_bundle_sha256','model_provenance_sha256','ort_sha256','cxx_sha256','overlay_pins')},
                runtime_sha256='3'*64,groups=n.summarize(rows),rejected_inputs=['empty','unaligned','nan','out_of_range'],**n.FLAGS)


class NegativeTests(unittest.TestCase):
    def test_unavailable_is_not_observed_no_text(self):
        rows=[]
        for group,count in zip(n.GROUPS,(12,3,3)):
            for _ in range(count):rows.append(dict(group=group,paths=[dict(source=s,status='UNAVAILABLE',reason='INCOMPLETE_DECODE') for s in n.SOURCES]))
        for r in n.summarize(rows):
            self.assertEqual(r['available'],0);self.assertEqual(r['unavailable'],r['cases'])
            self.assertEqual(r['observed_word_bearing'],0)
        f=fixture();f['groups']=n.summarize(rows);self.assertEqual(report.validate(f)['unavailable'],'TEXT_OUTCOME_NOT_OBSERVABLE')

    def test_per_group_denominators_and_raw_mapped_counts(self):
        f=fixture();report.validate(f)
        self.assertEqual([r['cases'] for r in f['groups']],[12,12,3,3,3,3])
        for row in f['groups']:
            self.assertEqual(row['observed_word_bearing_fraction_all_cases'],1)
            self.assertEqual(row['raw_accepted_word_bearing'],row['cases'])
            self.assertEqual(row['mapped_accepted_word_bearing'],0)

    def test_no_correctness_vad_system_or_production_promotion(self):
        for key in n.FLAGS:
            f=fixture();f[key]='PASS'
            with self.subTest(key=key),self.assertRaises(ValueError):report.validate(f)
        f=fixture();f['groups'][0]['wer']=0
        with self.assertRaises(ValueError):report.validate(f)

    def test_tampered_pins_and_missing_or_changed_groups_denied(self):
        for mutate in [lambda f:f['source_pins'].clear(),lambda f:f.update(private_model_sha256='0'*64),lambda f:f.update(musan_manifest_sha256='0'*64),
                       lambda f:f['groups'].pop(),lambda f:f['groups'][0].update(cases=11),lambda f:f['groups'][0].update(available=True),
                       lambda f:f['groups'][0].update(observed_word_bearing_fraction_all_cases=.1),lambda f:f['groups'][0].update(mapped_accepted_word_bearing=13)]:
            f=fixture();mutate(f)
            with self.assertRaises(ValueError):report.validate(f)

    def test_native_response_validation_and_word_bearing(self):
        native=dict(source=n.SOURCES[0],status='AVAILABLE',transcript='...',tokens=1,confidence=.9,geometric_mean=.9,minimum=.9,oracle_error=0,origins=dict(greedy=1,verification=0,redecode=0))
        response=dict(schema_version=1,paths=[native,dict(source=n.SOURCES[1],status='UNAVAILABLE',reason='GREEDY_UNAVAILABLE')])
        model=dict(minimum=.5,maximum=1,blocks=[dict(upper=1,count=2,correct=1)])
        obs=n.observation(n.GROUPS[0],response,{s:model for s in n.SOURCES})
        self.assertFalse(obs['paths'][0]['word_bearing']);self.assertEqual(obs['paths'][0]['mapped'],.5)
        native['transcript']='Some words';self.assertTrue(n.observation(n.GROUPS[0],response,{s:model for s in n.SOURCES})['paths'][0]['word_bearing'])
        native['confidence']=float('nan')
        with self.assertRaises(ValueError):n.observation(n.GROUPS[0],response,{s:model for s in n.SOURCES})

    def test_protocol_must_preexist_and_export_no_overwrite(self):
        with self.assertRaises(ValueError):n.committed('bad')
        with patch.object(n.subprocess,'run'),patch.object(n.subprocess,'check_output',return_value=b'changed'),self.assertRaises(ValueError):n.committed('a'*40)
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'summary';report.export(fixture(),out)
            text=(out/'summary.json').read_text();self.assertNotIn('transcript',text);self.assertNotIn('/Users/',text)
            with self.assertRaises(ValueError):report.export(fixture(),out)

    @unittest.skipUnless((n.HERE/'negative-results.json').exists(),'native controls not yet run')
    def test_actual_results(self):
        self.assertEqual(report.validate(n.read(n.HERE/'negative-results.json'))['physical'],'NOT_RUN')


if __name__=='__main__':unittest.main()
