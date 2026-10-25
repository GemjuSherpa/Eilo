import copy
import json
from pathlib import Path
import tempfile
import unittest
from noise_report import HERE,validate_suite,export,sha,load


def fixture():
    clean=json.loads((HERE/'corpus-results.json').read_text())
    reports={str(s):copy.deepcopy(clean) for s in (20,10,0)}
    for i,r in enumerate(reports.values()):r['provenance']['manifest_sha256']=str(i+1)*64
    suite=dict(schema_version=1,purpose='PAIRED_NOISE_SCORE_DIAGNOSTIC',
        clean_manifest_sha256=clean['provenance']['manifest_sha256'],noisy_manifest_sha256='a'*64,noise_manifest_sha256='b'*64,
        source_pins={n:sha(HERE/n) for n in ['noise_suite.py','run_android.py','diagnostics.py','main.cpp']},
        parents=30,variants=90,snrs=[20,10,0],pairing='SAME_PARENTS_CORRELATED_NOT_INDEPENDENT',
        threshold_fitting='NOT_PERFORMED',physical='NOT_RUN',production='NOT_ENABLED',reports={s:'c'*64 for s in reports})
    return suite,reports,clean


class NoiseReportTests(unittest.TestCase):
    def test_closed_scope_and_coverage(self):
        s,r,c=fixture();validate_suite(s,r,c)
        for mutation in [lambda s:s.update(parents=29),lambda s:s.update(variants=89),lambda s:s.update(physical='PASS'),
                         lambda s:s.update(threshold_fitting='PERFORMED'),lambda s:s.update(transcript='forbidden'),
                         lambda s:s.update(snrs=[0,10,20]),lambda s:s['source_pins'].update(**{'noise_suite.py':'0'*64})]:
            bad=copy.deepcopy(s);mutation(bad)
            with self.assertRaises(ValueError):validate_suite(bad,r,c)

    def test_missing_or_duplicate_condition_and_changed_model(self):
        s,r,c=fixture();r.pop('0')
        with self.assertRaises(ValueError):validate_suite(s,r,c)
        s,r,c=fixture();r['0']['provenance']['manifest_sha256']=r['10']['provenance']['manifest_sha256']
        with self.assertRaises(ValueError):validate_suite(s,r,c)
        s,r,c=fixture();r['0']['provenance']['ort_sha256']='0'*64
        with self.assertRaises(ValueError):validate_suite(s,r,c)

    def test_export_no_content_no_overwrite_and_byte_hash_integrity(self):
        s,r,c=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for snr,report in r.items():
                file=root/('snr'+snr+'.json');file.write_text(json.dumps(report));s['reports'][snr]=sha(file)
            (root/'suite.json').write_text(json.dumps(s));clean=root/'clean.json';clean.write_text(json.dumps(c))
            out=root/'out';result=export(root,clean,out);self.assertEqual(len(result['rows']),8)
            for token in ['"reference"','"transcript"','"speaker"','"case_id"']:self.assertNotIn(token,(out/'summary.json').read_text())
            with self.assertRaises(FileExistsError):export(root,clean,out)
            file=root/'snr0.json';file.write_text(file.read_text()+' ')
            with self.assertRaises(ValueError):load(root,clean)


if __name__=='__main__':unittest.main()
