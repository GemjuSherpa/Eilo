import unittest
from report import validate


def report():
    return dict(schema_version=1,scope='INTERNAL_IOS_FOREGROUND_TRIAL',physical_gate_acceptance='NOT_RUN',production='NOT_ENABLED',
        raw_audio_saved=False,raw_text_exported=False,confidence='UNAVAILABLE',airplane_mode='NOT_PROVIDED',wifi_bluetooth='NOT_PROVIDED',
        sdk_probe_completed=False,operator_heard_probe=False,microphone_finals=0,clarification_completed=0,synthetic_model_completed=0,synthetic_model_starts=0,
        os_build='Version 26.6.1 (Build 23G83)',physical_memory_bytes=12*1024**3,phase='LAUNCHED_NO_CAPTURE',updated_utc='2026-10-19T00:00:00Z')


class TrialReportValidation(unittest.TestCase):
    def test_unrun_and_partial_failure_are_not_acceptance(self):
        r=report();validate(r);r['phase']='SIGNED_CAPTURE_ATTACHMENT_FAILED';validate(r)
        for key,value in [('physical_gate_acceptance','PASS'),('production','ENABLED'),('confidence','CALIBRATED'),('transcript','unexpected'),('raw_audio_saved',True)]:
            bad=report();bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(bad)

    def test_completed_checks_require_declared_radio_and_voice_evidence(self):
        r=report();r.update(airplane_mode='OPERATOR_DECLARED_AT_BUILD',wifi_bluetooth='OPERATOR_DECLARED_OFF_AT_BUILD',
            radio_attestation_recorded_utc='2026-10-19T00:00:00Z',sdk_probe_completed=True,operator_heard_probe=True,
            microphone_finals=1,clarification_completed=1,synthetic_model_completed=1,synthetic_model_starts=1,phase='SINGLE_TURN_SDK_COMPLETED')
        validate(r)
        for key,value in [('sdk_probe_completed',False),('operator_heard_probe',False),('microphone_finals',0),('airplane_mode','OS_VERIFIED')]:
            bad=dict(r);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(bad)

    def test_preparation_diagnostic_is_closed_and_content_free(self):
        r=report();r.update(phase="MODEL_PREPARATION_FAILED",preparation_stage="VERIFY_LAB_MANIFEST");validate(r)
        r["preparation_stage"]="arbitrary error with user content"
        with self.assertRaises(ValueError):validate(r)

    def test_malformed_metadata_rejected(self):
        for key,value in [('source_rate',float('nan')),('normalized_samples',True),('phase','arbitrary'),('route_input',['raw speech sentence']),('physical_memory_bytes',True),('updated_utc','no timestamp')]:
            bad=report();bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(bad)


if __name__=='__main__':unittest.main()
