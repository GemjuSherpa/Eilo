"""Synthetic eight-hour traces. No real standby experiment."""
import copy
import json
import unittest
import test_screen_off as fixtures
from measure import digest
from standby import PLAN, summarize


class StandbyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.ScreenOffTests.setUpClass()
        base = copy.deepcopy(fixtures.ScreenOffTests.base); base['task'] = 'VC-GATE-03'
        row = base['configurations'][0]; row.pop('turns'); row['plan_sha256'] = digest(PLAN)
        row['resources'] = [{'minute': m, 'elapsed_seconds': m * 60, 'battery_percent': 100 - m / 60, 'charging': False, 'rss_bytes': 1_000_000, 'thermal_state': 'nominal', 'screen_off': True, 'capture_available': True} for m in range(481)]
        row.update(ambient_corpus_sha256='d' * 64, directed_wakes=[{'id': e['id'], 'scheduled_seconds': e['seconds'], 'observed_seconds': e['seconds'], 'detected': True} for e in json.loads(PLAN.read_text())['directed_wakes']], false_activations=[], activation_count=100, no_automatic_revival_observed=True, reviewer='Gemju Sherpa')
        cls.base = base

    @classmethod
    def tearDownClass(cls): fixtures.ScreenOffTests.tearDownClass()

    def test_complete_synthetic_trace_still_requires_review(self):
        r = summarize(self.base); m = r['configurations'][0]['metrics']
        self.assertEqual(m['target'], 'PASS'); self.assertEqual(m['battery_points_per_hour'], 1)
        self.assertEqual(r['physical_acceptance'], 'REVIEW_REQUIRED')

    def test_misses_false_triggers_gap_and_revival_fail(self):
        for kind in ['misses', 'false', 'capture', 'revival', 'battery']:
            report = copy.deepcopy(self.base); row = report['configurations'][0]
            if kind == 'misses':
                for wake in row['directed_wakes'][:6]: wake['detected'] = False
                row['activation_count'] = 94
            elif kind == 'false': row.update(false_activations=[{'elapsed_seconds': 1}, {'elapsed_seconds': 2}], activation_count=102)
            elif kind == 'capture': row['resources'][240]['capture_available'] = False
            elif kind == 'revival': row['no_automatic_revival_observed'] = False
            else:
                for resource in row['resources']: resource['battery_percent'] = 100 - resource['minute'] / 15
            self.assertEqual(summarize(report)['configurations'][0]['metrics']['target'], 'FAIL')

    def test_invalid_evidence_rejected(self):
        edits = [lambda r: r['resources'].pop(), lambda r: r['directed_wakes'].pop(), lambda r: r.update(activation_count=101), lambda r: r['configuration'].update(hardware_kind='simulator'), lambda r: r['resources'][1].update(screen_off=False), lambda r: r['resources'][1].update(charging=True), lambda r: r['resources'][1].update(battery_percent=float('inf')), lambda r: r['directed_wakes'][0].update(observed_seconds=0), lambda r: r['background_evidence'].update(permitted_execution_verified=False), lambda r: r.update(ambient_corpus_sha256='missing')]
        for edit in edits:
            report = copy.deepcopy(self.base); edit(report['configurations'][0])
            with self.assertRaises(ValueError): summarize(report)

    def test_incomplete_run_and_unrun_cannot_be_passes(self):
        report = copy.deepcopy(self.base); report['configurations'][0] = {'id': 'ios', 'platform': 'iOS', 'status': 'INCOMPLETE', 'reason': 'process killed', 'observed_seconds': 600}
        self.assertEqual(summarize(report)['configurations'][0]['target'], 'FAIL')
        report['configurations'][1]['detected'] = 100
        with self.assertRaises(ValueError): summarize(report)


if __name__ == '__main__': unittest.main()
