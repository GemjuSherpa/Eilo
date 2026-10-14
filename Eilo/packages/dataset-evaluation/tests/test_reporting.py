import copy
import json
from pathlib import Path
import tempfile
import unittest
from benchmark import report
from reporting import export
from smoke import smoke
from test_benchmark import fixture
from manifests import canonical_digest


class ReportingTests(unittest.TestCase):
    def test_end_to_end_smoke_and_not_run(self):
        with tempfile.TemporaryDirectory() as temp:
            value = smoke(temp)
            self.assertEqual(value['status'], 'MEASURED')
            summary = json.loads((Path(temp) / 'summary.json').read_text())
            self.assertEqual(summary['kind'], 'synthetic')
            self.assertNotIn('cases', summary)
            self.assertEqual(json.loads((Path(temp) / 'not-run/summary.json').read_text())['status'], 'NOT_RUN')
            self.assertEqual(json.loads((Path(temp) / 'regression.json').read_text())['status'], 'PASS')

    def test_escape_and_reduce_output(self):
        manifest, value = fixture()
        manifest['dataset'] = '<script>alert(1)</script>'
        value['manifest_sha256'] = canonical_digest(manifest)
        result = report(manifest, value)
        result['transcript'] = 'PRIVATE_TEST_TEXT'
        result['path'] = '/private/speaker.wav'
        with tempfile.TemporaryDirectory() as temp:
            summary = export(result, temp)
            page = (Path(temp) / 'summary.html').read_text()
            self.assertNotIn('<script>', page)
            self.assertIn('&lt;script&gt;', page)
            self.assertNotIn('PRIVATE_TEST_TEXT', page)
            self.assertNotIn('path', summary)

    def test_altered_physical_or_fake_not_run_rejected(self):
        manifest, _ = fixture()
        result = report(manifest)
        with tempfile.TemporaryDirectory() as temp:
            bad = copy.deepcopy(result)
            bad['physical_gates']['screen_off'] = 'PASS'
            with self.assertRaises(ValueError): export(bad, temp)
            bad = copy.deepcopy(result)
            bad['metrics']['wer'] = 0
            with self.assertRaises(ValueError): export(bad, temp)
