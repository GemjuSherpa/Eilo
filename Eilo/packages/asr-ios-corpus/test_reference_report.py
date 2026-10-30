"""Aggregate iOS reference reports reject qualification claims and altered evidence."""
import json
from pathlib import Path
import tempfile
import unittest

import reference_report as report


HERE = Path(__file__).resolve().parent


class ReferenceReportTests(unittest.TestCase):
    def current(self):
        return json.loads((HERE / 'ios-reference-results.json').read_text())

    def reject(self, change):
        value = self.current()
        change(value)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            report.validate(value, HERE / 'protocol.json')

    def test_actual_evidence_stays_diagnostic(self):
        summary = report.validate(self.current(), HERE / 'protocol.json')
        self.assertEqual(summary['status'], 'DIAGNOSTIC_ONLY')
        self.assertEqual(summary['clean_and_noise_rows'], 14)
        self.assertEqual(summary['negative_groups'], 6)
        self.assertEqual(summary['available_scores_by_source'], {
            'GREEDY_PREBIAS_MEAN_V1': 203, 'SELF_DRAFT_PREBIAS_MEAN_V1': 203})
        self.assertEqual(summary['physical'], 'NOT_RUN')
        self.assertEqual(summary['release'], 'HOLD')

    def test_qualification_flags_and_protocol_are_fixed(self):
        self.reject(lambda value: value.update(schema_version=True))
        for key in report.FLAGS:
            self.reject(lambda value, key=key: value.update({key: 'PASS'}))
        self.reject(lambda value: value.update(threshold='AUTHORIZED'))
        self.reject(lambda value: value.update(calibration='ESTABLISHED'))
        self.reject(lambda value: value['source_pins'].pop())
        self.reject(lambda value: value['clean'][0]['reports'][0]['metrics'].update(available=30))

    def test_negative_control_denominators_and_group_identity_are_closed(self):
        self.reject(lambda value: value['negative'][0].update(available=1))
        self.reject(lambda value: value['negative'][0].update(group='speech'))
        self.reject(lambda value: value['noise'][0].update(group='independent_noise'))

    def test_export_contains_only_aggregate_rows_and_no_private_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'report'
            report.export(self.current(), target, HERE / 'protocol.json')
            value = json.loads((target / 'summary.json').read_text())
            self.assertEqual(len(value['rows']), 14)
            self.assertNotIn('source_pins', value)
            self.assertNotIn('binary_sha256', value)
            self.assertNotIn('private_counts_sha256', value)
            self.assertNotIn('case_id', json.dumps(value))
            self.assertIn('previously exposed', (target / 'summary.html').read_text().lower())

    def test_duplicate_json_members_and_nonfinite_values_reject(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'invalid.json'
            for content in ('{"schema_version":1,"schema_version":1}', '{"value":NaN}'):
                path.write_text(content)
                with self.assertRaises(ValueError):
                    report.read(path)


if __name__ == '__main__':
    unittest.main()
