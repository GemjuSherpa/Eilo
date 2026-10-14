import copy
import unittest
from benchmark import aggregate, distance, normalize, report, score_case, vad_counts
from manifests import canonical_digest


def fixture(task='asr'):
    case = {'id': 'a' * 24, 'task': task, 'reference': 'yes stop', 'command': 'yes',
            'vad': [[0, 0.5]], 'samples': 16000, 'slice': 'synthetic', 'split': 'test'}
    manifest = {'schema_version': 1, 'rate': 16000, 'kind': 'synthetic', 'dataset': 'synthetic',
                'release': '1', 'cases': [case]}
    adapter = {'kind': 'synthetic', 'name': 'fixture', 'binary_sha256': 'b' * 64,
               'model_sha256': 'c' * 64, 'config_sha256': 'd' * 64}
    value = {'schema_version': 1, 'manifest_sha256': canonical_digest(manifest), 'adapter': adapter,
             'cases': [{'id': case['id'], 'transcript': 'yes', 'command': 'yes',
                        'vad': [[0.25, 0.75]], 'seconds': 0.2}]}
    return manifest, value


class BenchmarkTests(unittest.TestCase):
    def test_hand_computed_edit_distance(self):
        self.assertEqual(normalize('YES, STOP!'), 'yes stop')
        self.assertEqual(distance(['a', 'b'], ['a', 'c', 'd']), 2)
        manifest, value = fixture()
        result = report(manifest, value)
        self.assertEqual(result['metrics']['wer'], 0.5)
        self.assertEqual(result['metrics']['cer'], 5 / 8)
        self.assertEqual(result['metrics']['rtf'], 0.2)
        self.assertNotIn('transcript', result['cases'][0])

    def test_micro_not_mean_wer(self):
        cases = [{'word_errors': 1, 'reference_words': 1, 'character_errors': 1,
                  'reference_characters': 1, 'seconds': 1, 'audio_seconds': 1},
                 {'word_errors': 0, 'reference_words': 9, 'character_errors': 0,
                  'reference_characters': 9, 'seconds': 1, 'audio_seconds': 1}]
        self.assertEqual(aggregate(cases)['wer'], 0.1)

    def test_vad_overlap_and_negative_only(self):
        self.assertEqual(vad_counts([[0, 0.5]], [[0.25, 0.75]], 1),
                         {'tp': 13, 'fp': 12, 'fn': 12, 'tn': 13})
        manifest, value = fixture('vad')
        manifest['cases'][0]['vad'] = []
        value['manifest_sha256'] = canonical_digest(manifest)
        result = report(manifest, value)
        self.assertIsNone(result['metrics']['vad_miss_rate'])
        self.assertEqual(result['physical_gates']['screen_off'], 'NOT_RUN')
        for invalid in ([[0.5, 1.1]], [[0, 0.5], [0.4, 0.6]], [[float('nan'), 1]]):
            with self.assertRaises(ValueError):
                vad_counts([], invalid, 1)

    def test_absent_adapter_not_run(self):
        manifest, _ = fixture()
        self.assertEqual(report(manifest)['status'], 'NOT_RUN')

    def test_wrong_corpus_missing_duplicates_and_nan(self):
        manifest, good = fixture()
        for change in ('hash', 'missing', 'duplicate', 'nan'):
            value = copy.deepcopy(good)
            if change == 'hash': value['manifest_sha256'] = '0' * 64
            if change == 'missing': value['cases'] = []
            if change == 'duplicate': value['cases'] *= 2
            if change == 'nan': value['cases'][0]['seconds'] = float('nan')
            with self.assertRaises(ValueError):
                report(manifest, value)

    def test_commands_unknown_and_synthetic_protection(self):
        manifest, value = fixture('commands')
        self.assertEqual(report(manifest, value)['metrics']['command_accuracy'], 1)
        manifest['kind'] = 'public_corpus'
        value['manifest_sha256'] = canonical_digest(manifest)
        with self.assertRaises(ValueError):
            report(manifest, value)
