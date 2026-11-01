import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from audit_v2 import SOURCES
from evaluate_validation_v2 import (FREEZE_KINDS, evaluate_validation,
                                    fit_development, freeze_metadata, source_pins,
                                    verify_freeze_commit)
from shared import canonical_digest


class ValidationV2Tests(unittest.TestCase):
    def setUp(self):
        self.case_ids = [f'{index:024x}' for index in range(200)]
        self.cases = [{'id': case_id, 'reference': f'approved reference {index}'}
                      for index, case_id in enumerate(self.case_ids)]
        rows = []
        for case_id in self.case_ids:
            index = int(case_id, 16)
            if index < 10:
                rows.append({'case_id': case_id, 'status': 'UNAVAILABLE'})
            elif index < 140:
                rows.append({'case_id': case_id, 'status': 'AVAILABLE', 'score': 0.1,
                             'hypothesis': f'wrong low-score hypothesis {index}'})
            else:
                rows.append({'case_id': case_id, 'status': 'AVAILABLE', 'score': 0.9,
                             'hypothesis': f'approved reference {index}' if index < 197
                             else f'wrong high-score hypothesis {index}'})
        self.attempts = {'schema_version': 1, 'stage': 'VALIDATION',
                         'case_ids': self.case_ids,
                         'sources': [{'source': source, 'attempts': list(rows)}
                                     for source in SOURCES]}
        self.development_attempts = dict(self.attempts, stage='DEVELOPMENT')
        self.private = fit_development(self.development_attempts, self.cases)
        self.frozen = freeze_metadata(self.private, self.development_attempts, self.cases)

    def test_freeze_contains_hashes_and_no_mapping_knots(self):
        public = freeze_metadata(self.private, self.development_attempts, self.cases)
        self.assertEqual(set(public), FREEZE_KINDS)
        self.assertEqual(public['development_attempts_per_source'], 200)
        self.assertEqual(public['mapping_sha256'], {
            source: canonical_digest(self.private['models'][source]) for source in SOURCES
        })
        self.assertEqual(public['source_pins'], source_pins())
        self.assertNotIn('blocks', json.dumps(public))

    def test_private_model_must_recompute_from_development_only(self):
        altered = json.loads(json.dumps(self.private))
        altered['models'][SOURCES[0]]['blocks'][-1]['correct'] -= 1
        with self.assertRaisesRegex(ValueError, 'not fit from the frozen development attempts'):
            freeze_metadata(altered, self.development_attempts, self.cases)

    def test_validation_pass_emits_aggregate_only_and_keeps_other_gates_closed(self):
        report = evaluate_validation(self.attempts, self.private, self.frozen, self.cases)
        self.assertEqual(report['overall'], 'PASS')
        self.assertEqual([row['accepted'] for row in report['sources']], [60, 60])
        self.assertEqual([row['accepted_correct'] for row in report['sources']], [57, 57])
        self.assertEqual([row['coverage'] for row in report['sources']], [0.3, 0.3])
        self.assertEqual(report['sealed_audit'], 'CLOSED_UNTIL_BOTH_VALIDATION_SOURCES_PASS')
        self.assertEqual(report['threshold_authorization'], 'NOT_GRANTED')
        self.assertEqual(report['production'], 'NOT_ENABLED')
        serialized = json.dumps(report)
        self.assertNotIn(self.case_ids[0], serialized)
        self.assertNotIn('score', serialized)
        self.assertNotIn('approved reference', serialized)

    def test_one_source_failure_cannot_open_sealed_audit(self):
        self.attempts['sources'][1]['attempts'][-4]['hypothesis'] = 'wrong additional high-score case'
        report = evaluate_validation(self.attempts, self.private, self.frozen, self.cases)
        self.assertEqual(report['overall'], 'NOT_QUALIFIED')
        self.assertEqual(report['sources'][1]['status'], 'FAIL')
        self.assertEqual(report['sealed_audit'], 'CLOSED_UNTIL_BOTH_VALIDATION_SOURCES_PASS')

    def test_correctness_uses_frozen_normalization_without_exporting_hypotheses(self):
        self.attempts['sources'][0]['attempts'][140]['hypothesis'] = 'APPROVED REFERENCE 140!!!'
        report = evaluate_validation(self.attempts, self.private, self.frozen, self.cases)
        self.assertEqual(report['sources'][0]['accepted_correct'], 57)
        self.assertNotIn('APPROVED REFERENCE', json.dumps(report))

    def test_manifest_order_and_case_identity_are_required(self):
        with self.assertRaisesRegex(ValueError, 'frozen cohort manifest order'):
            evaluate_validation(self.attempts, self.private, self.frozen,
                                list(reversed(self.cases)))
        self.attempts['sources'][0]['attempts'][0]['case_id'] = self.case_ids[-1]
        with self.assertRaisesRegex(ValueError, 'attempt order differs'):
            evaluate_validation(self.attempts, self.private, self.frozen, self.cases)

    def test_unavailable_attempt_cannot_hide_score_or_label(self):
        self.attempts['sources'][0]['attempts'][0]['score'] = 0.9
        with self.assertRaisesRegex(ValueError, 'unavailable scores cannot include'):
            evaluate_validation(self.attempts, self.private, self.frozen, self.cases)

    def test_mapping_hash_mismatch_and_sealed_stage_fail_closed(self):
        frozen = dict(self.frozen)
        frozen['mapping_sha256'] = dict(frozen['mapping_sha256'])
        frozen['mapping_sha256'][SOURCES[0]] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'do not match the committed freeze'):
            evaluate_validation(self.attempts, self.private, frozen, self.cases)
        sealed = dict(self.attempts, stage='SEALED_AUDIT')
        with self.assertRaisesRegex(ValueError, 'only the frozen validation stage'):
            evaluate_validation(sealed, self.private, self.frozen, self.cases)

    def test_freeze_commit_must_be_ancestor_and_match_exact_blob(self):
        payload = json.dumps(self.frozen, indent=2, sort_keys=True).encode() + b'\n'
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            freeze_path = repository / 'Eilo/packages/asr-calibration/mapping-freeze-v2.json'
            freeze_path.parent.mkdir(parents=True)
            freeze_path.write_bytes(payload)
            with patch('evaluate_validation_v2.subprocess.run') as run, \
                    patch('evaluate_validation_v2.subprocess.check_output', return_value=payload):
                value, digest = verify_freeze_commit(freeze_path, 'a' * 40, repository)
            run.assert_called_once()
            self.assertEqual(value, self.frozen)
            self.assertEqual(len(digest), 64)
            with patch('evaluate_validation_v2.subprocess.run'), \
                    patch('evaluate_validation_v2.subprocess.check_output', return_value=b'{}'):
                with self.assertRaisesRegex(ValueError, 'differs from its committed blob'):
                    verify_freeze_commit(freeze_path, 'a' * 40, repository)


if __name__ == '__main__':
    unittest.main()
