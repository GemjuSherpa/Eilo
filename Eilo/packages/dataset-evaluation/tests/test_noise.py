import copy
import math
import unittest
from benchmark import report
from noise import compare, mix
from test_benchmark import fixture


class NoiseTests(unittest.TestCase):
    def test_seed_snr_and_headroom(self):
        clean = [int(30000 * math.sin(i * 0.1)) for i in range(1600)]
        noise = [10000, -10000, 5000, -5000, 2000, -2000, 1000]
        for snr in (20, 10, 0, -10):
            a, metadata = mix(clean, noise, snr, 3)
            self.assertEqual((a, metadata), mix(clean, noise, snr, 3))
            self.assertLessEqual(max(abs(x) for x in a), 32767)
            self.assertAlmostEqual(metadata['achieved_snr_db'], snr, delta=0.5)
        self.assertNotEqual(mix(clean, noise, 0, 3)[0], mix(clean, noise, 0, 1)[0])

    def test_silent_and_nonfinite_inputs_rejected(self):
        for clean, noise, snr in [([0], [1], 0), ([1], [0], 0), ([1], [1], float('nan')),
                                  ([], [1], 0), ([1], [1], 100)]:
            with self.assertRaises(ValueError): mix(clean, noise, snr)

    def test_regression_threshold_and_slice(self):
        manifest, value = fixture()
        baseline = report(manifest, value)
        value['cases'][0]['transcript'] = 'no go'
        current = report(manifest, value)
        result = compare(baseline, current, {'wer': 0.1})
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(len(result['changes']), 2)
        self.assertEqual(compare(baseline, baseline, {'wer': 0})['status'], 'PASS')
        self.assertEqual(compare(baseline, current, {'wer': 0.5})['status'], 'PASS')

    def test_incomparable_or_forged_baseline(self):
        manifest, value = fixture()
        baseline = report(manifest, value)
        for mutation in ('manifest_sha256', 'status', 'metrics', 'physical_gates'):
            current = copy.deepcopy(baseline)
            current[mutation] = 'bad'
            with self.assertRaises((ValueError, TypeError)):
                compare(baseline, current, {'wer': 0})
        with self.assertRaises(ValueError): compare(baseline, baseline, {'missing': 0})
        with self.assertRaises(ValueError): compare(baseline, baseline, {'wer': -1})
