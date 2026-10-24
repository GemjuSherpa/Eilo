import copy
import unittest
from lifecycle_report import CASES,validate


def fixture():
    return dict(schema_version=1,scope='IOS_LAB_LIFECYCLE_OBSERVATIONS',cases=[],phase='PARTIAL',pending_case='NONE',
                physical_gate_acceptance='NOT_RUN',production='NOT_ENABLED',acoustic_stop_timing='NOT_RUN',
                locked_capture_support='NOT_ENABLED',network_observation='NOT_RUN',raw_audio_saved=False,
                raw_text_exported=False,lock_action='OPERATOR_REQUESTED_NOT_OS_LOCK_PROOF',
                process_session='00000000-0000-4000-8000-000000000000',os_build='synthetic test',
                physical_memory_bytes=8*1024**3,updated_utc='2026-10-24T00:00:00Z')


def full():
    r=fixture();r['phase']='COMPLETED'
    r['cases']=[dict(case=key,attempt=1,outcome='OBSERVED',active_observed=True,
                     stop_event='STOP_BUTTON' if key.endswith('_stop') else 'SCENE_RESIGNED',
                     stopped_after_event=True,resumption_observed=False,return_check_completed=True) for key in CASES]
    return r


class LifecycleTests(unittest.TestCase):
    def test_partial_pending_full(self):
        validate(fixture());r=fixture();r.update(phase='IN_PROGRESS',pending_case=CASES[0]);validate(r)
        self.assertEqual(validate(full())['observed_cases'],6)

    def test_failed_attempt_retained(self):
        r=full();bad=copy.deepcopy(r['cases'][0]);bad.update(outcome='FAILED',active_observed=False,return_check_completed=False)
        r['cases'].insert(0,bad);r['cases'][1]['attempt']=2
        self.assertEqual(validate(r)['failed_attempts'],1)

    def test_false_acceptance_content_and_lock_claim_rejected(self):
        for key,value in [('physical_gate_acceptance','PASS'),('network_observation','NO_TRAFFIC_VERIFIED'),
                          ('locked_capture_support','PASS'),('lock_action','OS_LOCK_VERIFIED'),
                          ('transcript','private'),('raw_audio_saved',True)]:
            r=full();r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)

    def test_cannot_infer_start_stop_return_or_no_resume(self):
        for key,value in [('active_observed',False),('stopped_after_event',False),('return_check_completed',False),
                          ('resumption_observed',True),('stop_event','NONE'),('attempt',True),('controller_log','private')]:
            r=full();r['cases'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)

    def test_cannot_drop_reorder_duplicate_or_promote_partial(self):
        for mutation in [lambda r:r['cases'].pop(),lambda r:r['cases'].reverse(),
                         lambda r:r['cases'].append(r['cases'][0]),lambda r:r.update(pending_case=CASES[0])]:
            r=full();mutation(r)
            with self.assertRaises(ValueError):validate(r)

    def test_lock_callback_order_requires_return_and_is_not_background(self):
        r=full()
        for index in [2,5]:r["cases"][index]["stop_event"]="PROTECTED_DATA_UNAVAILABLE"
        self.assertEqual(validate(r)["observed_cases"],6)
        r["cases"][2]["return_check_completed"]=False
        with self.assertRaises(ValueError):validate(r)
        r=full();r["cases"][1]["stop_event"]="PROTECTED_DATA_UNAVAILABLE"
        with self.assertRaises(ValueError):validate(r)

    def test_actual_device_report_when_present(self):
        import json
        from pathlib import Path
        path=Path(__file__).parent/'tests/ios-lifecycle-device-results.json'
        if not path.exists():self.skipTest('physical collection pending')
        validate(json.loads(path.read_text()))


if __name__=='__main__':unittest.main()
