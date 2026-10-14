"""Synthetic WAV/schema regression fixtures. Never physical measurements."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
import wave

from measure import PLAN_PATH, digest, quantile, summarize


class AcousticEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.plan = json.loads(PLAN_PATH.read_text())
        cls.manifest = {'schema': 1, 'plan_sha256': digest(PLAN_PATH), 'frozen_before_collection': True, 'fixtures': []}
        samples = []
        for i, planned in enumerate(cls.plan['schedule']):
            # Unique PCM fixtures, no meaningful speech. Used only to test arithmetic.
            path = cls.root / (planned['id'] + '.wav')
            with wave.open(str(path), 'wb') as audio:
                audio.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
                audio.writeframes(struct.pack('<h', i) + b'\0' * (32000 - 2))
            record = {'file': path.name, 'sha256': digest(path)}
            cls.manifest['fixtures'].append({'id': planned['id'], 'question_index': planned['question_index'], 'audio': record})
            samples.append({'id': planned['id'], 'condition': planned['condition'], 'outcome': 'REPLY', 'recording': record, 'cold_reset_verified': i < 20, 'annotation': {'method': 'independent_same_recording_acoustic_frames', 'reviewer': 'Gemju Sherpa', 'user_speech_end_frame': 1000, 'first_meaningful_reply_frame': 9000, 'filler_excluded': True, 'timeout_observed': False}})
        manifest = cls.root / 'corpus.json'
        manifest.write_text(json.dumps(cls.manifest))
        cls.row = {'id': 'synthetic-ios', 'platform': 'iOS', 'status': 'ANNOTATED', 'plan_sha256': digest(PLAN_PATH), 'configuration': {'hardware_kind': 'physical', 'hardware_model': 'SYNTHETIC schema fixture', 'os_build': 'fixture', 'route': 'fixture speaker', 'runtime_revision': 'fixture', 'model_sha256': 'a' * 64, 'voice_id': 'fixture', 'network_observation': 'NO_TRAFFIC_VERIFIED', 'airplane_mode': True, 'wifi_enabled': False, 'cold_method': 'fresh_process_models_unloaded', 'pipeline': 'native_microphone_wake_vad_asr_llm_policy_tts'}, 'corpus': {'file': manifest.name, 'sha256': digest(manifest)}, 'samples': samples}
        cls.base = {'schema': 1, 'task': 'VC-VERIFY-02', 'configurations': [cls.row, {'id': 'android', 'platform': 'Android', 'status': 'NOT_RUN', 'reason': 'synthetic fixture', 'samples': []}]}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def report(self):
        return copy.deepcopy(self.base)

    def reject(self, edit):
        report = self.report()
        edit(report['configurations'][0])
        with self.assertRaises(ValueError):
            summarize(report, self.root)

    def test_complete_synthetic_arithmetic(self):
        result = summarize(self.report(), self.root)
        row = result['configurations'][0]
        self.assertEqual(row['cold']['attempted'], 20)
        self.assertEqual(row['warm']['attempted'], 80)
        self.assertEqual(row['overall']['median_ms'], 1000)
        self.assertEqual(row['overall']['p95_ms'], 1000)
        self.assertEqual(row['overall']['target'], 'PASS')
        self.assertEqual(result['physical_acceptance'], 'REVIEW_REQUIRED')
        self.assertIsNone(result['configurations'][1]['overall'])

    def test_nearest_rank_is_not_interpolation_or_averaging(self):
        self.assertEqual(quantile(list(range(1, 101)), .95), 95)
        self.assertEqual(quantile([1, 3], .5), 1)
        self.assertIsNone(quantile([], .95))

    def test_failure_not_dropped_to_improve_target(self):
        report = self.report()
        sample = report['configurations'][0]['samples'][0]
        sample['outcome'] = 'FAILED'
        sample['annotation']['first_meaningful_reply_frame'] = None
        row = summarize(report, self.root)['configurations'][0]
        self.assertEqual(row['cold']['target'], 'FAIL')
        self.assertEqual(row['overall']['non_replies'], 1)
        self.assertEqual(row['non_reply_outcomes']['FAILED'], 1)
        self.assertEqual(row['warm']['target'], 'PASS')

    def test_slow_cold_not_hidden_in_warm_aggregate(self):
        report = self.report()
        for sample in report['configurations'][0]['samples'][:20]:
            sample['annotation']['first_meaningful_reply_frame'] = 15000
        row = summarize(report, self.root)['configurations'][0]
        self.assertEqual(row['cold']['median_ms'], 1750)
        self.assertEqual(row['cold']['target'], 'FAIL')
        self.assertEqual(row['warm']['target'], 'PASS')
        self.assertEqual(row['configuration_target'], 'FAIL')

    def test_unrun_cannot_carry_measurements(self):
        report = self.report()
        report['configurations'][1]['samples'] = [1]
        with self.assertRaises(ValueError):
            summarize(report, self.root)
        report['configurations'][1]['samples'] = []
        report['configurations'][1]['median_ms'] = 0
        with self.assertRaises(ValueError):
            summarize(report, self.root)

    def test_platform_cannot_silently_disappear(self):
        report = self.report()
        report['configurations'].pop()
        with self.assertRaises(ValueError):
            summarize(report, self.root)

    def test_duplicate_config(self):
        report = self.report()
        report['configurations'][1]['id'] = 'synthetic-ios'
        with self.assertRaises(ValueError):
            summarize(report, self.root)

    def test_no_simulator_or_scripted_input(self):
        self.reject(lambda r: r['configuration'].update(hardware_kind='simulator'))
        self.reject(lambda r: r['configuration'].update(pipeline='recorded_pcm_scripted_endpoint'))

    def test_no_sdk_timestamp_or_filler(self):
        self.reject(lambda r: r['samples'][0]['annotation'].update(method='SDK_onStart'))
        self.reject(lambda r: r['samples'][0]['annotation'].update(filler_excluded=False))

    def test_frames_must_be_int_in_range_and_ordered(self):
        for value in [True, -1, 1.5, 16000, float('nan'), float('inf')]:
            self.reject(lambda r: r['samples'][0]['annotation'].update(user_speech_end_frame=value))
        for value in [True, -1, 9000.0, 999, 16000, None]:
            self.reject(lambda r: r['samples'][0]['annotation'].update(first_meaningful_reply_frame=value))

    def test_all_attempts_and_conditions_required(self):
        self.reject(lambda r: r['samples'].pop())
        self.reject(lambda r: r['samples'][0].update(condition='warm'))
        self.reject(lambda r: r['samples'][0].update(cold_reset_verified=False))

    def test_missing_or_repeated_recording(self):
        self.reject(lambda r: r['samples'][0]['recording'].update(file='missing.wav'))
        self.reject(lambda r: r['samples'][1].update(recording=r['samples'][0]['recording']))

    def test_checksum_and_frozen_plan(self):
        self.reject(lambda r: r.update(plan_sha256='b' * 64))
        self.reject(lambda r: r['samples'][0]['recording'].update(sha256='b' * 64))
        self.reject(lambda r: r['corpus'].update(sha256='b' * 64))

    def test_local_paths_only_no_symlinks(self):
        for name in ['../turn-001.wav', '/tmp/turn-001.wav', './turn-001.wav', 'a\\b.wav']:
            self.reject(lambda r: r['samples'][0]['recording'].update(file=name))
        link = self.root / 'linked.wav'
        link.symlink_to(self.root / 'turn-001.wav')
        try:
            self.reject(lambda r: r['samples'][0]['recording'].update(file=link.name))
        finally:
            link.unlink()

    def test_offline_and_exact_voice_evidence(self):
        self.reject(lambda r: r['configuration'].update(wifi_enabled=True))
        self.reject(lambda r: r['configuration'].update(network_observation='NOT_OBSERVED'))
        self.reject(lambda r: r['configuration'].update(voice_id=''))
        self.reject(lambda r: r['configuration'].update(model_sha256='unknown'))

    def test_failure_cannot_have_latency_and_short_timeout_rejected(self):
        self.reject(lambda r: r['samples'][0].update(outcome='FAILED'))
        def short_timeout(row):
            row['samples'][0]['outcome'] = 'TIMEOUT'
            row['samples'][0]['annotation'].update(first_meaningful_reply_frame=None, timeout_observed=True)
        self.reject(short_timeout)

    def test_long_timeout_counts_as_failure(self):
        path = self.root / 'timeout.wav'
        with wave.open(str(path), 'wb') as audio:
            audio.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
            audio.writeframes(b'\0' * (8000 * 31 * 2))
        report = self.report()
        sample = report['configurations'][0]['samples'][0]
        sample.update(outcome='TIMEOUT', recording={'file': path.name, 'sha256': digest(path)})
        sample['annotation'].update(first_meaningful_reply_frame=None, timeout_observed=True)
        row = summarize(report, self.root)['configurations'][0]
        self.assertEqual(row['overall']['target'], 'FAIL')
        self.assertEqual(row['non_reply_outcomes']['TIMEOUT'], 1)

    def test_truncated_wave_rejected_even_with_matching_hash(self):
        source = self.root / 'turn-001.wav'
        truncated = self.root / 'truncated.wav'
        truncated.write_bytes(source.read_bytes()[:-2])
        self.reject(lambda r: r['samples'][0].update(recording={'file': truncated.name, 'sha256': digest(truncated)}))

    def test_no_unplanned_transcript_or_user_data_fields(self):
        self.reject(lambda r: r['samples'][0].update(transcript='not allowed'))

    def test_corpus_is_frozen_before_collection(self):
        manifest = copy.deepcopy(self.manifest)
        manifest['frozen_before_collection'] = False
        path = self.root / 'not-frozen.json'
        path.write_text(json.dumps(manifest))
        self.reject(lambda r: r.update(corpus={'file': path.name, 'sha256': digest(path)}))


if __name__ == '__main__':
    unittest.main()
