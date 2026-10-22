import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from acceptance import CASES, evaluate, load


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.matrix = {'schema': 1, 'sprint': 'S16', 'owner_approved_devices': False,
                       'devices': [], 'results': []}

    def device(self, alias='lab-ios', platform='ios'):
        return {'alias': alias, 'platform': platform, 'model_family': 'lab-fixture',
                'os_version': '27.0', 'build_sha256': 'a' * 64, 'physical': True}

    def populated(self):
        # Synthetic metadata/artifacts test the inventory, never a real-device claim.
        m = copy.deepcopy(self.matrix)
        m['owner_approved_devices'] = True
        m['devices'] = [self.device(), self.device('lab-android', 'android')]
        (self.root / 'evidence').mkdir(exist_ok=True)
        for d in m['devices']:
            for case, platforms in CASES.items():
                if d['platform'] not in platforms:
                    continue
                name = f"evidence/{d['alias']}-{case}.json"
                raw = json.dumps({'synthetic': True, 'case': case}).encode()
                (self.root / name).write_bytes(raw)
                m['results'].append({'device': d['alias'], 'case': case, 'status': 'PASS',
                                     'evidence': {'path': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                                                  'build_sha256': d['build_sha256'], 'reviewed_by_owner': True}})
        return m

    def test_empty_and_missing_matrix_hold(self):
        self.assertEqual(evaluate(self.matrix, self.root)['decision'], 'HOLD')
        self.matrix['devices'] = [self.device()]
        r = evaluate(self.matrix, self.root)
        self.assertGreater(r['missing_cases'], 0)
        self.assertEqual(r['decision'], 'HOLD')

    def test_complete_inventory_requires_manual_review(self):
        r = evaluate(self.populated(), self.root)
        self.assertEqual(r['decision'], 'READY_FOR_MANUAL_ACCEPTANCE_REVIEW')
        self.assertEqual(r['physical_acceptance'], 'NOT_ESTABLISHED_BY_THIS_TOOL')
        self.assertEqual(r['s08_decision'], 'HOLD')
        self.assertFalse(r['persistent_memory_allowed'])

    def test_nonpass_and_unapproved_never_ready(self):
        m = self.populated()
        m['owner_approved_devices'] = False
        self.assertEqual(evaluate(m, self.root)['decision'], 'HOLD')
        m['owner_approved_devices'] = True
        for status in ('FAIL', 'UNSUPPORTED', 'BLOCKED', 'NOT_RUN'):
            n = copy.deepcopy(m)
            n['results'][0]['status'] = status
            if status in ('BLOCKED', 'NOT_RUN'):
                n['results'][0]['evidence'] = None
            self.assertEqual(evaluate(n, self.root)['decision'], 'HOLD')

    def test_duplicate_unknown_platform_and_simulator_reject(self):
        for mutate in (
            lambda m: m['devices'].append(copy.deepcopy(m['devices'][0])),
            lambda m: m['results'].append(copy.deepcopy(m['results'][0])),
            lambda m: m['devices'][0].update(physical=False),
            lambda m: m['results'][0].update(device='unknown'),
            lambda m: m['results'][0].update(case='unknown'),
            lambda m: m['devices'][0].update(platform='unknown'),
            lambda m: m.update(extra='private-marker'),
        ):
            m = self.populated()
            mutate(m)
            with self.assertRaises(ValueError):
                evaluate(m, self.root)

    def test_evidence_review_build_integrity_and_paths(self):
        for mutate in (
            lambda e: e.update(reviewed_by_owner=False),
            lambda e: e.update(build_sha256='b' * 64),
            lambda e: e.update(sha256='b' * 64),
            lambda e: e.update(path='../private.json'),
            lambda e: e.update(path='/private.json'),
            lambda e: e.update(path='evidence/private.json?query=secret'),
        ):
            m = self.populated()
            mutate(m['results'][0]['evidence'])
            with self.assertRaises(ValueError):
                evaluate(m, self.root)
        m = self.populated()
        p = self.root / m['results'][0]['evidence']['path']
        p.unlink()
        p.symlink_to(self.root / m['results'][1]['evidence']['path'])
        with self.assertRaises(ValueError):
            evaluate(m, self.root)

    def test_all_devices_required_and_platform_cases_reject(self):
        m = self.populated()
        m['devices'].append(self.device('lab-ios-two'))
        result = evaluate(m, self.root)
        self.assertGreater(result['missing_cases'], 0)
        self.assertEqual(result['decision'], 'HOLD')
        m = self.populated()
        row = m['results'][0]
        row['case'] = 'overlay-touch-back-insets-native-stop'
        with self.assertRaises(ValueError):
            evaluate(m, self.root)
        m = self.populated()
        row = m['results'][0]
        path = self.root / row['evidence']['path']
        path.write_bytes(b'not-json')
        row['evidence']['sha256'] = hashlib.sha256(b'not-json').hexdigest()
        with self.assertRaises(ValueError):
            evaluate(m, self.root)

    def test_duplicate_json_oversize_and_bad_boolean(self):
        path = self.root / 'matrix.json'
        for raw in (b'{"schema":1,"schema":1}', b' ' * 131073):
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                load(path)
        self.matrix['owner_approved_devices'] = 1
        with self.assertRaises(ValueError):
            evaluate(self.matrix, self.root)

    def test_cli_hold_and_invalid_redaction(self):
        script = Path(__file__).with_name('acceptance.py')
        path = self.root / 'matrix.json'
        path.write_text(json.dumps(self.matrix))
        run = subprocess.run([sys.executable, str(script), str(path), '--require-ready'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(json.loads(run.stdout)['decision'], 'HOLD')
        path.write_text('{"private-marker":')
        run = subprocess.run([sys.executable, str(script), str(path)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertNotIn('private-marker', run.stdout + run.stderr)


if __name__ == '__main__':
    unittest.main()
