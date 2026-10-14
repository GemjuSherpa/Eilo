import copy
import json
from pathlib import Path
import tempfile
import unittest
from manifests import HERE, receipt, safe_path, validate_registry, verify_receipt


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads((HERE / 'registry.json').read_text())

    def test_registry_and_unselected_common_voice(self):
        validate_registry(self.registry)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'archive'
            path.write_bytes(b'synthetic')
            with self.assertRaises(ValueError):
                receipt(self.registry, 'common_voice', path, path)

    def test_receipt_detects_same_size_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'archive'
            path.write_bytes(b'1234')
            value = receipt(self.registry, 'musan', path, path)
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
