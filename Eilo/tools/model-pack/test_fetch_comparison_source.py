import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from fetch_comparison_source import artifacts, fetch, verify


class SourceTests(unittest.TestCase):
    def row(self, data=b'fixture', lfs=True):
        return {'path': 'fixture.bin', 'bytes': len(data),
                'sha256': hashlib.sha256(data).hexdigest() if lfs else None,
                'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}

    def test_both_digest_formats(self):
        for lfs in (False, True):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                row = self.row(lfs=lfs)
                fetch(root, row, 'unused', lambda *a, **k: io.BytesIO(b'fixture'))
                verify(root / row['path'], row)
                fetch(root, row, 'unused', lambda *a, **k: self.fail('existing verified file downloaded'))

    def test_failed_download_never_published(self):
        for data in (b'short', b'fixture!', b'corrupt'):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                with self.assertRaises(ValueError):
                    fetch(root, self.row(), 'unused', lambda *a, **k: io.BytesIO(data))
                self.assertEqual(list(root.iterdir()), [])

    def test_existing_corrupt_file_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'fixture.bin'
            target.write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                fetch(root, self.row(), 'unused', lambda *a, **k: self.fail('network used'))
            self.assertEqual(target.read_bytes(), b'corrupt')

    def test_symlink_denied(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'source').write_bytes(b'fixture')
            (root / 'fixture.bin').symlink_to(root / 'source')
            with self.assertRaises(ValueError):
                fetch(root, self.row(), 'unused')

    def test_manifest_paths_and_identity(self):
        lock = json.loads(Path(__file__).with_name('qwen3-0.6b-source-lock.json').read_text())
        self.assertEqual(sum(r['bytes'] for r in artifacts(lock)), 1519193708)
        for name in ('../escape', '.', '/absolute', 'nested/file'):
            altered = json.loads(json.dumps(lock))
            altered['source_artifacts'][0]['path'] = name
            with self.assertRaises(ValueError):
                artifacts(altered)
        lock['source_artifacts'].append(lock['source_artifacts'][0])
        with self.assertRaises(ValueError):
            artifacts(lock)


if __name__ == '__main__':
    unittest.main()
