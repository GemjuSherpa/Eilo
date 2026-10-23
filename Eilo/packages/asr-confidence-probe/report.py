"""Validate pinned, synthetic-only prototype evidence without executing native code."""
import hashlib
import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def validate(report):
    def require(condition):
        if not condition:
            raise ValueError('invalid or stale confidence prototype evidence')
    require(set(report) == {'version', 'status', 'platform', 'calibrated', 'policy_authorized', 'physical', 'source_commit', 'source_pins', 'binary_sha256', 'ort_sha256', 'cxx_sha256', 'model_provenance_sha256', 'fixtures_sha256', 'rejected_inputs', 'cases'})
    require(report['version'] == 1 and report['status'] == 'SYNTHETIC_DIAGNOSTIC_ONLY')
    require(report['calibrated'] is False and report['policy_authorized'] is False and report['physical'] == 'NOT_RUN')
    require(report['platform'] == 'Android API35 ARM64 emulator')
    manifest = json.loads((HERE / 'source-manifest.json').read_text())
    require(report['source_commit'] == manifest['commit'])
    expected = ['main.cpp', 'probability.h', 'CMakeLists.txt', 'check_android.py', 'source-manifest.json']
    require(set(report['source_pins']) == set(expected))
    for name in expected:
        require(report['source_pins'][name] == hashlib.sha256((HERE / name).read_bytes()).hexdigest())
    for field, path in [('model_provenance_sha256', 'provenance.json'), ('fixtures_sha256', 'tests/fixtures.json')]:
        require(report[field] == hashlib.sha256((HERE.parent / 'asr-runtime' / path).read_bytes()).hexdigest())
    for field in ['binary_sha256', 'ort_sha256', 'cxx_sha256']:
        require(type(report[field]) is str and len(report[field]) == 64 and all(x in '0123456789abcdef' for x in report[field]))
    require(report['ort_sha256'] == '86e85022fc539963177e478c8e9a8a8219bc3b0d7515bf5297a62986dbc45e7a')
    require(report['rejected_inputs'] == ['empty', 'unaligned', 'nan', 'out_of_range'])
    fixtures = json.loads((HERE.parent / 'asr-runtime/tests/fixtures.json').read_text())['cases']
    require([case['case'] for case in report['cases']] == [case['id'] for case in fixtures])
    for case in report['cases']:
        require(set(case) == {'case', 'status', 'tokens', 'mean_probability', 'geometric_mean', 'minimum', 'maximum', 'draft_verified', 'draft_mean_probability', 'max_probability_delta', 'corrupted_draft_rejected', 'calibrated'})
        require(case['status'] == 'DIAGNOSTIC_ONLY' and case['calibrated'] is False)
        require(case['draft_verified'] is True and case['corrupted_draft_rejected'] is True)
        require(type(case['tokens']) is int and 0 < case['tokens'] < 128)
        for key in ['mean_probability', 'geometric_mean', 'minimum', 'maximum', 'draft_mean_probability', 'max_probability_delta']:
            require(type(case[key]) in (int, float) and math.isfinite(case[key]) and 0 <= case[key] <= 1)
        require(0 < case['minimum'] <= case['geometric_mean'] <= case['mean_probability'] + 1e-8 <= case['maximum'] + 1e-8 <= 1 + 1e-8)
    return {'status': 'SYNTHETIC_DIAGNOSTIC_ONLY', 'cases': len(report['cases']),
            'maximum_observed_path_delta': max(case['max_probability_delta'] for case in report['cases']),
            'calibrated': False, 'policy_authorized': False, 'physical': 'NOT_RUN'}


if __name__ == '__main__':
    print(json.dumps(validate(json.loads((HERE / 'android-results.json').read_text())), indent=2))
