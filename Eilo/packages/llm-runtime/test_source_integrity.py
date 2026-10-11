import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from check_host import verify_tree


class SourceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.archive = self.root / 'source.tar.gz'

    def archive_entries(self, entries):
        with tarfile.open(self.archive, 'w:gz') as archive:
            for name, kind in entries:
                item = tarfile.TarInfo(name)
                if kind == 'link':
                    item.type = tarfile.SYMTYPE
                    item.linkname = '/tmp/outside'
                    archive.addfile(item)
                else:
                    item.size = 7
                    archive.addfile(item, io.BytesIO(b'fixture'))

    def normal(self):
        self.archive_entries([('source/code.cc', 'file')])
        (self.source / 'code.cc').write_bytes(b'fixture')

    def test_exact_source_passes(self):
        self.normal()
        verify_tree(self.archive, self.source, 'source')

    def test_edited_source_is_rejected(self):
        self.normal()
        (self.source / 'code.cc').write_bytes(b'changed')
        with self.assertRaises(ValueError):
            verify_tree(self.archive, self.source, 'source')

    def test_extra_source_is_rejected(self):
        self.normal()
        (self.source / 'unexpected.cc').write_bytes(b'fixture')
        with self.assertRaises(ValueError):
            verify_tree(self.archive, self.source, 'source')

    def test_traversal_link_and_duplicate_are_rejected(self):
        for entries in [[('source/../outside', 'file')], [('source/code.cc', 'link')],
                        [('source/code.cc', 'file'), ('source/code.cc', 'file')]]:
            with self.subTest(entries=entries):
                (self.source / 'code.cc').write_bytes(b'fixture')
                self.archive_entries(entries)
                with self.assertRaises(ValueError):
                    verify_tree(self.archive, self.source, 'source')

    def test_symlink_source_is_rejected(self):
        self.normal()
        target = self.root / 'outside'
        target.write_bytes(b'fixture')
        (self.source / 'code.cc').unlink()
        (self.source / 'code.cc').symlink_to(target)
        with self.assertRaises(ValueError):
            verify_tree(self.archive, self.source, 'source')


if __name__ == '__main__':
    unittest.main()
