"""Adversarial checks for committed joined framework observations; no native caches."""
import copy
import json
import unittest
from framework_capture_report import HERE, validate, framework_module


class FrameworkCaptureTests(unittest.TestCase):
    def setUp(self):
        self.r=framework_module().read(HERE/'tests/ios-framework-capture-results.json')

    def reject(self,mutate):
        value=copy.deepcopy(self.r);mutate(value)
        with self.assertRaises((ValueError, RuntimeError, AssertionError, KeyError, TypeError)):
            validate(value)

    def test_current_execution(self):
        summary=validate(self.r)
        self.assertEqual([r['llm_starts'] for r in summary['cases']],[1,1,0])
        self.assertEqual(summary['release'],'HOLD')

    def test_acceptance_and_audio_escalation(self):
        for key,value in [('physical','PASS'),('production','ENABLED'),('confidence','CALIBRATED'),('voice_evidence','VERIFIED'),('microphone','USED'),('sdk_speech_gain',1),('sdk_speech_gain',False)]:
            with self.subTest(key=key,value=value):self.reject(lambda r:r.update({key:value}))

    def test_loader_path_and_relocation(self):
        for value in [['/usr/lib/swift','/tmp/frameworks'],['/usr/lib/swift','@executable_path/Frameworks','/tmp']]:
            self.reject(lambda r:r.update(client_rpaths=value))
        self.reject(lambda r:r.update(relocation='BUILT_ONLY'))
        self.reject(lambda r:r['framework'].update(install_name='/tmp/CEiloAsr'))

    def test_joined_behavior_required(self):
        for row,key,value in [(0,'completed',False),(1,'context_messages',2),(2,'llm_starts',1),(2,'recognized',1),(0,'inference_worker_verified',False),(0,'normalized_samples',True),(1,'transcript_sha256','0'*64)]:
            with self.subTest(row=row,key=key):self.reject(lambda r:r['cases'][row].update({key:value}))
        self.reject(lambda r:r.update(cases=list(reversed(r['cases']))))

    def test_source_and_model_drift(self):
        self.reject(lambda r:r['source_pins'].pop())
        self.reject(lambda r:r['source_pins'][0].update(sha256='0'*64))
        for key in ['fixture_sha256','vad_model_sha256','llm_model_sha256','source_sha256']:
            self.reject(lambda r:r.update({key:'0'*64}))

    def test_closed_schema_and_libraries(self):
        self.reject(lambda r:r.update(secret='unexpected'))
        self.reject(lambda r:r.update(schema_version=True))
        self.reject(lambda r:r['llm_libraries'].pop())
        self.reject(lambda r:r['llm_libraries'][0].update(file='/private/path/libllama.a'))
        self.reject(lambda r:r['llm_libraries'][0].update(sha256='bad'))
        self.reject(lambda r:r['cases'][0].update(transcript='private'))

    def test_duplicate_json_fields_rejected(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'report.json';path.write_text('{"scope":1,"scope":2}')
            with self.assertRaises(ValueError):framework_module().read(path)


if __name__=='__main__':unittest.main()
