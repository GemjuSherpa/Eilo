import copy
import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch
import audit
import report


class AuditTests(unittest.TestCase):
    def sample(self):
        return dict(NSPrivacyAccessedAPITypes=[dict(NSPrivacyAccessedAPIType='NSPrivacyAccessedAPICategoryFileTimestamp', NSPrivacyAccessedAPITypeReasons=['C617.1'])], NSPrivacyTracking=False, NSPrivacyCollectedDataTypes=[])

    def test_xml_binary_equal_and_unknowns_preserved(self):
        value = self.sample()
        xml = audit.manifest(plistlib.dumps(value)); binary = audit.manifest(plistlib.dumps(value, fmt=plistlib.FMT_BINARY))
        self.assertEqual(xml, binary)
        self.assertFalse(xml['tracking']); self.assertIsNone(xml['tracking_domains_count'])
        self.assertIsNone(audit.manifest(plistlib.dumps({}))['tracking'])
        self.assertFalse(audit.manifest(plistlib.dumps({}))['accessed_api_list_present'])

    def test_xml_duplicates_and_external_entities_denied(self):
        for raw in [b'<plist><dict><key>NSPrivacyTracking</key><false/><key>NSPrivacyTracking</key><true/></dict></plist>',
                    b'<!DOCTYPE plist [<!ENTITY x SYSTEM "file:///etc/passwd">]><plist><dict/></plist>',
                    b'<!doctype plist><plist><dict/></plist>']:
            with self.subTest(raw=raw), self.assertRaises(ValueError): audit.manifest(raw)

    def test_duplicate_binary_keys_denied(self):
        # Handcrafted valid binary plist dictionary whose two keys point to one key object.
        raw = bytearray(plistlib.dumps({'a': False, 'b': True}, fmt=plistlib.FMT_BINARY, sort_keys=True))
        self.assertEqual(raw[8], 0xd2)
        raw[10] = raw[9]
        with self.assertRaises(ValueError): audit.manifest(bytes(raw))

    def test_malformed_reasons_and_categories(self):
        for key, value in [('NSPrivacyAccessedAPITypeReasons', []), ('NSPrivacyAccessedAPITypeReasons', ['C617.1', 'C617.1']),
                           ('NSPrivacyAccessedAPITypeReasons', ['<script>']), ('NSPrivacyAccessedAPITypeReasons', 'C617.1'),
                           ('NSPrivacyAccessedAPIType', '../../private')]:
            d = self.sample(); d['NSPrivacyAccessedAPITypes'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError): audit.manifest(plistlib.dumps(d))
        d = self.sample(); d['NSPrivacyAccessedAPITypes'] *= 2
        with self.assertRaises(ValueError): audit.manifest(plistlib.dumps(d))

    def test_tracking_types_unknown_fields_and_bounds(self):
        for value in [dict(NSPrivacyTracking=0), dict(NSPrivacyAccessedAPITypes={}), dict(NSPrivacyTrackingDomains='private'),
                      dict(unknown='value'), dict(NSPrivacyCollectedDataTypes={})]:
            with self.subTest(value=value), self.assertRaises(ValueError): audit.manifest(plistlib.dumps(value))
        with self.assertRaises(ValueError): audit.manifest(b'x'*262145)

    def test_domain_values_and_collected_details_not_exported(self):
        d = self.sample(); d['NSPrivacyTrackingDomains'] = ['private.example']; d['NSPrivacyCollectedDataTypes'] = [{'sensitive': 'secret'}]
        result = audit.manifest(plistlib.dumps(d)); text = json.dumps(result)
        self.assertNotIn('private.example', text); self.assertNotIn('secret', text)
        self.assertEqual(result['tracking_domains_count'], 1); self.assertEqual(result['collected_data_count'], 1)

    def test_selected_imports_exact_names_only(self):
        result = audit.selected_imports('_fstat\n_fstat\n_statfs\n_prefix_fstat\n_fstat_suffix\n_other\n')
        self.assertEqual(result, [{'category': 'NSPrivacyAccessedAPICategoryDiskSpace', 'symbols': ['_statfs']},
                                 {'category': 'NSPrivacyAccessedAPICategoryFileTimestamp', 'symbols': ['_fstat']}])
        self.assertEqual(audit.selected_imports('_other'), [])

    def test_tree_fingerprint_tamper_and_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root/'a').write_bytes(b'a'); first = audit.tree_digest(root)
            (root/'a').write_bytes(b'b'); self.assertNotEqual(first, audit.tree_digest(root))
            (root/'link').symlink_to(root/'a')
            with self.assertRaises(ValueError): audit.tree_digest(root)

    def test_collector_rejects_wrong_artifact_before_tool_execution(self):
        baseline = {'ios': {'tree_sha256': '0'*64}}
        with tempfile.TemporaryDirectory() as folder, patch.object(audit, 'read', return_value=baseline), patch.object(audit, 'validate_baseline'), patch.object(audit.subprocess, 'run') as run:
            (Path(folder)/'a').write_bytes(b'actual bytes')
            with self.assertRaises(ValueError): audit.inspect(Path(folder), Path('/missing-nm'))
            run.assert_not_called()

    def inspect_fixture(self, root, nm):
        raw = plistlib.dumps(self.sample()); (root/'PrivacyInfo.xcprivacy').write_bytes(raw)
        (root/'Eilo').write_bytes(b'pinned binary'); nm.write_bytes(b'pinned tool')
        return {'ios': {'tree_sha256': audit.tree_digest(root),
                'privacy_declarations': [{'path': 'PrivacyInfo.xcprivacy', 'sha256': audit.sha(root/'PrivacyInfo.xcprivacy'),
                                         'accessed_api_types': ['NSPrivacyAccessedAPICategoryFileTimestamp'], 'declared_tracking': False}],
                'native_binaries': [{'path': 'Eilo', 'sha256': audit.sha(root/'Eilo')}]}}

    def test_collector_pinned_inputs_and_exact_tool_arguments(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/'app'; root.mkdir(); nm = Path(folder)/'nm'; baseline = self.inspect_fixture(root, nm)
            result = type('Result', (), {'stdout': '_fstat\n_unrelated\n'})()
            with patch.object(audit, 'read', return_value=baseline), patch.object(audit, 'validate_baseline'), patch.object(audit.subprocess, 'run', return_value=result) as run:
                value = audit.inspect(root, nm)
                self.assertEqual(value['binaries'][0]['selected_imports'][0]['symbols'], ['_fstat'])
                self.assertEqual(run.call_args.args[0], [str(nm), '-u', '-j', str(root/'Eilo')])
                self.assertTrue(run.call_args.kwargs['check'])

    def test_collector_rechecks_artifact_and_tool_after_scan(self):
        for target in ['Eilo', 'nm']:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)/'app'; root.mkdir(); nm = Path(folder)/'nm'; baseline = self.inspect_fixture(root, nm)
                def changed(*args, **kwargs):
                    (nm if target == 'nm' else root/'Eilo').write_bytes(b'changed')
                    return type('Result', (), {'stdout': '_fstat\n'})()
                with patch.object(audit, 'read', return_value=baseline), patch.object(audit, 'validate_baseline'), patch.object(audit.subprocess, 'run', side_effect=changed):
                    with self.assertRaises(ValueError): audit.inspect(root, nm)

    def test_unmatched_disk_candidate_is_explicit(self):
        value = report.read(audit.HERE/'observed.json')
        value['binaries'][0]['selected_imports'].insert(0, {'category': 'NSPrivacyAccessedAPICategoryDiskSpace', 'symbols': ['_statfs']})
        self.assertEqual(report.validate(value)['candidate_categories_without_app_wide_declaration'], ['NSPrivacyAccessedAPICategoryDiskSpace'])


