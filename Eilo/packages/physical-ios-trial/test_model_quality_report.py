import copy
import json
from pathlib import Path
import unittest
from model_quality_report import FIXED, validate, validate_pair


def sample(complete=False):
    pin = json.loads(Path(__file__).with_name('tests').joinpath('model-comparison-pins.json').read_text())[0]
    return dict(FIXED, model_sha256=pin['sha256'], model_bytes=pin['bytes'], session_id='12345678-1234-1234-1234-123456789ABC',
                os_build='Version 26.6.1 (Build 23G83)', updated_utc='2026-10-19T12:00:00Z',
                attempts=[dict(fixture_id=f'compare-{i:02d}', attempt=i, model_status='GENERATED', rubric_quality=3) for i in range(1, 7)] if complete else [])


class QualityReportTests(unittest.TestCase):
    def test_partial_complete_retry(self):
        validate(sample());validate(sample(True))
        r=sample();r['attempts']=[dict(fixture_id='compare-01',attempt=i,model_status=s) for i,s in enumerate(['FAILED','CANCELLED','GENERATED'],1)]
        r['attempts'][-1]['rubric_quality']=4;validate(r)

    def test_content_and_fake_acceptance_denied(self):
        for key,value in [('response','text'),('raw_text_exported',True),('physical_gate_acceptance','PASS'),('network_observation','NO_TRAFFIC_VERIFIED'),('rating_source','MODEL'),('threads',True),('model_sha256','0'*64)]:
            r=sample(True);r[key]=value
            with self.assertRaises(ValueError):validate(r)
        r=sample(True);r['attempts'][0]['text']='response'
        with self.assertRaises(ValueError):validate(r)

    def test_invalid_scores_and_status(self):
        for value in (True,0,6,3.5,None):
            r=sample(True);r['attempts'][0]['rubric_quality']=value
            with self.assertRaises(ValueError):validate(r)
        for status in ('GENERATING','FAILED','CANCELLED'):
            r=sample(True);r['attempts'][0]['model_status']=status
            with self.assertRaises(ValueError):validate(r)

    def test_sequence_retries_and_pending(self):
        r=sample(True);r['attempts'].reverse()
        with self.assertRaises(ValueError):validate(r)
        r=sample(True);r['attempts'][1]=copy.deepcopy(r['attempts'][0])
        with self.assertRaises(ValueError):validate(r)
        r=sample();r['attempts']=[dict(fixture_id='compare-01',attempt=i,model_status='CANCELLED') for i in range(1,5)]
        with self.assertRaises(ValueError):validate(r)
        r=sample(True);del r['attempts'][0]['rubric_quality']
        with self.assertRaises(ValueError):validate(r)

    def test_pair_needs_actual_completed_distinct_models(self):
        a,b=sample(True),sample(True)
        with self.assertRaises(ValueError):validate_pair([a,b])
        pin=json.loads(Path(__file__).with_name('tests').joinpath('model-comparison-pins.json').read_text())[1]
        b.update(model_sha256=pin['sha256'],model_bytes=pin['bytes'],session_id='87654321-1234-1234-1234-123456789ABC')
        validate_pair([a,b]);b['attempts'].pop()
        with self.assertRaises(ValueError):validate_pair([a,b])


if __name__ == '__main__':unittest.main()
