import copy
import json
from pathlib import Path
import tempfile
import unittest
from fresh_report import validate,export,validate_selection
from shared import HERE,CORPUS,SDK,read,source_pins,protocol,sha,canonical_digest


def fixture():
    baseline=read(CORPUS/'corpus-results.json')
    selection=dict(schema_version=1,purpose=protocol()['purpose'],protocol_sha256=sha(HERE/'protocol.json'),
        prior_manifest_sha256=baseline['provenance']['manifest_sha256'],receipt_sha256='a'*64,source_pins=source_pins(),
        partitions={s:dict(cases=30,speakers=16 if s=='dev' else 24,manifest_sha256=('b' if s=='dev' else 'c')*64) for s in ('dev','test')},
        prior_speaker_overlap=0,prior_utterance_overlap=0,cross_speaker_overlap=0,cross_utterance_overlap=0,
        model_training_overlap='UNKNOWN',physical='NOT_RUN',production='NOT_ENABLED')
    partitions={}
    for split in ('dev','test'):
        sources=copy.deepcopy(baseline['sources'])
        for source in sources:source['scope']=('CURATOR_DEV' if split=='dev' else 'CURATOR_TEST')+'_DIAGNOSTIC_ONLY'
        partitions[split]=dict(partition='CURATOR_DEV' if split=='dev' else 'CURATOR_TEST',cases_total=30,sources=sources,private_counts_sha256='d'*64)
    return dict(schema_version=1,purpose=protocol()['purpose'],selection=selection,source_pins=source_pins(),
        model_bundle_sha256=baseline['provenance']['model_bundle_sha256'],ort_sha256=baseline['provenance']['ort_sha256'],
        runtime_sha256='e'*64,cxx_sha256=baseline['provenance']['cxx_sha256'],overlay_pins=read(SDK/'overlay-expected.json'),partitions=partitions,
        rejected_inputs=['empty','unaligned','nan','out_of_range'],threshold_fitting='NOT_PERFORMED',model_training_overlap='UNKNOWN',
        native_calibration='NOT_ESTABLISHED',threshold_authorization='NOT_GRANTED',production='NOT_ENABLED',physical='NOT_RUN')


class FreshReportTests(unittest.TestCase):
    def test_actual_fresh_evidence_preserves_both_partitions(self):
        r=read(HERE/'results.json');rows=validate(r)
        self.assertEqual([x['available'] for x in rows],[30]*4)
        self.assertEqual([x['correct'] for x in rows],[19,19,16,15])
        self.assertEqual([x['errors_0_85'] for x in rows],[9]*4)
        self.assertEqual([r['selection']['partitions'][s]['speakers'] for s in ['dev','test']],[16,24])

    def test_both_partitions_and_source_identities_remain_separate(self):
        r=fixture();rows=validate(r);self.assertEqual(len(rows),4)
        self.assertEqual([x['partition'] for x in rows],['CURATOR_DEV']*2+['CURATOR_TEST']*2)
        r['partitions']['dev']['partition']='CURATOR_TEST'
        with self.assertRaises(ValueError):validate(r)

    def test_freshness_and_source_claims_fail_closed(self):
        for mutate in [lambda r:r['selection'].update(prior_speaker_overlap=1),lambda r:r['selection'].update(cross_utterance_overlap=1),
                       lambda r:r['selection'].update(prior_utterance_overlap=True),lambda r:r['selection']['partitions']['dev'].update(speakers=14),
                       lambda r:r['source_pins'].update(**{'asr-fresh-split/evaluate.py':'0'*64}),
                       lambda r:r['selection'].update(prior_manifest_sha256='0'*64)]:
            r=fixture();mutate(r)
            with self.assertRaises(ValueError):validate(r)

    def test_no_fitting_training_independence_or_acceptance_promotion(self):
        for key,value in [('threshold_fitting','PERFORMED'),('model_training_overlap','EXCLUDED'),('native_calibration','PASS'),('threshold_authorization','GRANTED'),('production','ENABLED'),('physical','PASS')]:
            r=fixture();r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)

    def test_all_public_levels_are_closed_to_content(self):
        for location in ['root','selection','selection_partition','partition','source','metrics']:
            r=fixture();target={'root':r,'selection':r['selection'],'selection_partition':r['selection']['partitions']['dev'],
                'partition':r['partitions']['dev'],'source':r['partitions']['dev']['sources'][0],
                'metrics':r['partitions']['dev']['sources'][0]['metrics']}[location];target['transcript']='forbidden'
            with self.subTest(location=location),self.assertRaises(ValueError):validate(r)

    def test_missing_scores_math_model_and_partition_cannot_be_changed(self):
        for mutate in [lambda r:r['partitions'].pop('test'),lambda r:r['partitions']['test'].update(cases_total=29),
                       lambda r:r['partitions']['dev']['sources'][0]['metrics'].update(brier_score=0),
                       lambda r:r['partitions']['test']['sources'][0].update(unavailable_reasons={}),
                       lambda r:r.update(model_bundle_sha256='0'*64),lambda r:r.update(cxx_sha256='0'*64)]:
            r=fixture();mutate(r)
            with self.assertRaises(ValueError):validate(r)

    def test_json_html_no_content_no_overwrite_and_strict_parser(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'report';export(fixture(),path)
            for token in ['"transcript"','"reference"','"speaker"','"case_id"']:self.assertNotIn(token,(path/'summary.json').read_text())
            self.assertIn('Model training overlap UNKNOWN',(path/'summary.html').read_text())
            with self.assertRaises(ValueError):export(fixture(),path)
            bad=Path(tmp)/'bad.json'
            for text in ['{"x":1,"x":2}','{"x":NaN}']:
                bad.write_text(text)
                with self.assertRaises(ValueError):read(bad)


if __name__=='__main__':unittest.main()
