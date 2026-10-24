import copy
import unittest
from permission_report import validate

SESSION='00000000-0000-4000-8000-000000000001'

def fixture():
    denial=dict(kind='DENIED_START',permission='DENIED',start_requested=True,start_accepted=False,capture_effect_calls=0,
                capture_pending=False,controller_state='permission_required',prior_denial_same_process=False,outcome='OBSERVED',
                process_session=SESSION,updated_utc='2026-10-24T00:00:00Z')
    restored=dict(denial,kind='RESTORED_NO_START',permission='GRANTED',start_requested=False,prior_denial_same_process=True)
    return dict(schema_version=1,scope='IOS_OS_PERMISSION_BOUNDARY',samples=[denial,restored],raw_audio_saved=False,
                raw_text_exported=False,physical_gate_acceptance='NOT_RUN',hardware_capture='NOT_OPENED',production='NOT_ENABLED')

class PermissionReportTests(unittest.TestCase):
    def test_same_process_and_relaunch_distinguished(self):
        self.assertTrue(validate(fixture())['restoration_same_process_observed'])
        r=fixture();r['samples'][1].update(process_session='00000000-0000-4000-8000-000000000002',prior_denial_same_process=False)
        self.assertTrue(validate(r)['restoration_no_start_observed'])
        self.assertFalse(validate(r)['restoration_same_process_observed'])

    def test_no_automatic_start_cannot_be_fabricated(self):
        for field,value in [('start_accepted',True),('capture_effect_calls',1),('capture_pending',True),('controller_state','standby')]:
            r=fixture();r['samples'][1][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate(r)
            r['samples'][1]['outcome']='FAILED';self.assertEqual(validate(r)['failed_attempts'],1)

    def test_missing_denial_or_session_mismatch_rejected(self):
        r=fixture();r['samples'].pop(0)
        with self.assertRaises(ValueError):validate(r)
        r=fixture();r['samples'][1]['process_session']='00000000-0000-4000-8000-000000000002'
        with self.assertRaises(ValueError):validate(r)

    def test_closed_content_types_and_no_physical_promotion(self):
        for field,value in [('raw_text_exported',True),('transcript','synthetic forbidden'),('physical_gate_acceptance','PASS'),('hardware_capture','VERIFIED')]:
            r=fixture();r[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate(r)
        r=fixture();r['samples'][0]['capture_effect_calls']=False
        with self.assertRaises(ValueError):validate(r)
        r=fixture();r['samples']*=5
        with self.assertRaises(ValueError):validate(r)

    def test_actual_device_evidence_and_source_receipt(self):
        import hashlib,json
        from pathlib import Path
        folder=Path(__file__).parent/'tests'
        data=(folder/'ios-permission-device-results.json').read_bytes()
        provenance=json.loads((folder/'ios-permission-device-provenance.json').read_text())
        self.assertEqual(hashlib.sha256(data).hexdigest(),provenance['report_sha256'])
        result=validate(json.loads(data))
        self.assertTrue(result['denial_observed'])
        self.assertTrue(result['restoration_no_start_observed'])
        self.assertFalse(result['restoration_same_process_observed'])
        self.assertEqual(result['failed_attempts'],0)
        self.assertEqual(provenance['restoration_scope'],'FRESH_PROCESS_NO_START')

if __name__=='__main__':unittest.main()
