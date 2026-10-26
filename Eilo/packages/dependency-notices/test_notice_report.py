import copy
import json
from pathlib import Path
import tempfile
import unittest
from notice_report import validate,export
from notices import HERE
from inventory_report import read


def fixture():return read(HERE/'observed.json')


class ReportTests(unittest.TestCase):
    def test_observed_provenance_resolves_two_metadata_gaps_without_approval(self):
        r=fixture();s=validate(r)
        self.assertEqual((s['maven_entries'],s['verified_artifacts_scanned'],s['unrecorded_artifact_digests']),(108,100,8))
        self.assertEqual((s['artifacts_with_notices'],s['artifacts_without_matching_notice'],s['notice_records']),(12,88,12))
        self.assertEqual((s['distinct_notice_hashes'],s['distinct_notice_hashes_found_in_apk']),(2,2))
        self.assertEqual(s['cached_parent_declarations'],1);self.assertEqual(s['ios_matching_notice_files'],0)
        self.assertEqual(s['own_workspace_license'],'OWNER_DECISION_PENDING')

    def test_license_owner_choice_and_release_cannot_be_promoted(self):
        for key,value in [('own_workspace_license','MIT'),('sbom_completeness','COMPLETE'),('redistribution_review','PASS'),('release_acceptance','PASS'),('network_privacy','PASS'),('physical','PASS'),('memory','ENABLED')]:
            r=fixture();r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)

    def test_stale_sources_changed_artifacts_and_missing_components_rejected(self):
        for mutate in [lambda r:r['source_pins'].update(**{'packages/dependency-notices/notices.py':'0'*64}),
                       lambda r:r.update(baseline_inventory_sha256='0'*64),lambda r:r['maven'].pop(),
                       lambda r:r['maven'][0].update(artifact_sha256='0'*64),lambda r:r['packaged']['android'].update(artifact_sha256='0'*64)]:
            r=fixture();mutate(r)
            with self.assertRaises(ValueError):validate(r)

    def test_all_nested_records_are_closed_to_content(self):
        for location in ['root','record','notice','parent','chain','license','npm','file','packaged']:
            r=fixture();record=next(x for x in r['maven'] if x['notices']);parent=next(x['parent_declaration'] for x in r['maven'] if x['parent_declaration'])
            target={'root':r,'record':record,'notice':record['notices'][0],'parent':parent,'chain':parent['chain'][0],
                    'license':parent['chain'][-1]['licenses'][0],'npm':r['npm_exit'],'file':r['npm_exit']['files'][0],'packaged':r['packaged']}[location]
            target['license_body']='forbidden'
            with self.subTest(location=location),self.assertRaises(ValueError):validate(r)

    def test_embedded_child_parent_and_installed_proof_cannot_be_dropped(self):
        r=fixture();p=next(x['parent_declaration'] for x in r['maven'] if x['parent_declaration']);p['child_embedded_pom_sha256']='0'*64
        with self.assertRaises(ValueError):validate(r)
        r=fixture();r['npm_exit']['files'][0]['installed_bytes_match']=False
        with self.assertRaises(ValueError):validate(r)
        r=fixture();r['npm_exit']['integrity']='sha512-'+'A'*88
        with self.assertRaises(ValueError):validate(r)
        r=fixture();record=next(x for x in r['maven'] if x['artifact_sha256'] is None);record['notices']=[]
        with self.assertRaises(ValueError):validate(r)

    def test_export_no_bodies_paths_or_overwrite_and_closed_json(self):
        r=fixture();encoded=json.dumps(r)
        for token in ['/Users/','/private/tmp/','Permission is hereby','"license_body"','"transcript"','"speaker"']:self.assertNotIn(token,encoded)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'report';export(r,out);self.assertIn('not authenticated publisher metadata',(out/'summary.html').read_text())
            with self.assertRaises(ValueError):export(r,out)
            path=Path(tmp)/'bad.json'
            for raw in ['{"x":1,"x":2}','{"x":NaN}']:
                path.write_text(raw)
                with self.assertRaises(ValueError):read(path)


if __name__=='__main__':unittest.main()