class ReportTests(unittest.TestCase):
    def setUp(self): self.value = report.read(audit.HERE/'observed.json')

    def test_current_snapshot_and_summary(self):
        s = report.validate(self.value)
        self.assertEqual((s['manifests'], s['binaries'], s['declared_category_reason_pairs'], s['selected_import_matches']), (8, 4, 3, 7))
        self.assertEqual(s['candidate_categories_without_app_wide_declaration'], [])
        self.assertEqual(s['api_coverage'], 'NOT_ESTABLISHED')

    def test_stale_pins_wrong_artifacts_and_promotions_denied(self):
        for mutate in [lambda v: v['source_pins'].clear(), lambda v: v.update(app_tree_sha256='0'*64),
                       lambda v: v['binaries'][0].update(sha256='0'*64), lambda v: v['manifests'][0].update(sha256='0'*64),
                       lambda v: v.update(release_acceptance='PASS'), lambda v: v.update(api_coverage='COMPLETE'),
                       lambda v: v.update(physical='PASS'), lambda v: v.update(memory='ENABLED')]:
            v = copy.deepcopy(self.value); mutate(v)
            with self.assertRaises(ValueError): report.validate(v)

    def test_unmapped_import_and_reason_injection_denied(self):
        v = copy.deepcopy(self.value); v['binaries'][0]['selected_imports'][0]['symbols'].append('_private')
        with self.assertRaises(ValueError): report.validate(v)
        v = copy.deepcopy(self.value); v['manifests'][0]['declarations'][0]['reasons'] = ['<script>']
        with self.assertRaises(ValueError): report.validate(v)

    def test_ambiguous_json_and_overwrite_denied(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'input.json'; p.write_text('{"x":1,"x":2}')
            with self.assertRaises(ValueError): report.read(p)
            out = Path(folder)/'out'; report.export(self.value, out)
            self.assertIn('not proof', (out/'summary.html').read_text())
            self.assertNotIn('/Users/', (out/'summary.json').read_text())
            with self.assertRaises(ValueError): report.export(self.value, out)


if __name__ == '__main__': unittest.main()
