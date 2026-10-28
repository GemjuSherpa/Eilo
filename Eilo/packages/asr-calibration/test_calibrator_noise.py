import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import noise_pilot as n
import noise_pilot_report as report


def fixture():
    clean=n.read(n.HERE/'results.json');native=clean['native']
    reports={str(s):copy.deepcopy(native) for s in (20,10,0)}
    for i,r in enumerate(reports.values()):r['provenance']['manifest_sha256']=str(i+1)*64
    suite=n.read(n.CORPUS/'noise-results/suite.json')
    suite.update(clean_manifest_sha256=native['provenance']['manifest_sha256'],reports={s:report.canonical_file_hash(r) for s,r in reports.items()})
    return dict(schema_version=1,purpose=n.policy()['purpose'],protocol_sha256=n.sha(n.HERE/'noise-protocol.json'),protocol_commit='a'*40,
        source_pins=n.noise_pins(),calibrator_freeze_sha256=n.sha(n.HERE/'freeze.json'),clean_pilot_sha256=n.sha(n.HERE/'results.json'),
        private_model_sha256=n.read(n.HERE/'freeze.json')['private_model_sha256'],suite=suite,reports=reports,
        mapped={str(s):copy.deepcopy(clean['test']) for s in (20,10,0)},pairing=n.policy()['pairing'],
        calibrator_refit='NOT_PERFORMED',threshold_fitting='NOT_PERFORMED',native_calibration='NOT_ESTABLISHED',
        threshold_authorization='NOT_GRANTED',production='NOT_ENABLED',physical='NOT_RUN')


class NoisePilotTests(unittest.TestCase):
    def test_comparable_correlated_fixture_and_denominators(self):
        summary=report.validate(fixture());self.assertEqual(len(summary['rows']),8)
        self.assertEqual([r['condition'] for r in summary['rows']],['clean','clean','20','20','10','10','0','0'])
        for row in summary['rows']:self.assertEqual(row['mapped_coverage'],row['mapped_accepted']/30)

    def test_refit_new_holdout_or_acceptance_promotion_denied(self):
        for key,value in [('calibrator_refit','PERFORMED'),('threshold_fitting','PERFORMED'),('pairing','INDEPENDENT_HOLDOUT'),
                          ('native_calibration','ESTABLISHED'),('threshold_authorization','GRANTED'),('production','ENABLED'),('physical','PASS')]:
            changed=fixture();changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):report.validate(changed)

    def test_source_model_baseline_and_native_hash_tamper_denied(self):
        for mutate in [lambda r:r['source_pins'].clear(),lambda r:r.update(private_model_sha256='0'*64),lambda r:r.update(clean_pilot_sha256='0'*64),
                       lambda r:r['reports']['20'].update(status='other'),lambda r:r['suite']['reports'].update({'0':'0'*64})]:
            changed=fixture();mutate(changed)
            with self.assertRaises(ValueError):report.validate(changed)

    def test_missing_snr_and_metric_changes_denied(self):
        for mutate in [lambda r:r['mapped'].pop('0'),lambda r:r['reports'].pop('10'),
                       lambda r:r['mapped']['20'][0]['mapped'].update(brier_score=.999)]:
            changed=fixture();mutate(changed)
            with self.assertRaises(ValueError):report.validate(changed)

    def test_private_model_and_committed_protocol_are_required(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'fake.json';p.write_text('{}')
            with self.assertRaises(ValueError):n.model(p)
        with self.assertRaises(ValueError):n.committed_protocol('bad-commit')
        with patch.object(n.subprocess,'run'),patch.object(n.subprocess,'check_output',return_value=b'changed'),self.assertRaises(ValueError):n.committed_protocol('a'*40)

    def test_export_closed_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'report';report.export(fixture(),out)
            self.assertNotIn('/Users/',(out/'summary.json').read_text());self.assertIn('not new holdout',(out/'summary.html').read_text())
            with self.assertRaises(ValueError):report.export(fixture(),out)

    @unittest.skipUnless((n.HERE/'noise-results.json').exists(),'native noise run not yet completed')
    def test_recorded_noise_results_remain_unqualified(self):
        summary=report.validate(n.read(n.HERE/'noise-results.json'))
        self.assertEqual(len(summary['rows']),8);self.assertEqual(summary['native_calibration'],'NOT_ESTABLISHED')


if __name__=='__main__':unittest.main()
