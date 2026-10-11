import json
import unittest
from trial_summary import HERE,summarize

class WakeTrialSummaryTests(unittest.TestCase):
    def test_frozen_scores_do_not_manufacture_physical_hours(self):
        report=json.loads((HERE/'tests/android-device-results.json').read_text())
        manifest=json.loads((HERE/'tests/fixtures/manifest.json').read_text())
        value=summarize(report,manifest)
        self.assertEqual((value['positive_cases'],value['negative_cases'],value['excluded_diagnostics']),(11,15,2))
        self.assertIsNone(value['physical_false_activations_per_hour'])
        self.assertEqual(value['physical_8h_ambient'],'NOT RUN')
        report['cases'].pop()
        with self.assertRaises(ValueError):summarize(report,manifest)

    def test_multiple_activations_are_visible_and_noninteger_counts_rejected(self):
        manifest={'fixtures':[{'file':'wake.wav','kind':'wake','sha256':'synthetic'}]}
        report={'cases':[{'file':'wake.wav','kind':'wake','detections':2}]}
        self.assertEqual(summarize(report,manifest)['multiple_positive_cases'],1)
        report['cases'][0]['detections']=True
        with self.assertRaises(ValueError):summarize(report,manifest)

if __name__=='__main__':unittest.main()
