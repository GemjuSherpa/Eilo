import copy
import unittest
from baseline import candidate, check
from benchmark import aggregate, report
from test_benchmark import fixture


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.manifest, self.predictions = fixture('commands')
        self.baseline = report(self.manifest, self.predictions)
        self.lock = candidate(self.manifest, self.baseline, {'wer': 0})

    def test_locked_repeat_and_regression(self):
        self.assertEqual(check(self.lock, self.manifest, self.baseline, self.baseline)['status'], 'PASS')
        self.predictions['cases'][0]['transcript'] = 'wrong words here'
        current = report(self.manifest, self.predictions)
        self.assertEqual(check(self.lock, self.manifest, self.baseline, current)['status'], 'FAIL')

    def test_tampered_lock_and_baseline(self):
        for field in ('report_sha256', 'manifest_sha256', 'tolerances_sha256', 'review_status'):
            lock = copy.deepcopy(self.lock)
            lock[field] = 'changed'
            with self.assertRaises(ValueError):
                check(lock, self.manifest, self.baseline, self.baseline)

    def test_recomputed_metrics_cannot_hide_changed_case_identity(self):
        for field, value in [('id', 'wrong'), ('slice', 'wrong'), ('task', 'asr'),
                             ('reference_words', 99), ('audio_seconds', 2),
                             ('confusion', ['no', 'yes']), ('correct', 0)]:
            current = copy.deepcopy(self.baseline)
            current['cases'][0][field] = value
            current['metrics'] = aggregate(current['cases'])
            current['slices'] = {current['cases'][0]['slice']: current['metrics']}
            with self.assertRaises(ValueError):
                check(self.lock, self.manifest, self.baseline, current)
