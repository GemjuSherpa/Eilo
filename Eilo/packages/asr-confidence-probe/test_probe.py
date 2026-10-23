import copy
import json
import pathlib
import subprocess
import tempfile
import unittest

import report

HERE = pathlib.Path(__file__).resolve().parent


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((HERE / 'android-results.json').read_text())

    def test_actual_report(self):
        self.assertEqual(report.validate(self.data)['cases'], 6)

    def test_rejects_promotion(self):
        for key, value in [('calibrated', True), ('policy_authorized', True), ('physical', 'PASS')]:
            bad = copy.deepcopy(self.data); bad[key] = value
            with self.assertRaises(ValueError): report.validate(bad)

    def test_rejects_stale_source_model_and_fixtures(self):
        bad = copy.deepcopy(self.data); bad['source_pins']['main.cpp'] = '0' * 64
        with self.assertRaises(ValueError): report.validate(bad)
        for field in ['model_provenance_sha256', 'fixtures_sha256', 'ort_sha256']:
            bad = copy.deepcopy(self.data); bad[field] = '0' * 64
            with self.assertRaises(ValueError): report.validate(bad)

    def test_rejects_invalid_scores(self):
        for value in [float('nan'), float('inf'), -0.1, 1.1, True, '0.9']:
            bad = copy.deepcopy(self.data); bad['cases'][0]['mean_probability'] = value
            with self.assertRaises(ValueError): report.validate(bad)

    def test_rejects_missing_duplicate_and_failed_draft(self):
        for mutation in [lambda r: r['cases'].pop(), lambda r: r['cases'].append(r['cases'][0]), lambda r: r['cases'][0].update(draft_verified=False), lambda r: r['cases'][0].update(corrupted_draft_rejected=False)]:
            bad = copy.deepcopy(self.data); mutation(bad)
            with self.assertRaises(ValueError): report.validate(bad)

    def test_rejects_transcript_fields(self):
        for target in ['root', 'case']:
            bad = copy.deepcopy(self.data)
            (bad if target == 'root' else bad['cases'][0])['transcript'] = 'private'
            with self.assertRaises(ValueError): report.validate(bad)

    def test_native_softmax_extremes_and_invalid_input(self):
        code = r'''
#include "probability.h"
#include <limits>
int main() {
 float equal[]={1000,1000}; require(std::abs(probability(equal,2,0)-0.5)<1e-12);
 float shifted[]={-1000,-1000}; require(probability(shifted,2,1)==0.5);
 float extreme[]={10000,-10000}; require(probability(extreme,2,0)==1);
 float nan[]={std::numeric_limits<float>::quiet_NaN()};
 bool rejected=false; try { probability(nan,1,0); } catch(const std::exception&) { rejected=true; } require(rejected);
 rejected=false; try { probability(equal,2,2); } catch(const std::exception&) { rejected=true; } require(rejected);
 rejected=false; try { best(equal,0); } catch(const std::exception&) { rejected=true; } require(rejected);
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp); (path / 'test.cpp').write_text(code)
            subprocess.run(['c++', '-std=c++20', '-I', str(HERE), str(path / 'test.cpp'), '-o', str(path / 'test')], check=True, capture_output=True)
            subprocess.run([str(path / 'test')], check=True, capture_output=True)


if __name__ == '__main__': unittest.main()
