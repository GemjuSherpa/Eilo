"""Actual scanner controls for the two independently verified source-hash exceptions."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO=Path(__file__).resolve().parents[2]


def scan(path,lines):
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);file=root/path;file.parent.mkdir(parents=True);file.write_text('\n'.join(lines)+'\n')
        report=root/'findings.json'
        process=subprocess.run(['gitleaks','dir','.','--config',str(REPO/'.gitleaks.toml'),'--redact=100','--no-banner','--report-format','json','--report-path',str(report)],capture_output=True,text=True,timeout=30,cwd=root)
        if process.returncode not in (0,1):raise RuntimeError('scanner did not complete')
        findings=json.loads(report.read_text()) if report.exists() else []
        return process.returncode,findings


def hash_lines():
    source=REPO/'Eilo/packages/native-test-seam/Sources/NativeTestSeam'
    return ['  "native-test-seam/Sources/NativeTestSeam/'+name+'": "'+hashlib.sha256((source/name).read_bytes()).hexdigest()+'",' for name in ('IOSConsentAuthentication.swift','ProtectedKey.swift')]


class FrameworkScannerTests(unittest.TestCase):
    def test_verified_hash_fields_only_are_exempt(self):
        code,rows=scan('Eilo/packages/asr-runtime/framework-results.json',hash_lines())
        self.assertEqual(code,0);self.assertEqual(rows,[])

    def test_same_file_credential_field_is_still_detected(self):
        # Deliberately generated noncredential; never log the matching value.
        marker=hashlib.sha256(b'synthetic scanner positive control, not a credential').hexdigest()
        code,rows=scan('Eilo/packages/asr-runtime/framework-results.json',hash_lines()+['"api_key": "'+marker+'"'])
        self.assertEqual(code,1);self.assertTrue(any(r['RuleID']=='generic-api-key' for r in rows))

    def test_same_hash_fields_in_other_files_remain_detected(self):
        code,rows=scan('Eilo/packages/asr-runtime/other.json',hash_lines())
        self.assertEqual(code,1);self.assertEqual(len(rows),2)


if __name__=='__main__':unittest.main()
