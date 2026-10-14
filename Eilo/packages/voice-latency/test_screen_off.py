"""Synthetic schema tests; no device is locked or background mode enabled."""
import copy
import unittest
import test_endurance as fixtures
from measure import digest
from screen_off import PLAN, summarize


class ScreenOffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.EnduranceTests.setUpClass(); cls.root = fixtures.EnduranceTests.root
        cls.base = copy.deepcopy(fixtures.EnduranceTests.base); cls.base['task'] = 'VC-GATE-02'
        row = cls.base['configurations'][0]; row['plan_sha256'] = digest(PLAN)
        row['background_evidence'] = {'consent_verified': True, 'permitted_execution_verified': True, 'generic_locked_policy_review': 'APPROVED_FOR_GENERIC_AUDIO', 'no_keepalive_workaround': True, 'policy_revision': 'synthetic fixture', 'lifecycle_trace_sha256': 'c' * 64}
        for r in row['resources']: r['screen_off'] = True

    @classmethod
    def tearDownClass(cls): fixtures.EnduranceTests.tearDownClass()

    def test_synthetic_complete_requires_review(self):
        r = summarize(self.base, self.root)
        self.assertEqual(r['configurations'][0]['metrics']['target'], 'PASS')
        self.assertEqual(r['physical_acceptance'], 'REVIEW_REQUIRED')

    def test_permission_policy_keepalive_and_screen_failures(self):
        edits = [lambda r: r['background_evidence'].update(consent_verified=False), lambda r: r['background_evidence'].update(permitted_execution_verified=False), lambda r: r['background_evidence'].update(generic_locked_policy_review='PENDING'), lambda r: r['background_evidence'].update(no_keepalive_workaround=False), lambda r: r['resources'][30].update(screen_off=False), lambda r: r['configuration'].update(hardware_kind='simulator'), lambda r: r.update(plan_sha256='wrong'), lambda r: r['resources'].pop()]
        for edit in edits:
            report = copy.deepcopy(self.base); edit(report['configurations'][0])
            with self.assertRaises(ValueError): summarize(report, self.root)

    def test_stopped_capture_is_failed(self):
        report = copy.deepcopy(self.base); report['configurations'][0]['resources'][1]['capture_available'] = False
        self.assertEqual(summarize(report, self.root)['configurations'][0]['metrics']['target'], 'FAIL')

    def test_short_run_not_relabelled_hour(self):
        report = copy.deepcopy(self.base); report['configurations'][0] = {'id': 'ios', 'platform': 'iOS', 'status': 'INCOMPLETE', 'reason': 'capture stopped on lock', 'observed_seconds': 1}
        r = summarize(report)['configurations'][0]; self.assertEqual(r['target'], 'FAIL'); self.assertIsNone(r['metrics'])


if __name__ == '__main__': unittest.main()
