"""Pending reports cannot manufacture acceptance or hide missing gates."""
import copy
import json
import unittest
from decision import EILO, validate


class DecisionTests(unittest.TestCase):
    def setUp(self): self.base = json.loads((EILO / 'docs/sprints/S08_FEASIBILITY_DECISION.json').read_text())

    def test_actual_pending_matrix_is_not_acceptance(self):
        r = validate(self.base); self.assertEqual(r['supported_configurations'], []); self.assertFalse(r['persistent_memory_allowed']); self.assertEqual(r['physical_acceptance'], 'NOT_ESTABLISHED')

    def test_no_approval_or_scope_inferred(self):
        for edit in [lambda r: r.update(persistent_memory_allowed=True), lambda r: r.update(supported_configurations=['iOS']), lambda r: r.update(review_state='APPROVED'), lambda r: r.update(recommendation='GO')]:
            r = copy.deepcopy(self.base); edit(r)
            with self.assertRaises(ValueError): validate(r)

    def test_physical_pass_cannot_be_inferred_from_prior_protocol(self):
        r = copy.deepcopy(self.base); r['platforms'][0]['gates'][0].update(physical_status='PASS', evidence_kind='physical')
        with self.assertRaises(ValueError): validate(r)
        r = copy.deepcopy(self.base); r['platforms'][0]['gates'][0].update(physical_status='FAIL', evidence_kind='policy_observation')
        with self.assertRaises(ValueError): validate(r)

    def test_platforms_and_all_dependencies_required(self):
        r = copy.deepcopy(self.base); r['platforms'].pop()
        with self.assertRaises(ValueError): validate(r)
        r = copy.deepcopy(self.base); r['platforms'][0]['gates'].pop()
        with self.assertRaises(ValueError): validate(r)
        r = copy.deepcopy(self.base); r['platforms'][0]['gates'][0] = 1
        with self.assertRaises(ValueError): validate(r)

    def test_stale_hash_and_missing_path_rejected(self):
        for edit in [lambda r: r['platforms'][0]['gates'][0].update(sha256='0' * 64), lambda r: r['policy_observations'][0].update(artifact='../AGENTS.md'), lambda r: r['policy_observations'][0].update(sha256='0' * 64)]:
            r = copy.deepcopy(self.base); edit(r)
            with self.assertRaises(ValueError): validate(r)

    def test_unknown_personal_fields_and_metrics_rejected(self):
        r = copy.deepcopy(self.base); r['platforms'][0]['gates'][0]['latency_ms'] = 0
        with self.assertRaises(ValueError): validate(r)
        r = copy.deepcopy(self.base); r['device_serial'] = 'not allowed'
        with self.assertRaises(ValueError): validate(r)


if __name__ == '__main__': unittest.main()
