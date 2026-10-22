import unittest
from check_speech_android_evidence import ROOT,load,validate,check_evidence

class SpeechSdkEvidenceTests(unittest.TestCase):
    def report(self):return load(ROOT/'packages/conversation-integration/tests/android-speech-results.json')
    def test_actual_pins_and_callbacks(self):check_evidence()
    def test_scope_and_privacy_claims_reject(self):
        for key,value in [('physical','PASS'),('network_acceptance','PASS'),('acoustic_acceptance','PASS'),('production','ENABLED'),
            ('microphone','USED'),('download_requested',True),('temporary_files_removed',False),('normal_app_restored',False),
            ('internet_permission','PRESENT'),('microphone_permission','PRESENT'),('voice_id','unexpected'),('android_api',True)]:
            report=self.report();report[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(report)
    def test_events_and_flags_must_match(self):
        for key,value in [('sdk_started',0),('sdk_finished',2),('sdk_started',True),('sdk_completed',False),('eligible_voice',False),('status','PASS')]:
            report=self.report();report[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(report)
    def test_missing_voice_is_blocked_not_sdk_pass(self):
        report=self.report();report.update(status='BLOCKED_OFFLINE_VOICE_MISSING',eligible_voice=False,sdk_completed=False,sdk_started=0,sdk_finished=0);validate(report)
        report['sdk_completed']=True
        with self.assertRaises(ValueError):validate(report)

if __name__=='__main__':unittest.main()
