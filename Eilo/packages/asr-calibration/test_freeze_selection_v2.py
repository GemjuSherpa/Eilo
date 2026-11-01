import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import freeze_selection_v2 as freeze
from shared import canonical_digest


class SelectionFreezeV2Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.selection_path = self.root / 'selection-private.json'
        self.decoder_sha = 'a' * 64
        self.source_pins = {'select_audit_v2.py': 'b' * 64}
        phases = {}
        for phase in freeze.PHASES:
            split = 'validation' if phase == 'validation' else 'test'
            cases = [{'id': f'{index:024x}', 'task': 'asr', 'split': split,
                      'reference': f'private transcript {index}',
                      'speaker': f'{index:024x}', 'source_sha256': 'c' * 64,
                      'pcm_sha256': 'd' * 64}
                     for index in range(200)]
            manifest = {
                'schema_version': 1,
                'kind': 'public_corpus',
                'dataset': 'common_voice',
                'release': '26.0-2026-06-12-en-AU-MDC-2026-07-20',
                'rate': 16000,
                'recipe': 'pcm16-mono-area-downsample-linear-upsample-v1',
                'decoder_kind': 'ffmpeg',
                'decoder_sha256': self.decoder_sha,
                'receipt_sha256': 'e' * 64,
                'seed': 20261030,
                'cases': cases,
            }
            directory = self.root / phase
            directory.mkdir()
            (directory / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            phases[phase] = {'cases': 200, 'manifest_sha256': canonical_digest(manifest)}
        self.inventory = {
            'schema_version': 1,
            'purpose': freeze.SELECTION_PURPOSE,
            'protocol_sha256': freeze.sha256(freeze.PROTOCOL),
            'source_pins': self.source_pins,
            'archive_sha256': 'f' * 64,
            'receipt_sha256': 'e' * 64,
            'prior_manifest_sha256': ['1' * 64, '2' * 64, '3' * 64, '4' * 64],
            'excluded_prior_cases': 120,
            'phases': phases,
            'cross_phase_id_overlap': 0,
            'cross_phase_text_overlap': 0,
            'prior_id_text_source_pcm_overlap': 0,
            'model_training_overlap': 'UNKNOWN',
            'frozen_before_inference': True,
            'inference': 'NOT_RUN',
            'native_calibration': 'NOT_ESTABLISHED',
            'threshold_authorization': 'NOT_GRANTED',
            'production': 'NOT_ENABLED',
            'physical': 'NOT_RUN',
        }
        self.selection_path.write_text(json.dumps(self.inventory), encoding='utf-8')

    def patch_pins(self):
        return patch.object(freeze, 'selection_pins', return_value=self.source_pins)

    def test_public_freeze_contains_hashes_and_no_private_rows(self):
        with self.patch_pins(), patch.object(freeze, 'validate_manifest') as validate:
            public = freeze.public_freeze(self.selection_path)
        self.assertEqual(validate.call_count, 3)
        self.assertEqual(public['purpose'], freeze.FREEZE_PURPOSE)
        self.assertEqual(public['phase_manifest_sha256'], {
            phase: self.inventory['phases'][phase]['manifest_sha256'] for phase in freeze.PHASES
        })
        self.assertEqual(public['decoder'], {'kind': 'ffmpeg', 'sha256': self.decoder_sha})
        self.assertTrue(public['frozen_before_inference'])
        self.assertEqual(public['inference'], 'NOT_RUN')
        serialized = json.dumps(public)
        self.assertNotIn('private transcript', serialized)
        self.assertNotIn('speaker', serialized)
        self.assertNotIn('source_sha256', serialized)
        self.assertNotIn('pcm_sha256', serialized)

    def test_changed_private_manifest_or_code_pin_fails_closed(self):
        manifest_path = self.root / 'audit/manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['cases'][0]['reference'] = 'changed private transcript'
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        with self.patch_pins(), patch.object(freeze, 'validate_manifest'):
            with self.assertRaisesRegex(ValueError, 'private manifest differs'):
                freeze.public_freeze(self.selection_path)

        manifest_path.write_text(json.dumps({**manifest, 'cases': [
            {'id': f'{index:024x}', 'task': 'asr', 'split': 'test',
             'reference': f'private transcript {index}', 'speaker': f'{index:024x}',
             'source_sha256': 'c' * 64, 'pcm_sha256': 'd' * 64}
            for index in range(200)
        ]}), encoding='utf-8')
        with self.patch_pins(), patch.object(freeze, 'validate_manifest'):
            self.inventory['source_pins'] = {'changed.py': '0' * 64}
            self.selection_path.write_text(json.dumps(self.inventory), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'code pins changed'):
                freeze.public_freeze(self.selection_path)

    def test_inference_must_remain_unrun_and_phase_decoder_must_match(self):
        self.inventory['inference'] = 'RUN'
        self.selection_path.write_text(json.dumps(self.inventory), encoding='utf-8')
        with self.patch_pins(), patch.object(freeze, 'validate_manifest'):
            with self.assertRaisesRegex(ValueError, 'frozen before inference'):
                freeze.public_freeze(self.selection_path)

    def test_public_freeze_is_create_only(self):
        output = self.root / 'selection-freeze-v2.json'
        with self.patch_pins(), patch.object(freeze, 'validate_manifest'), \
                patch.object(freeze, 'SELECTION_FREEZE_PATH', output):
            freeze.write_public_freeze(self.selection_path, output)
            first = output.read_bytes()
            with self.assertRaises(FileExistsError):
                freeze.write_public_freeze(self.selection_path, output)
            self.assertEqual(output.read_bytes(), first)


if __name__ == '__main__':
    unittest.main()
