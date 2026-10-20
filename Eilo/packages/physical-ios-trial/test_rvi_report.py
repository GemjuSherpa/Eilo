import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from rvi_report import load, render, validate

ROOT = Path(__file__).parent


class RviReportTests(unittest.TestCase):
    def setUp(self):
        self.pre = json.loads((ROOT/'tests/network-rvi-preflight-results.json').read_text())
        self.cal = json.loads((ROOT/'tests/network-rvi-calibration-results.json').read_text())

    def test_actual_evidence_is_blocked_not_zero_traffic(self):
        result = validate(self.pre, self.cal)
        self.assertEqual(result['physical_gate_acceptance'], 'NOT_RUN')
        self.assertIsNone(result['packet_count'])
        self.assertIn('not traffic counts', result['conclusion'])

    def test_no_acceptance_or_metric_promotion(self):
        for key, value in [('packet_count', 0), ('sent_bytes', 0), ('received_bytes', 0),
                           ('network_observation', 'PASS'), ('physical_gate_acceptance', 'PASS'),
                           ('target_attribution', 'ESTABLISHED'), ('schema_version', True)]:
            for index in (0, 1):
                records = [copy.deepcopy(self.pre), copy.deepcopy(self.cal)]
                records[index][key] = value
                with self.subTest(key=key, index=index), self.assertRaises(ValueError):
                    validate(*records)

    def test_cleanup_and_scope_cannot_be_weakened(self):
        for patch in [{'interface_stopped':False}, {'observer_ready':False},
                      {'packet_lines_retained':True}, {'packet_files_created':True},
                      {'inference_started':True}, {'marker_send_result_bytes':-1},
                      {'observer_ready':1}, {'endpoint':'private'}, {'payload':'private'}]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                validate(self.pre, {**self.cal, **patch})
        for patch in [{'rvi_stop':'FAILED'}, {'process_filter_query':'UNSUPPORTED'},
                      {'packet_capture':'STARTED'}, {'persistent_security_setting_changes':True}]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                validate({**self.pre, **patch}, self.cal)

    def test_positive_or_invalid_marker_counts_cannot_pass(self):
        for matches, attributed in [(0,1), (1,1), (-1,0), (True,0), (0,False), (0.0,0)]:
            with self.subTest(counts=(matches, attributed)), self.assertRaises(ValueError):
                validate(self.pre, {**self.cal, 'matching_marker_count':matches,
                                    'metadata_marker_count':attributed})
        result = validate(self.pre, {**self.cal, 'matching_marker_count':2})
        self.assertEqual(result['network_observation'], 'NOT_RUN')

    def test_time_bound_is_finite_and_not_boolean(self):
        for duration in [0, -1, 180.001, True, math.inf, math.nan, '60']:
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                validate(self.pre, {**self.cal, 'elapsed_seconds':duration})
        self.assertEqual(validate(self.pre, {**self.cal, 'elapsed_seconds':180})['observer_seconds'],180)

    def test_redaction_and_html_do_not_echo_free_text(self):
        for text in ['<script>', 'https://private.invalid', 'user@example.invalid', 'x\ny', 'x'*241]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                validate(self.pre, {**self.cal, 'limitation':text})
        result = validate(self.pre, {**self.cal, 'limitation':'SENSITIVE_SENTINEL'})
        self.assertNotIn('SENSITIVE_SENTINEL', render(result))
        self.assertIn('NOT_RUN', render(result))

    def test_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'duplicate.json'
            path.write_text('{"status":"NOT_RUN","status":"PASS"}')
            with self.assertRaises(ValueError):load(path)

    def test_cli_outputs_provenance_and_preserves_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            pre, cal, output, page = [Path(directory)/name for name in ('pre.json','cal.json','out.json','out.html')]
            pre.write_text(json.dumps(self.pre));cal.write_text(json.dumps(self.cal))
            before = pre.read_bytes(), cal.read_bytes()
            command = [sys.executable, str(ROOT/'rvi_report.py'), str(pre), str(cal)]
            subprocess.run(command+['--json-output',str(output),'--html-output',str(page)],check=True,capture_output=True)
            result = json.loads(output.read_text())
            self.assertRegex(result['preflight_sha256'],r'^[0-9a-f]{64}$')
            self.assertIn('Network verification: NOT_RUN',page.read_text())
            for arguments in [['--json-output',str(pre)], ['--json-output',str(output),'--html-output',str(output)]]:
                self.assertNotEqual(subprocess.run(command+arguments,capture_output=True).returncode,0)
            self.assertEqual((pre.read_bytes(),cal.read_bytes()),before)


if __name__ == '__main__':unittest.main()
