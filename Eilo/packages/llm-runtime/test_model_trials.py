import copy
import json
from pathlib import Path
import unittest
from validate_model_trials import validate


class EvidenceTests(unittest.TestCase):
    def report(self):
        return json.loads((Path(__file__).parent / 'tests/physical-model-comparison.json').read_text())

    def test_unrun_cannot_contain_metrics(self):
        report = self.report()
        self.assertTrue(validate(report))
        report['platforms'][0]['first_token_ms'] = 0
        with self.assertRaises(ValueError):
            validate(report)

    def test_desktop_single_candidate_and_forbidden_background_rejected(self):
        report = self.report()
        report['status'] = 'MEASURED'
        row = report['platforms'][0]
        row.update(hardware_kind='physical', hardware_model='synthetic model', os_build='synthetic OS')
        row['models'] = [{'id': name, 'sha256': 'a' * 64, 'bytes': 4, 'license_evidence': 'synthetic', 'runtime_revision': 'synthetic'} for name in ('qwen3-1.7b-q4-k-m', 'qwen3-0.6b-q4-k-m')]
        row['samples'] = [{'model_id': m['id'], 'fixture_id': 'compare-01', 'backends': 'CPU only', 'enable_thinking': False, 'context_tokens': 4096, 'output_tokens': 8, 'execution_mode': 'foreground', 'memory_method': 'native_OS_peak_footprint', 'network_observation': 'NO_TRAFFIC_VERIFIED', 'prefill_ms': 10, 'first_token_ms': 12, 'peak_memory_bytes': 100, 'rated_by': 'Gemju Sherpa', 'quality': 4} for m in row['models']]
        self.assertTrue(validate(report))  # Schema fixture only, not a trial.
        for mutation in ('desktop', 'single', 'background'):
            bad = copy.deepcopy(report)
            if mutation == 'desktop':
                bad['platforms'][0]['hardware_kind'] = 'desktop'
            elif mutation == 'single':
                bad['platforms'][0]['models'].pop()
            else:
                bad['platforms'][0]['samples'][0]['execution_mode'] = 'permitted_background'
            with self.assertRaises(ValueError):
                validate(bad)


if __name__ == '__main__':
    unittest.main()
