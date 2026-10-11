"""Synthetic APK/ELF rejection checks; no device or native execution."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

from check_android_package import LIBRARIES, verify_apk, verify_elf


class PackageChecks(unittest.TestCase):
    def test_elf_requires_loads_and_64_bit_alignment(self):
        good = ' LOAD 0x0 0x0 0x0 0x100 0x100 R E 0x4000\n LOAD 0x4000 0x4000 0x4000 0x100 0x100 RW 0x4000'
        self.assertEqual([16384, 16384], verify_elf(good, '', 'arm64-v8a')['load_alignments'])
        for headers in ('', good.replace('RW 0x4000', 'RW 0x1000'), good.replace('RW 0x4000', 'RW 0x5000')):
            with self.assertRaises(ValueError):
                verify_elf(headers, '', 'x86_64')
        self.assertEqual([4096], verify_elf(' LOAD 0 0 0 0 0 R 0x1000', '', 'x86')['load_alignments'])

    def test_dependencies_must_be_packaged_or_system(self):
        headers = ' LOAD 0 0 0 0 0 R 0x4000'
        dynamic = '(NEEDED) Shared library: [libonnxruntime.so]\n(NEEDED) Shared library: [libc.so]'
        self.assertEqual(['libonnxruntime.so', 'libc.so'], verify_elf(headers, dynamic, 'arm64-v8a')['needed'])
        with self.assertRaises(ValueError):
            verify_elf(headers, '(NEEDED) Shared library: [libmissing.so]', 'arm64-v8a')

    def test_apk_rejects_missing_changed_compressed_extra_and_duplicate_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            apk = Path(directory) / 'synthetic.apk'
            entries = {f'lib/arm64-v8a/{name}': b'synthetic' for name in LIBRARIES}
            expected = {name: hashlib.sha256(data).hexdigest() for name, data in entries.items()}
            def write(items, compression=zipfile.ZIP_STORED):
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    with zipfile.ZipFile(apk, 'w', compression=compression) as out:
                        for name, data in items:
                            out.writestr(name, data)
            write(list(entries.items()))
            self.assertEqual(3, verify_apk(apk, expected)['wake_library_entries'])
            mutations = [list(entries.items())[1:], [(name, b'changed') for name in entries],
                         list(entries.items()) + [('lib/x86/libonnxruntime.so', b'synthetic')],
                         list(entries.items()) + [next(iter(entries.items()))]]
            for items in mutations:
                write(items)
                with self.assertRaises(ValueError):
                    verify_apk(apk, expected)
            write(list(entries.items()), zipfile.ZIP_DEFLATED)
            with self.assertRaises(ValueError):
                verify_apk(apk, expected)


if __name__ == '__main__':
    unittest.main()
