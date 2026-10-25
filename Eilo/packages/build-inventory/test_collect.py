import copy
import io
import json
from pathlib import Path
import plistlib
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from collect import sdk_dependencies,pom_licenses,maven_inventory,npm_inventory,pods_inventory,safe_name,apk_inventory,ios_inventory,sha


def metadata(digest=True):
    escaped=''.join('\\%03o'%i for i in range(32))
    return '\nlibrary {\n  maven_library {\n    groupId: "example.group"\n    artifactId: "library"\n    version: "1.0"\n  }\n'+('  digests {\n    sha256: "'+escaped+'"\n  }\n' if digest else '')+'  repo_index {\n  }\n}\n'


class CollectTests(unittest.TestCase):
    def test_digest_bytes_and_missing_metadata_are_distinct(self):
        self.assertEqual(sdk_dependencies(metadata())[0]['artifact_sha256'],bytes(range(32)).hex())
        self.assertIsNone(sdk_dependencies(metadata(False))[0]['artifact_sha256'])
        for raw in [metadata()+metadata(),metadata().replace('sha256:','wrong:'),metadata().replace('example.group','bad/path')]:
            with self.assertRaises(ValueError):sdk_dependencies(raw)

    def test_cache_missing_mismatch_and_no_digest_are_not_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.assertEqual(maven_inventory(metadata(),root)[0]['cache_match'],'MISSING')
            folder=root/'example.group/library/1.0/hash';folder.mkdir(parents=True);(folder/'library.jar').write_bytes(b'wrong')
            self.assertEqual(maven_inventory(metadata(),root)[0]['cache_match'],'MISMATCH')
            self.assertEqual(maven_inventory(metadata(False),root)[0]['cache_match'],'NOT_RECORDED')

    def test_pom_declarations_do_not_follow_external_entities_or_infer_missing_license(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'x.pom';path.write_text('<project xmlns="urn:test"><licenses><license><name>MIT</name><url>https://example.com/LICENSE</url></license></licenses></project>')
            self.assertEqual(pom_licenses(path),[dict(name='MIT',url='https://example.com/LICENSE')])
            path.write_text('<project><parent><license>ignored inheritance</license></parent></project>');self.assertEqual(pom_licenses(path),[])
            path.write_text('<!DOCTYPE project [<!ENTITY x SYSTEM "file:///private">]><project/>')
            with self.assertRaises(ValueError):pom_licenses(path)

    def test_workspace_links_reference_real_lock_records_and_remain_lock_only(self):
        lock=dict(lockfileVersion=3,packages={'':{},'packages/local':dict(name='@local/package',version='1.0'),
            'node_modules/@local/package':dict(link=True,resolved='packages/local'),
            'node_modules/example':dict(version='2.0',license='MIT',dev=True)})
        rows=npm_inventory(lock);self.assertEqual(len(rows),2);self.assertTrue(rows[0]['development_only']);self.assertTrue(rows[1]['workspace']);self.assertIsNone(rows[1]['declared_license'])
        lock['packages']['node_modules/@local/package']['resolved']='missing'
        with self.assertRaises(ValueError):npm_inventory(lock)

    def test_pods_subspecs_and_notice_hashes_are_not_license_approvals(self):
        raw='PODS:\n  - Example (1.0):\n    - Other\n  - Example/Sub (1.0)\n\nDEPENDENCIES:\n'
        result=pods_inventory(raw,dict(PreferenceSpecifiers=[dict(Title='Example',FooterText='synthetic notice'),dict(Title='',FooterText='generated footer')]))
        self.assertEqual(len(result['components']),2);self.assertEqual(len(result['notice_evidence']),2)
        self.assertNotIn('synthetic notice',json.dumps(result))

    def test_archive_traversal_alias_and_controls_rejected(self):
        for name in ['../escape','/absolute','x\\y','x/../y','x//y','x/./y','x\nname']:
            with self.subTest(name=name),self.assertRaises(ValueError):safe_name(name)

    def test_apk_native_dependencies_permissions_and_model_leak_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'app.apk'
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('lib/arm64-v8a/libexample.so',b'\x7fELFsynthetic')
                z.writestr('assets/leaked.wav',b'synthetic')
            def run(tool,*args):
                return '(NEEDED) Shared library: [libc.so]\n' if str(tool)=='readelf' else "package: name='com.eilo' versionCode='1'\nuses-permission: name='android.permission.INTERNET'\n"
            with patch('collect.command',side_effect=run):r=apk_inventory(path,Path('readelf'),Path('aapt'))
            self.assertEqual(r['native_libraries'][0]['needed'],['libc.so']);self.assertEqual(r['prohibited_audio_model_resources'],['assets/leaked.wav'])
            self.assertEqual(r['permissions'],['android.permission.INTERNET'])

    def test_wrong_app_debug_and_device_artifacts_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'app.apk'
            with zipfile.ZipFile(path,'w') as z:z.writestr('lib/arm64-v8a/libexample.so',b'\x7fELFsynthetic')
            for badge in ["package: name='com.other' versionCode='1'\n", "package: name='com.eilo' versionCode='1'\napplication-debuggable\n"]:
                with patch('collect.command',side_effect=['',badge+"uses-permission: name='android.permission.INTERNET'\n"]),self.assertRaises(ValueError):apk_inventory(path,Path('readelf'),Path('aapt'))
            app=Path(tmp)/'Eilo.app';app.mkdir()
            (app/'Eilo').write_bytes(b'\xcf\xfa\xed\xfe'+b'synthetic')
            (app/'PrivacyInfo.xcprivacy').write_bytes(plistlib.dumps({}))
            for bundle,platform,supported in [('org.reactjs.native.example.Eilo','iphoneos','iPhoneOS'),('org.example.lab','iphonesimulator','iPhoneSimulator')]:
                (app/'Info.plist').write_bytes(plistlib.dumps(dict(CFBundleIdentifier=bundle,DTPlatformName=platform,CFBundleSupportedPlatforms=[supported])))
                with patch('collect.command',return_value=''),self.assertRaises(ValueError):ios_inventory(app,Path('none'))

    def test_apk_links_and_duplicate_paths_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'app.apk'
            with zipfile.ZipFile(path,'w') as z:
                member=zipfile.ZipInfo('lib/arm64-v8a/liblink.so');member.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(member,'outside')
            with self.assertRaises(ValueError):apk_inventory(path,Path('none'),Path('none'))
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning)
                with zipfile.ZipFile(path,'w') as z:
                    z.writestr('assets/same','first');z.writestr('assets/same','second')
            with self.assertRaises(ValueError):apk_inventory(path,Path('none'),Path('none'))

    def test_ios_binary_imports_strip_local_paths_and_keep_missing_tracking_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=Path(tmp)/'Example.app';app.mkdir();(app/'Example').write_bytes(b'\xcf\xfa\xed\xfe'+b'synthetic')
            (app/'PrivacyInfo.xcprivacy').write_bytes(plistlib.dumps({}))
            (app/'Info.plist').write_bytes(plistlib.dumps(dict(CFBundleIdentifier='org.reactjs.native.example.Eilo',DTPlatformName='iphonesimulator',CFBundleSupportedPlatforms=['iPhoneSimulator'])))
            with patch('collect.command',return_value='/private/example:\n\t/private/path/System.framework/System (compatibility version 1.0.0, current version 1.0.0)\n'):
                r=ios_inventory(app,Path('otool'))
            self.assertEqual(r['native_binaries'][0]['linked_basenames'],['System']);self.assertIsNone(r['privacy_declarations'][0]['declared_tracking'])
            self.assertNotIn('/private/path',json.dumps(r))
            (app/'linked').symlink_to('/tmp')
            with self.assertRaises(ValueError):ios_inventory(app,Path('none'))


if __name__=='__main__':unittest.main()
