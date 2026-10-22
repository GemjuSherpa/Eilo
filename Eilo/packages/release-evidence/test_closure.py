import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from closure import evaluate, parse, read, requirements


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'planning').mkdir()
        self.raw = json.dumps([{'body': '- [ ] **VC-TEST-01 — test**\n  - Requirements: F01, S01\n'}]).encode()
        (self.root / 'planning/sprint-issues.json').write_bytes(self.raw)
        self.ledger = {'schema': 1, 'sprint': 'S17', 'reviewed_main': 'a' * 40,
                       'release_decision': 'HOLD', 's08_decision': 'HOLD',
                       'persistent_memory_allowed': False, 'supported_configurations': [],
                       'sources': {'plan': {'path': 'planning/sprint-issues.json',
                                            'sha256': hashlib.sha256(self.raw).hexdigest(),
                                            'kind': 'SUPPORTING_CONTEXT_NOT_ACCEPTANCE'}},
                       'requirements': [{'id': req, 'tasks': ['VC-TEST-01'],
                                         'full_app_acceptance': 'BLOCKED',
                                         'blocker': 'INTEGRATED_PHYSICAL_ACCEPTANCE',
                                         'supporting_sources': ['plan']} for req in ('F01', 'S01')]}

    def test_valid_pending_never_release(self):
        result = evaluate(self.ledger, self.root)
        self.assertEqual(result['requirements'], 2)
        self.assertEqual(result['blocked_requirements'], 2)
        self.assertEqual(result['release_decision'], 'HOLD')
        self.assertFalse(result['persistent_memory_allowed'])
        self.assertEqual(result['physical_acceptance'], 'NOT_ESTABLISHED')

    def test_forged_pass_release_memory_and_support_reject(self):
        for field, value in [('release_decision', 'PASS'), ('s08_decision', 'PASS'),
                             ('persistent_memory_allowed', True), ('supported_configurations', ['phone'])]:
            ledger = copy.deepcopy(self.ledger)
            ledger[field] = value
            with self.assertRaises(ValueError):
                evaluate(ledger, self.root)
        self.ledger['requirements'][0]['full_app_acceptance'] = 'PASS'
        with self.assertRaises(ValueError):
            evaluate(self.ledger, self.root)

    def test_missing_duplicate_unknown_and_task_mapping_reject(self):
        for change in ('missing', 'duplicate', 'unknown', 'tasks'):
            ledger = copy.deepcopy(self.ledger)
            if change == 'missing':
                ledger['requirements'].pop()
            elif change == 'duplicate':
                ledger['requirements'][1] = copy.deepcopy(ledger['requirements'][0])
            elif change == 'unknown':
                ledger['requirements'][0]['id'] = 'F99'
            else:
                ledger['requirements'][0]['tasks'] = ['VC-OTHER-01']
            with self.assertRaises(ValueError):
                evaluate(ledger, self.root)

    def test_stale_planner_new_requirement_detected(self):
        raw = json.dumps([{'body': '- [ ] **VC-TEST-01**\n  - Requirements: F01, S01, N01\n'}]).encode()
        (self.root / 'planning/sprint-issues.json').write_bytes(raw)
        with self.assertRaises(ValueError):
            evaluate(self.ledger, self.root)
        self.ledger['sources']['plan']['sha256'] = hashlib.sha256(raw).hexdigest()
        with self.assertRaises(ValueError):
            evaluate(self.ledger, self.root)

    def test_source_path_digest_kind_and_symlink_reject(self):
        for field, value in [('path', '../private'), ('path', '/private'),
                             ('path', 'planning/../private'), ('path', 'planning/private?query=x'),
                             ('sha256', 'b' * 64), ('kind', 'ACCEPTED')]:
            ledger = copy.deepcopy(self.ledger)
            ledger['sources']['plan'][field] = value
            with self.assertRaises(ValueError):
                evaluate(ledger, self.root)
        p = self.root / 'planning/sprint-issues.json'
        p.rename(self.root / 'original.json')
        p.symlink_to(self.root / 'original.json')
        with self.assertRaises(ValueError):
            evaluate(self.ledger, self.root)

    def test_unknown_fields_blockers_refs_and_boolean_reject(self):
        for change in ('field', 'blocker', 'refs', 'duplicate-ref', 'schema'):
            ledger = copy.deepcopy(self.ledger)
            if change == 'field':
                ledger['private-marker'] = 'sensitive'
            elif change == 'blocker':
                ledger['requirements'][0]['blocker'] = ''
            elif change == 'refs':
                ledger['requirements'][0]['supporting_sources'] = ['unknown']
            elif change == 'duplicate-ref':
                ledger['requirements'][0]['supporting_sources'] = ['plan', 'plan']
            else:
                ledger['schema'] = True
            with self.assertRaises(ValueError):
                evaluate(ledger, self.root)

    def test_duplicate_keys_oversize_and_invalid_plan_reject(self):
        with self.assertRaises(ValueError):
            parse(b'{"schema":1,"schema":1}')
        p = self.root / 'large.json'
        p.write_bytes(b' ' * 524289)
        with self.assertRaises(ValueError):
            read(p)
        for body in ('  - Requirements: F01', '- [ ] **VC-TEST-01**\n  - Requirements: none',
                     '- [ ] **VC-TEST-01**\n- [ ] **VC-TEST-01**\n  - Requirements: F01'):
            with self.assertRaises(ValueError):
                requirements(json.dumps([{'body': body}]).encode())

    def test_actual_ledger_and_release_exit_redaction(self):
        script = Path(__file__).with_name('closure.py')
        run = subprocess.run([sys.executable, str(script), '--require-release-ready'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        result = json.loads(run.stdout)
        self.assertEqual(result['requirements'], 93)
        self.assertEqual(result['supporting_sources'], 10)
        self.assertEqual(result['release_decision'], 'HOLD')
        p = self.root / 'bad.json'
        p.write_text('{"private-marker":')
        run = subprocess.run([sys.executable, str(script), str(p)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertNotIn('private-marker', run.stdout + run.stderr)


if __name__ == '__main__':
    unittest.main()
