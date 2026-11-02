import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_validation_v2 as runner
from audit_v2 import SOURCES


def response_for(source, transcript='private validation hypothesis'):
    origins = {'greedy': 1, 'verification': 0, 'redecode': 0}
    if source == SOURCES[1]:
        origins = {'greedy': 0, 'verification': 1, 'redecode': 0}
    return {'source': source, 'status': 'AVAILABLE', 'transcript': transcript,
            'tokens': 1, 'confidence': 0.9, 'geometric_mean': 0.9, 'minimum': 0.9,
            'oracle_error': 0.0, 'origins': origins}


class ValidationRunnerV2Tests(unittest.TestCase):
    def test_validation_attempt_document_has_fixed_stage_and_source_order(self):
        case_ids = [f'{index:024x}' for index in range(200)]
        rows = [runner.common.unavailable_rows(case_id) for case_id in case_ids]
        document = runner.build_validation_attempt_document(case_ids, rows)
        self.assertEqual(document['stage'], 'VALIDATION')
        self.assertEqual(document['case_ids'], case_ids)
        self.assertEqual([row['source'] for row in document['sources']], list(SOURCES))
        self.assertEqual(len(document['sources'][0]['attempts']), 200)
        self.assertNotIn('hypothesis', json.dumps(document))

    def test_validation_document_rejects_incomplete_or_reordered_cases(self):
        case_ids = [f'{index:024x}' for index in range(200)]
        rows = [runner.common.unavailable_rows(case_id) for case_id in case_ids]
        with self.assertRaisesRegex(ValueError, '200 unique cases'):
            runner.build_validation_attempt_document(case_ids[:-1], rows[:-1])
        rows[0][SOURCES[0]]['case_id'] = case_ids[-1]
        with self.assertRaisesRegex(ValueError, 'manifest order'):
            runner.build_validation_attempt_document(case_ids, rows)

    def test_response_conversion_preserves_only_private_rows_and_unavailable_status(self):
        case_id = 'a' * 24
        response = {'schema_version': 1, 'paths': [
            response_for(SOURCES[0]),
            {'source': SOURCES[1], 'status': 'UNAVAILABLE', 'reason': 'COLLECTOR_ERROR'},
        ]}
        rows = runner.common.rows_from_response(case_id, response)
        self.assertEqual(rows[SOURCES[1]], {'case_id': case_id, 'status': 'UNAVAILABLE'})
        self.assertEqual(set(rows[SOURCES[0]]), {'case_id', 'status', 'score', 'hypothesis'})
        self.assertNotIn('reason', rows[SOURCES[1]])

    def test_selection_validation_loader_binds_only_frozen_validation_phase(self):
        selection_path = runner.LOCAL / 'asr-calibration-audit-v2/selection-private.json'
        freeze = {
            'purpose': 'S05_VC_TURN_10_SELECTION_FREEZE',
            'phase_manifest_sha256': {
                phase: f'{phase}-hash' for phase in runner.PHASES
            },
            'decoder': {'kind': 'ffmpeg', 'sha256': 'd' * 64},
        }
        with tempfile.TemporaryDirectory() as directory:
            freeze_path = Path(directory) / 'freeze.json'
            freeze_path.write_text(json.dumps(freeze), encoding='utf-8')
            with patch.object(runner, 'load_private_selection') as load:
                inventory = {'phases': {phase: {'manifest_sha256': f'{phase}-hash'}
                                       for phase in runner.PHASES}}
                manifests = {phase: {'cases': []} for phase in runner.PHASES}
                manifests['validation']['cases'] = [
                    {'id': f'{index:024x}', 'split': 'validation', 'task': 'asr'}
                    for index in range(200)
                ]
                load.return_value = (inventory, manifests, 'ffmpeg', 'd' * 64)
                with patch.object(runner, 'SELECTION_FREEZE_PATH', Path('/tmp/freeze.json')):
                    _, manifest = runner.load_validation_cases(selection_path, freeze_path)
        self.assertEqual(len(manifest['cases']), 200)
        self.assertTrue(all(case['split'] == 'validation' for case in manifest['cases']))

    def test_main_requires_mapping_freeze_and_only_validation_runner_options(self):
        with patch('sys.argv', ['run_validation_v2.py', '--help']), \
                self.assertRaises(SystemExit) as exit_info:
            runner.main()
        self.assertEqual(exit_info.exception.code, 0)


if __name__ == '__main__':
    unittest.main()
