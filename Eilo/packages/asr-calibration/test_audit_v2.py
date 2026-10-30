import unittest

from audit_v2 import SOURCES, evaluate_source, protocol, validate_counts, wilson_lower


class ConfidenceAuditV2Tests(unittest.TestCase):
    def test_protocol_freezes_proposed_sample_and_acceptance_rules(self):
        value = protocol()
        self.assertEqual((value['development_cases'], value['validation_cases'], value['sealed_audit_cases']), (200, 200, 200))
        self.assertEqual(value['validation_rule']['minimum_coverage_of_all_attempts'], 0.30)
        self.assertEqual(value['validation_rule']['minimum_wilson_lower_bound_among_accepted'], 0.85)
        self.assertEqual(value['sources'], list(SOURCES))
        self.assertEqual(value['audio']['recipe'], 'pcm16-mono-area-downsample-linear-upsample-v1')
        self.assertEqual(value['threshold_authorization'], 'NOT_GRANTED')

    def test_wilson_known_values_and_small_sample_conservatism(self):
        self.assertAlmostEqual(wilson_lower(57, 60), 0.8630, places=3)
        self.assertLess(wilson_lower(56, 60), 0.85)
        self.assertGreater(wilson_lower(180, 200), 0.85)

    def test_acceptance_uses_all_attempts_for_coverage(self):
        row = evaluate_source(SOURCES[0], 200, 10, 60, 57)
        self.assertEqual(row['status'], 'PASS')
        self.assertEqual(row['coverage'], 0.30)
        self.assertAlmostEqual(row['wilson_lower_95'], wilson_lower(57, 60))

    def test_unavailable_scores_reduce_coverage_and_never_count_accepted(self):
        row = evaluate_source(SOURCES[0], 200, 141, 59, 57)
        self.assertEqual(row['status'], 'FAIL')
        self.assertEqual(row['coverage'], 0.295)

    def test_incomplete_source_cannot_pass(self):
        row = evaluate_source(SOURCES[0], 199, 0, 199, 199)
        self.assertEqual(row['status'], 'INCOMPLETE')
        self.assertFalse(row['passes'])

    def test_sealed_audit_stage_stays_closed_until_committed_validation_gate_exists(self):
        value = {'schema_version': 1, 'stage': 'SEALED_AUDIT', 'sources': [
            {'source': source, 'attempted': 200, 'unavailable': 0, 'accepted': 60,
             'accepted_correct': 56 if index == 0 else 60}
            for index, source in enumerate(SOURCES)
        ]}
        with self.assertRaisesRegex(ValueError, 'sealed audit execution is not implemented'):
            validate_counts(value)

    def test_stage_requires_exact_sources_and_closed_schema(self):
        value = {'schema_version': 1, 'stage': 'VALIDATION', 'sources': [
            {'source': source, 'attempted': 200, 'unavailable': 0, 'accepted': 60,
             'accepted_correct': 60} for source in SOURCES
        ]}
        value['extra'] = True
        with self.assertRaises(ValueError):
            validate_counts(value)
        value.pop('extra')
        value['sources'].reverse()
        with self.assertRaises(ValueError):
            validate_counts(value)

    def test_source_rows_reject_extra_fields(self):
        value = {'schema_version': 1, 'stage': 'VALIDATION', 'sources': [
            {'source': source, 'attempted': 200, 'unavailable': 0, 'accepted': 60,
             'accepted_correct': 60} for source in SOURCES
        ]}
        value['sources'][0]['raw_score'] = 0.9
        with self.assertRaises(ValueError):
            validate_counts(value)

    def test_public_report_never_claims_release_authority(self):
        value = {'schema_version': 1, 'stage': 'VALIDATION', 'sources': [
            {'source': source, 'attempted': 200, 'unavailable': 0, 'accepted': 60,
             'accepted_correct': 60} for source in SOURCES
        ]}
        report = validate_counts(value)
        self.assertEqual(report['overall'], 'PASS')
        self.assertEqual(report['software_audit_qualification'], 'NOT_ESTABLISHED')
        self.assertEqual(report['threshold_authorization'], 'NOT_GRANTED')
        self.assertEqual(report['production'], 'NOT_ENABLED')
        self.assertEqual(report['physical'], 'NOT_RUN')


if __name__ == '__main__':
    unittest.main()
