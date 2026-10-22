import tempfile
import json
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import check_installer_android as art
import check_android_installer_evidence as evidence


class AndroidInstallerTests(unittest.TestCase):
    def test_explicit_emulator_only(self):
        self.assertEqual(art.serial('emulator-5554'), 'emulator-5554')
        for value in ('physical-device', 'emulator-5554;echo', 'emulator-', None, True):
            with self.assertRaises(ValueError):
                art.serial(value)

    def test_exact_symbol_and_version_required(self):
        needed = 'U OrtGetApiBase@VERS_1.23.2\nU OrtSessionOptionsAppendExecutionProvider_CPU@VERS_1.23.2'
        symbols = 'T OrtGetApiBase@@VERS_1.23.2\nT OrtSessionOptionsAppendExecutionProvider_CPU@@VERS_1.23.2'
        art.require_ort_symbols(needed, symbols)
        for bad in (symbols.replace('1.23.2', '1.28.2'), symbols.splitlines()[0], '', 'T Other@@VERS_1.23.2'):
            with self.assertRaises(ValueError):
                art.require_ort_symbols(needed, bad)
        with self.assertRaises(ValueError):
            art.require_ort_symbols('', symbols)

    def apk(self, folder, libraries):
        path = Path(folder) / 'app.apk'
        with zipfile.ZipFile(path, 'w') as archive:
            for name in libraries:
                archive.writestr('lib/arm64-v8a/' + name, b'fixture')
        return path

    def test_evaluation_apk_must_remove_mic_and_internet(self):
        with tempfile.TemporaryDirectory() as folder:
            apk = self.apk(folder, art.LIBRARIES)
            with patch.object(art, 'run', side_effect=['package: com.eilo', 'SignedSpeechArtInstrumentation']):
                art.inspect_apk(apk, Path('aapt'), True)
            for permission in ('INTERNET', 'RECORD_AUDIO'):
                with patch.object(art, 'run', return_value='android.permission.' + permission):
                    with self.assertRaises(ValueError):
                        art.inspect_apk(apk, Path('aapt'), True)

    def test_normal_apk_must_remove_evaluation_native_and_runner(self):
        permissions = 'android.permission.INTERNET android.permission.RECORD_AUDIO'
        with tempfile.TemporaryDirectory() as folder:
            apk = self.apk(folder, [])
            with patch.object(art, 'run', side_effect=[permissions, 'normal manifest']):
                art.inspect_apk(apk, Path('aapt'), False)
            with patch.object(art, 'run', side_effect=[permissions, 'SignedSpeechArtInstrumentation']):
                with self.assertRaises(ValueError):
                    art.inspect_apk(apk, Path('aapt'), False)
            apk = self.apk(folder, art.LIBRARIES)
            with patch.object(art, 'run', return_value=permissions):
                with self.assertRaises(ValueError):
                    art.inspect_apk(apk, Path('aapt'), False)

    def report(self):
        return evidence.load(art.HERE / 'tests/signed-installer-android-results.json')

    def test_actual_aggregate_is_not_physical_acceptance(self):
        result = evidence.check_evidence()
        self.assertEqual(result['cases'], 8)
        self.assertEqual(result['physical'], 'NOT_RUN')
        self.assertEqual(result['production'], 'NOT_ENABLED')

    def test_scope_cleanup_and_permission_promotions_reject(self):
        for key, value in [('physical', 'PASS'), ('production', 'ENABLED'),
                           ('internet_permission', 'PRESENT'), ('microphone_permission', 'PRESENT'),
                           ('temporary_files_removed', False), ('normal_app_restored', False),
                           ('controller_permission_and_readiness', 'PRODUCTION'), ('android_api', True)]:
            report = self.report(); report[key] = value
            with self.assertRaises(ValueError):
                evidence.validate_report(report)

    def test_model_conversion_and_vendor_tampering_reject(self):
        for change in ('model', 'conversion', 'vendor', 'source', 'native-case', 'field'):
            report = self.report()
            if change == 'model': report['asr_model_files'].pop()
            elif change == 'conversion': report['vad_conversion']['optimization'] = 'ENABLED'
            elif change == 'vendor': report['library_sha256']['libonnxruntime.so'] = 'a' * 64
            elif change == 'source': report['vad_source_model_sha256'] = 'a' * 64
            elif change == 'native-case': report['cases'][0]['recognized'] = 0
            else: report['endpoint'] = 'private-marker'
            with self.assertRaises(ValueError):
                evidence.validate_report(report)

    def test_duplicate_keys_and_header_tampering_reject(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); path = root / 'bad.json'
            path.write_text('{"physical":"PASS","physical":"NOT_RUN"}')
            with self.assertRaises(ValueError): evidence.load(path)
            path.write_bytes(b' ' * 524289)
            with self.assertRaises(ValueError): evidence.load(path)
            record = json.loads((art.HERE / 'android-ort-header-provenance.json').read_text())
            for row in record['files']: (root / row['file']).write_bytes(b'x' * row['bytes'])
            with self.assertRaises(ValueError): art.verify_headers(root)


if __name__ == '__main__':
    unittest.main()
