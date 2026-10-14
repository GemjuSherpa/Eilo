"""Synthetic resource/acoustic evidence. No physical hour is executed."""
import copy
import unittest
import test_measure as fixtures
from endurance import PLAN, summarize
from measure import digest


class EnduranceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.AcousticEvidenceTests.setUpClass(); cls.root = fixtures.AcousticEvidenceTests.root
        config = {'hardware_kind': 'physical', 'hardware_model': 'SYNTHETIC fixture', 'os_build': 'fixture', 'route': 'fixture', 'runtime_revision': 'fixture', 'model_sha256': 'a' * 64, 'voice_id': 'fixture', 'workload_frozen_before_collection': True, 'native_pipeline_verified': True, 'offline_verified': True, 'resource_trace_sha256': 'b' * 64, 'peak_rss_bytes': 1_000_000, 'pack_bytes': 1_000_000, 'thermal_shutdown': False, 'crashed': False, 'capture_continuity_verified': True, 'resource_measurement_method': 'native_process_peak_rss_and_battery_trace'}
        rows = [{'minute': m, 'elapsed_seconds': m * 60, 'battery_percent': 100 - m / 12, 'charging': False, 'rss_bytes': 1_000_000, 'thermal_state': 'nominal', 'screen_off': False, 'capture_available': True} for m in range(61)]
        turns = [{'minute': m, 'scheduled_seconds': m * 60, 'started_seconds': m * 60, 'question_index': m % 10, 'outcome': 'REPLY', 'recording': copy.deepcopy(fixtures.AcousticEvidenceTests.row['samples'][m]['recording']), 'annotation': {'method': 'independent_same_recording_acoustic_frames', 'reviewer': 'Gemju Sherpa', 'user_speech_end_frame': 1000, 'first_meaningful_reply_frame': 9000, 'filler_excluded': True}} for m in range(60)]
        cls.row = {'id': 'ios', 'platform': 'iOS', 'status': 'ANNOTATED', 'plan_sha256': digest(PLAN), 'configuration': config, 'resources': rows, 'turns': turns}
        cls.base = {'schema': 1, 'task': 'VC-GATE-01', 'configurations': [cls.row, {'id': 'android', 'platform': 'Android', 'status': 'NOT_RUN', 'reason': 'fixture', 'observed_seconds': None}]}

    @classmethod
    def tearDownClass(cls): fixtures.AcousticEvidenceTests.tearDownClass()

    def test_full_arithmetic(self):
        r = summarize(self.base, self.root); metrics = r['configurations'][0]['metrics']
        self.assertEqual(metrics['target'], 'PASS'); self.assertEqual(metrics['battery_points_per_hour'], 5)
        self.assertEqual(metrics['final15_replies'], 15); self.assertEqual(metrics['final15_median_ms'], 1000)
        self.assertEqual(r['physical_acceptance'], 'REVIEW_REQUIRED')

    def test_failed_targets_and_lifecycle_remain_failures(self):
        for edit in [lambda r: r['configuration'].update(peak_rss_bytes=2_500_000_000), lambda r: r['configuration'].update(pack_bytes=2_000_000_000), lambda r: r['configuration'].update(crashed=True), lambda r: r['configuration'].update(thermal_shutdown=True), lambda r: r['configuration'].update(capture_continuity_verified=False), lambda r: r['resources'][30].update(capture_available=False), lambda r: r['turns'][0].update(outcome='FAILED', annotation={**r['turns'][0]['annotation'], 'first_meaningful_reply_frame': None})]:
            report = copy.deepcopy(self.base); edit(report['configurations'][0])
            self.assertEqual(summarize(report, self.root)['configurations'][0]['metrics']['target'], 'FAIL')

    def test_final15_degradation_not_hidden(self):
        report = copy.deepcopy(self.base)
        for turn in report['configurations'][0]['turns'][45:]: turn['annotation']['first_meaningful_reply_frame'] = 15000
        self.assertEqual(summarize(report, self.root)['configurations'][0]['metrics']['target'], 'FAIL')

    def test_invalid_resource_and_acoustic_evidence_rejected(self):
        edits = [lambda r: r['configuration'].update(hardware_kind='simulator'), lambda r: r['resources'].pop(), lambda r: r['resources'][30].update(charging=True), lambda r: r['resources'][30].update(battery_percent=float('nan')), lambda r: r['resources'][0].update(battery_percent=99), lambda r: r['resources'][1].update(elapsed_seconds=1), lambda r: r['resources'][-1].update(elapsed_seconds=3599), lambda r: r['resources'][0].update(screen_off=True), lambda r: r['turns'].pop(), lambda r: r['turns'][0].update(started_seconds=10), lambda r: r['turns'][0]['annotation'].update(method='SDK_onStart'), lambda r: r['turns'][0]['annotation'].update(first_meaningful_reply_frame=True), lambda r: r['configuration'].update(peak_rss_bytes=1), lambda r: r['turns'][0].update(question_index=1)]
        for edit in edits:
            report = copy.deepcopy(self.base); edit(report['configurations'][0])
            with self.assertRaises(ValueError): summarize(report, self.root)

    def test_battery_target(self):
        report = copy.deepcopy(self.base)
        for row in report['configurations'][0]['resources']: row['battery_percent'] = 100 - row['minute'] / 3
        self.assertEqual(summarize(report, self.root)['configurations'][0]['metrics']['target'], 'FAIL')

    def test_incomplete_duration_has_no_fake_metrics(self):
        report = copy.deepcopy(self.base)
        report['configurations'][0] = {'id': 'ios', 'platform': 'iOS', 'status': 'INCOMPLETE', 'reason': 'capture terminated', 'observed_seconds': 30}
        row = summarize(report)['configurations'][0]; self.assertEqual(row['target'], 'FAIL'); self.assertIsNone(row['metrics'])
        report['configurations'][0]['observed_seconds'] = 3600
        with self.assertRaises(ValueError): summarize(report)

    def test_unrun_with_metrics_rejected(self):
        report = copy.deepcopy(self.base); report['configurations'][1]['battery_percent'] = 100
        with self.assertRaises(ValueError): summarize(report, self.root)


if __name__ == '__main__': unittest.main()
