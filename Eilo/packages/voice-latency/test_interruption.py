"""Synthetic acoustic/schema fixtures, never phone interruption results."""
import copy
import json
import struct
import unittest
import wave
from interruption import PLAN, summarize
from measure import digest
import test_measure as fixtures


class InterruptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.AcousticEvidenceTests.setUpClass()
        cls.root = fixtures.AcousticEvidenceTests.root
        plan = json.loads(PLAN.read_text())
        samples = []
        for index, expected in enumerate(plan['schedule']):
            sample = fixtures.AcousticEvidenceTests.row['samples'][index]
            samples.append({'id': expected['id'], 'clause_position': expected['clause_position'], 'outcome': 'STOPPED', 'recording': copy.deepcopy(sample['recording']), 'annotation': {'method': 'independent_same_recording_acoustic_frames', 'reviewer': 'Gemju Sherpa', 'intelligible_user_onset_frame': 1000, 'last_old_audio_frame': 1800, 'old_audio_resumed': False, 'old_audio_observed_before_onset': True, 'observation_end_frame': 15000}})
        noise = []
        for index, expected in enumerate(plan['noise_controls']):
            path = cls.root / (expected['id'] + '.wav')
            with wave.open(str(path), 'wb') as audio:
                audio.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
                audio.writeframes(struct.pack('<h', index + 1000) + b'\0' * 31998)
            noise.append({'id': expected['id'], 'outcome': 'IGNORED', 'recording': {'file': path.name, 'sha256': digest(path)}, 'reviewer': 'Gemju Sherpa'})
        config = {'hardware_kind': 'physical', 'hardware_model': 'SYNTHETIC fixture', 'os_build': 'fixture', 'route': 'fixture', 'model_sha256': 'a' * 64, 'runtime_revision': 'fixture', 'voice_id': 'fixture', 'native_pipeline_verified': True, 'offline_verified': True, 'input_corpus_sha256': 'b' * 64, 'corpus_frozen_before_collection': True}
        cls.base = {'schema': 1, 'task': 'VC-VERIFY-03', 'configurations': [{'id': 'ios', 'platform': 'iOS', 'status': 'ANNOTATED', 'configuration': config, 'plan_sha256': digest(PLAN), 'samples': samples, 'noise_controls': noise}, {'id': 'android', 'platform': 'Android', 'status': 'NOT_RUN', 'reason': 'fixture', 'samples': [], 'noise_controls': []}]}

    @classmethod
    def tearDownClass(cls):
        fixtures.AcousticEvidenceTests.tearDownClass()

    def test_complete_arithmetic_requires_review(self):
        r = summarize(self.base, self.root)
        self.assertEqual(r['configurations'][0]['p95_ms'], 100)
        self.assertEqual(r['configurations'][0]['target'], 'PASS')
        self.assertEqual(r['physical_acceptance'], 'REVIEW_REQUIRED')

    def test_misses_resumption_and_noise_cannot_improve_p95(self):
        for edit in [lambda r: r['samples'][0].update(outcome='MISSED', annotation={**r['samples'][0]['annotation'], 'last_old_audio_frame': None}), lambda r: r['samples'][0]['annotation'].update(old_audio_resumed=True), lambda r: r['noise_controls'][0].update(outcome='FALSE_TRIGGER')]:
            report = copy.deepcopy(self.base); edit(report['configurations'][0])
            self.assertEqual(summarize(report, self.root)['configurations'][0]['target'], 'FAIL')

    def test_bad_evidence_is_rejected(self):
        edits = [lambda r: r['configuration'].update(hardware_kind='simulator'), lambda r: r['samples'][0]['annotation'].update(method='SDK_stop'), lambda r: r['samples'][0]['annotation'].update(intelligible_user_onset_frame=True), lambda r: r['samples'][0]['annotation'].update(last_old_audio_frame=999), lambda r: r['samples'][0]['annotation'].update(old_audio_observed_before_onset=False), lambda r: r['samples'][0]['annotation'].update(observation_end_frame=1001), lambda r: r['samples'].pop(), lambda r: r['noise_controls'].pop(), lambda r: r['noise_controls'][0].update(recording=r['samples'][0]['recording']), lambda r: r.update(plan_sha256='x'), lambda r: r['configuration'].update(native_pipeline_verified=False), lambda r: r['samples'][0].update(clause_position='unknown')]
        for edit in edits:
            report = copy.deepcopy(self.base); edit(report['configurations'][0])
            with self.assertRaises(ValueError): summarize(report, self.root)

    def test_slow_stop_fails(self):
        report = copy.deepcopy(self.base)
        for sample in report['configurations'][0]['samples']:
            sample['annotation']['last_old_audio_frame'] = 4000
        self.assertEqual(summarize(report, self.root)['configurations'][0]['target'], 'FAIL')

    def test_unrun_cannot_include_numbers_or_samples(self):
        report = copy.deepcopy(self.base); report['configurations'][1]['p95_ms'] = 0
        with self.assertRaises(ValueError): summarize(report, self.root)

    def test_both_platforms_and_unique_configuration(self):
        report = copy.deepcopy(self.base); report['configurations'].pop()
        with self.assertRaises(ValueError): summarize(report, self.root)
        report = copy.deepcopy(self.base); report['configurations'][1]['id'] = 'ios'
        with self.assertRaises(ValueError): summarize(report, self.root)


if __name__ == '__main__': unittest.main()
