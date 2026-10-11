import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import prepare_source


class Response(io.BytesIO):
    def __init__(self, data, url):
        super().__init__(data)
        self.url = url

    def geturl(self):
        return self.url


class SourceDownloadTests(unittest.TestCase):
    def scenario(self, response_url, correct_hash):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            source.mkdir()
            (source / 'code.cc').write_bytes(b'fixture')
            data = io.BytesIO()
            with tarfile.open(fileobj=data, mode='w:gz') as archive:
                item = tarfile.TarInfo('source/code.cc')
                item.size = 7
                archive.addfile(item, io.BytesIO(b'fixture'))
            payload = data.getvalue()
            previous = root / 'llama-v0.6.0.tar.gz'
            previous.write_bytes(b'previous')
            provenance = {'runtime': {'source_url': 'https://example.invalid/source',
                                      'source_archive_sha256': hashlib.sha256(payload).hexdigest() if correct_hash else '0' * 64}}
            with patch.object(prepare_source, 'CACHE', root), patch.object(prepare_source, 'SOURCE', source), \
                    patch.object(prepare_source, 'PROVENANCE', provenance), \
                    patch.object(prepare_source.urllib.request, 'urlopen', return_value=Response(payload, response_url)):
                if response_url != provenance['runtime']['source_url'] or not correct_hash:
                    with self.assertRaises(ValueError):
                        prepare_source.main()
                    self.assertEqual(previous.read_bytes(), b'previous')
                else:
                    prepare_source.main()
                    self.assertEqual(previous.read_bytes(), payload)
            self.assertEqual((source / 'code.cc').read_bytes(), b'fixture')
            self.assertFalse((root / 'source-download.tmp').exists())

    def test_changed_download_cannot_replace_previous_archive(self):
        self.scenario('https://example.invalid/source', False)

    def test_foreign_redirect_is_rejected(self):
        self.scenario('https://other.invalid/source', True)

    def test_verified_existing_source_is_preserved(self):
        self.scenario('https://example.invalid/source', True)


if __name__ == '__main__':
    unittest.main()
