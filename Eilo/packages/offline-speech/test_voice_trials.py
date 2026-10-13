import copy
import json
from pathlib import Path
import unittest
from validate_voice_trials import validate


class EvidenceTests(unittest.TestCase):
    def test_unrun_cannot_manufacture_results(self):
        report = json.loads((Path(__file__).parent / 'tests/physical-voice-trials.json').read_text())
        self.assertTrue(validate(report))
        report['platforms'][0]['first_audible_ms'] = 0
        with self.assertRaises(ValueError):
            validate(report)

    def test_sdk_start_and_simulator_cannot_be_physical_evidence(self):
        report = json.loads((Path(__file__).parent / 'tests/physical-voice-trials.json').read_text())
        report['status'] = 'MEASURED'
        row = report['platforms'][0]
        row.update(hardware_kind='physical', hardware_model='synthetic fixture', os_build='synthetic build', installed_voices=[{'id': 'fixture', 'installed': True}])
        row['samples'] = [{'voice_id': 'fixture', 'fixture_id': 'voice-01', 'airplane_mode': True, 'wifi_enabled': False, 'network_observation': 'NO_TRAFFIC_VERIFIED', 'first_audible_method': 'independent_local_audio_timestamp', 'first_audible_ms': 100, 'rated_by': 'Gemju Sherpa', 'intelligibility': 4}]
        self.assertTrue(validate(report))  # Synthetic schema fixture, never a trial result.
        bad = copy.deepcopy(report)
        bad['platforms'][0]['samples'][0]['first_audible_method'] = 'SDK_onStart'
        with self.assertRaises(ValueError):
            validate(bad)
        row['hardware_kind'] = 'simulator'
        with self.assertRaises(ValueError):
            validate(report)


if __name__ == '__main__':
    unittest.main()
