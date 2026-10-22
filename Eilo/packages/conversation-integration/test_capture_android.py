"""Reject false integration acceptance and changed offline model/source evidence."""
import unittest
import tempfile
from pathlib import Path
import json
import check_capture_android_evidence as evidence
from check_capture_android import serial, require_ort_symbols, inspect_apk, LIBRARIES
import tempfile,zipfile
from unittest.mock import patch


class AndroidCaptureTests(unittest.TestCase):
    def report(self):return evidence.load(evidence.ROOT/'packages/conversation-integration/tests/android-capture-results.json')
    def test_actual_aggregate_and_pins(self):evidence.check_evidence();evidence.check_evidence(sdk=True)
    def test_sdk_cannot_be_silently_substituted(self):
        report=evidence.load(evidence.ROOT/'packages/conversation-integration/tests/android-sdk-capture-results.json')
        evidence.validate_report(report,sdk=True)
        with self.assertRaises(ValueError):evidence.validate_report(report)
        report['speech_sink']='SYNTHETIC_NO_SDK'
        with self.assertRaises(ValueError):evidence.validate_report(report,sdk=True)
    def test_emulator_and_versioned_symbols(self):
        self.assertEqual(serial('emulator-5554'),'emulator-5554')
        with self.assertRaises(ValueError):serial('physical-phone')
        with self.assertRaises(ValueError):require_ort_symbols('OrtGetApiBase@VERS_1.23.2','OrtGetApiBase@@VERS_1.28.2')
    def test_both_invocation_modes_enforce_apk_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            apk=Path(folder)/'eval.apk'
            with zipfile.ZipFile(apk,'w') as archive:
                for name in LIBRARIES:archive.writestr('lib/arm64-v8a/'+name,b'fixture')
            for probe in ('CaptureReplyInstrumentation','CaptureSdkReplyInstrumentation'):
                with patch('check_capture_android.run',side_effect=['package: com.eilo',probe]):inspect_apk(apk,Path('aapt'),True,probe)
                with patch('check_capture_android.run',return_value='android.permission.RECORD_AUDIO'):
                    with self.assertRaises(ValueError):inspect_apk(apk,Path('aapt'),True,probe)
                with patch('check_capture_android.run',side_effect=['package: com.eilo','WrongInstrumentation']):
                    with self.assertRaises(ValueError):inspect_apk(apk,Path('aapt'),True,probe)
    def test_scope_and_permissions_must_not_be_promoted(self):
        for key,value in [('physical','PASS'),('production','ENABLED'),('speech_sink','ACTUAL_SDK'),('confidence','CALIBRATED'),
                          ('microphone','USED'),('network_acceptance','PASS'),('controller_permission_and_readiness','REAL'),
                          ('temporary_files_removed',False),('normal_app_restored',False),('internet_permission','PRESENT'),
                          ('microphone_permission','PRESENT'),('android_api',True),('transcript','unexpected')]:
            report=self.report();report[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):evidence.validate_report(report)
    def test_cases_counts_and_transcript_digest(self):
        for index,key,value in [(0,'llm_starts',0),(1,'context_messages',2),(2,'recognized',1),(2,'llm_starts',1),
                                (0,'normalized_samples',0),(1,'transcript_sha256','b'*64),(2,'reply_submitted',True),
                                (0,'clauses',0),(1,'worker_verified',False),(0,'recognized',True),(0,'raw_text','unexpected')]:
            report=self.report();report['cases'][index][key]=value
            with self.subTest(index=index,key=key),self.assertRaises(ValueError):evidence.validate_report(report)
        for cases in ([],self.report()['cases'][:2],list(reversed(self.report()['cases']))):
            report=self.report();report['cases']=cases
            with self.assertRaises(ValueError):evidence.validate_report(report)
    def test_model_vendor_and_build_changes(self):
        for kind in ('model','runtime','vendor','source-model','conversion','cpu','permission','library','conversion-bytes'):
            report=self.report()
            if kind=='model':report['llm']['model']['sha256']='a'*64
            elif kind=='runtime':report['llm']['runtime_commit']='a'*40
            elif kind=='vendor':report['library_sha256']['libonnxruntime.so']='a'*64
            elif kind=='source-model':report['vad_source_model_sha256']='a'*64
            elif kind=='conversion':report['vad_conversion']['optimization']='ENABLED'
            elif kind=='conversion-bytes':report['vad_conversion']['bytes']=True
            elif kind=='cpu':report['llm']['cpu_options']['GGML_CUDA']='ON'
            elif kind=='permission':report['controller_permission_and_readiness']='REAL'
            else:report['library_sha256']['extra.so']='a'*64
            with self.subTest(kind=kind),self.assertRaises(ValueError):evidence.validate_report(report)
    def test_ambiguous_and_oversize_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'report.json'
            for raw in ('{"physical":"PASS","physical":"NOT_RUN"}',' '*524289):
                path.write_text(raw)
                with self.assertRaises(ValueError):evidence.load(path)


if __name__=='__main__':unittest.main()
