import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from check_capture_evidence import ROOT, check_evidence, sha256


class JoinedEvidenceTampering(unittest.TestCase):
    def test_source_changes_and_content_bearing_report_fail(self):
        audit_path = Path('packages/conversation-integration/tests/capture-evidence.json')
        report_path = Path('packages/conversation-integration/tests/ios-capture-results.json')
        audit = json.loads((ROOT / audit_path).read_text())
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for relative in [r['path'] for r in audit['inputs']] + [str(audit_path), str(report_path)]:
                target = root / relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            with contextlib.redirect_stdout(io.StringIO()): check_evidence(root)
            source = root / audit['inputs'][0]['path']; saved = source.read_bytes()
            source.write_bytes(saved + b'changed')
            with self.assertRaises(ValueError): check_evidence(root)
            source.write_bytes(saved)
            report = root / report_path; data = json.loads(report.read_text()); data['transcript'] = 'unexpected'
            report.write_text(json.dumps(data)); audit['report_sha256'] = sha256(report)
            (root / audit_path).write_text(json.dumps(audit))
            with self.assertRaises(ValueError): check_evidence(root)


if __name__ == '__main__':
    unittest.main()
