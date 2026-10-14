import copy
import json
from pathlib import Path
import tempfile
import unittest
from manifests import HERE, receipt, safe_path, validate_registry, verify_receipt


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads((HERE / 'registry.json').read_text())
        self.synthetic_registry = copy.deepcopy(self.registry)
        self.synthetic_registry['datasets'][1].update({'sha256': None, 'bytes': None,
                                                       'checksum_status': 'NOT_DOWNLOADED'})

    def test_registry_and_unapproved_common_voice(self):
        validate_registry(self.registry)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'archive'
            path.write_bytes(b'synthetic')
            registry = copy.deepcopy(self.registry)
            registry['datasets'][0]['permission'] = 'ACCOUNT_AND_TERMS_REQUIRED'
            with self.assertRaises(ValueError):
                receipt(registry, 'common_voice', path, path)

    def test_receipt_detects_same_size_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'archive'
            path.write_bytes(b'1234')
            value = receipt(self.synthetic_registry, 'musan', path, path)
            verify_receipt(value, path)
            self.assertEqual(value['checksum_status'], 'LOCAL_OBSERVED')
            path.write_bytes(b'4321')
            with self.assertRaises(ValueError):
                verify_receipt(value, path)

    def test_invalid_registry(self):
        for field, value in [('sha256', 'bad'), ('download_url', 'http://example.com'),
                             ('bytes', -1), ('checksum_status', 'PASS')]:
            record = copy.deepcopy(self.registry)
            record['datasets'][1][field] = value
            with self.assertRaises(ValueError):
                validate_registry(record)

    def test_traversal_and_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'root'
            root.mkdir()
            outside = Path(temp) / 'audio'
            outside.write_bytes(b'x')
            (root / 'link').symlink_to(outside)
            for path in ('../audio', str(outside), 'link'):
                with self.assertRaises(ValueError):
                    safe_path(root, path)

    def test_empty_archive_and_incomplete_receipts_rejected(self):
        from manifests import validate_receipt
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'archive'
            path.write_bytes(b'')
            with self.assertRaises(ValueError): receipt(self.synthetic_registry, 'musan', path, path)
            path.write_bytes(b'valid')
            value = receipt(self.synthetic_registry, 'musan', path, path)
            for key, invalid in [('bytes', 0), ('version', 'UNSELECTED'),
                                 ('license', 'unreviewed'), ('permission', 'PENDING')]:
                record = dict(value)
                record[key] = invalid
                with self.assertRaises(ValueError): validate_receipt(record)

    def test_registry_pin_cannot_be_silently_replaced(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'changed-archive'
            path.write_bytes(b'different archive')
            registry = copy.deepcopy(self.registry)
            registry['datasets'][1].update({'sha256': '0' * 64, 'bytes': path.stat().st_size,
                                            'checksum_status': 'LOCAL_OBSERVED'})
            with self.assertRaises(ValueError): receipt(registry, 'musan', path, path)
