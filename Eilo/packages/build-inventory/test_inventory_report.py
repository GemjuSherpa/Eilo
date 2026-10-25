import copy
import json
from pathlib import Path
import tempfile
import unittest
from inventory_report import validate,export,read
from collect import HERE


def fixture():return read(HERE/'observed.json')


class ReportTests(unittest.TestCase):
    def test_actual_observations_preserve_gaps_and_build_scope(self):
        r=fixture();s=validate(r)
        self.assertEqual((s['android_native_libraries'],s['ios_native_binaries']),(52,4))
        self.assertEqual((s['maven_metadata_entries'],s['maven_verified'],s['maven_without_digest']),(108,100,8))
        self.assertEqual(s['maven_without_direct_license_declaration'],1);self.assertEqual(s['npm_undeclared_licenses'],5)
        self.assertEqual(s['sbom_completeness'],'NOT_ESTABLISHED')

    def test_no_release_license_privacy_or_physical_promotion(self):
        for key,value in [('release_acceptance','PASS'),('license_approval','GRANTED'),('network_privacy','PASS'),('physical','PASS'),('memory','ENABLED'),('sbom_completeness','COMPLETE'),('signing_provenance','VERIFIED')]:
            r=fixture();r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)

    def test_every_export_level_is_closed(self):
        for key in ['root','android','library','ios','binary','privacy','maven','pom','npm','pods','notice']:
            r=fixture();target={'root':r,'android':r['android'],'library':r['android']['native_libraries'][0],
                'ios':r['ios'],'binary':r['ios']['native_binaries'][0],'privacy':r['ios']['privacy_declarations'][0],
                'maven':r['maven'][0],'pom':r['maven'][0]['poms'][0],'npm':r['npm_lock_only'][0],
                'pods':r['pods_lock_and_notices'],'notice':r['pods_lock_and_notices']['notice_evidence'][0]}[key]
            target['transcript']='forbidden'
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)

    def test_unrecorded_digest_cannot_be_called_verified(self):
        r=fixture();c=next(c for c in r['maven'] if c['artifact_sha256'] is None);c['cache_match']='VERIFIED'
        with self.assertRaises(ValueError):validate(r)
        r=fixture();r['source_pins']['collect.py']='0'*64
        with self.assertRaises(ValueError):validate(r)
        r=fixture();r['repository_pins']['package-lock.json']='0'*64
        with self.assertRaises(ValueError):validate(r)

    def test_wrong_scope_resource_leaks_and_unsafe_binary_paths_are_rejected(self):
        for mutation in [lambda r:r['ios'].update(build_kind='SIGNED_DEVICE_RELEASE'),
                         lambda r:r['android']['prohibited_audio_model_resources'].append('assets/fixture.wav'),
                         lambda r:r['android']['native_libraries'][0].update(path='../lib.so'),
                         lambda r:r['ios']['native_binaries'][0]['linked_basenames'].append('/Users/private'),
                         lambda r:r['input_pins'].update(npm_lock='0'*64)]:
            r=fixture();mutation(r)
            with self.assertRaises(ValueError):validate(r)

    def test_export_is_content_free_and_refuses_overwrite_and_bad_json(self):
        r=fixture();encoded=json.dumps(r)
        for token in ['/Users/','/private/tmp/','"transcript"','"reference"','"speaker"','"case_id"','FooterText']:
            self.assertNotIn(token,encoded)
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'report';export(r,output)
            self.assertIn('not a complete mapping',(output/'summary.html').read_text())
            with self.assertRaises(ValueError):export(r,output)
            p=Path(tmp)/'bad.json'
            for raw in ['{"x":1,"x":2}','{"x":NaN}']:
                p.write_text(raw)
                with self.assertRaises(ValueError):read(p)


if __name__=='__main__':unittest.main()
