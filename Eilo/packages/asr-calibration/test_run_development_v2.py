import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import run_development_v2 as runner
from audit_v2 import SOURCES


def available(source, transcript='a private hypothesis'):
    origins = {'greedy': 1, 'verification': 0, 'redecode': 0}
    if source == SOURCES[1]:
        origins = {'greedy': 0, 'verification': 1, 'redecode': 0}
    return {'source': source, 'status': 'AVAILABLE', 'transcript': transcript,
            'tokens': 1, 'confidence': 0.9, 'geometric_mean': 0.9, 'minimum': 0.9,
            'oracle_error': 0.0, 'origins': origins}


class DevelopmentRunnerV2Tests(unittest.TestCase):
    def test_pcm16_conversion_is_little_endian_and_normalized(self):
        pcm = struct.pack('<hhh', -32768, 0, 32767)
        floats = runner.pcm16_to_float32(pcm)
        values = struct.unpack('<fff', floats)
        self.assertEqual(values[0], -1.0)
        self.assertEqual(values[1], 0.0)
        self.assertAlmostEqual(values[2], 32767 / 32768)
        for bad in (b'', b'x', struct.pack('<h', 1)):
            with self.assertRaises(ValueError):
                runner.pcm16_to_float32(bad, sample_rate=8000 if bad else 16000)

    def test_attempt_rows_keep_only_scores_and_local_hypotheses(self):
        case_id = 'a' * 24
        response = {'schema_version': 1, 'paths': [
            available(SOURCES[0]),
            {'source': SOURCES[1], 'status': 'UNAVAILABLE', 'reason': 'COLLECTOR_ERROR'},
        ]}
        rows = runner.rows_from_response(case_id, response)
        self.assertEqual(list(rows), list(SOURCES))
        self.assertEqual(rows[SOURCES[0]], {
            'case_id': case_id, 'status': 'AVAILABLE', 'score': 0.9,
            'hypothesis': 'a private hypothesis',
        })
        self.assertEqual(rows[SOURCES[1]], {'case_id': case_id, 'status': 'UNAVAILABLE'})
        self.assertNotIn('reason', rows[SOURCES[1]])
        self.assertNotIn('exact_match', rows[SOURCES[0]])

    def test_attempt_document_is_fixed_to_ordered_development_only_rows(self):
        case_ids = [f'{index:024x}' for index in range(200)]
        rows_by_case = [runner.unavailable_rows(case_id) for case_id in case_ids]
        document = runner.build_attempt_document(case_ids, rows_by_case)
        self.assertEqual(set(document), {'schema_version', 'stage', 'case_ids', 'sources'})
        self.assertEqual(document['stage'], 'DEVELOPMENT')
        self.assertEqual([row['source'] for row in document['sources']], list(SOURCES))
        self.assertEqual([row['case_id'] for row in document['sources'][0]['attempts']], case_ids)
        self.assertEqual(set(document['sources'][0]['attempts'][0]), {'case_id', 'status'})
        with self.assertRaisesRegex(ValueError, '200 unique cases'):
            runner.build_attempt_document(case_ids[:-1], rows_by_case[:-1])

    def test_commit_blob_verification_requires_full_ancestor_commit(self):
        payload = b'committed freeze\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'freeze.json'
            path.write_bytes(payload)
            with patch.object(runner.subprocess, 'run') as run, \
                    patch.object(runner.subprocess, 'check_output', return_value=payload):
                digest = runner.verify_committed_blob('a' * 40, 'Eilo/freeze.json', path)
            run.assert_called_once()
            self.assertEqual(len(digest), 64)
            with patch.object(runner.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'full reviewed commit'):
                    runner.verify_committed_blob('abc', 'Eilo/freeze.json', path)
                run.assert_not_called()

    def test_booted_simulator_requires_matching_available_booted_device(self):
        payload = json.dumps({'devices': {'iOS 27.0': [
            {'udid': 'one', 'state': 'Booted', 'isAvailable': True},
            {'udid': 'two', 'state': 'Shutdown', 'isAvailable': True},
            {'udid': 'three', 'state': 'Booted', 'isAvailable': False},
        ]}})
        result = type('Result', (), {'stdout': payload})()
        with patch.object(runner.subprocess, 'run', return_value=result):
            self.assertTrue(runner.booted_simulator('one'))
            self.assertFalse(runner.booted_simulator('two'))
            self.assertFalse(runner.booted_simulator('three'))

    def test_private_output_is_create_only_and_permissions_are_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'attempts.json'
            value = {'stage': 'DEVELOPMENT', 'private': 'hypothesis'}
            runner.exclusive_json(path, value)
            original = path.read_bytes()
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                runner.exclusive_json(path, {'stage': 'VALIDATION'})
            self.assertEqual(path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
