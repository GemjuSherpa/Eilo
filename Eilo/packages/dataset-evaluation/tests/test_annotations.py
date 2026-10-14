import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from annotations import DECLARATION, apply_review, draft, prepare, validate_reviewed_manifest
from audio import RATE, write_wav
from benchmark import report
from manifests import canonical_digest, sha256
from test_benchmark import fixture


def reviewed(manifest):
    value = draft(manifest)
    value.update(status='REVIEWED', reviewer='synthetic-test-reviewer',
                 reviewed_at='2020-01-01T00:00:00Z', declaration=DECLARATION)
    for case in value['cases']:
        case.update(status='REVIEWED', intervals_samples=[[160, 8000]])
    return value


class AnnotationTests(unittest.TestCase):
    def setUp(self):
        self.manifest, self.predictions = fixture('vad')
        self.manifest['cases'][0]['pcm_sha256'] = 'c' * 64
        self.review = reviewed(self.manifest)

    def test_round_trip_and_no_speech_are_explicit(self):
        result = apply_review(self.manifest, self.review)
        validate_reviewed_manifest(result)
        self.assertEqual(result['cases'][0]['vad'], [[.01, .5]])
        self.assertNotIn('reference', result['cases'][0])
        self.review['cases'][0]['intervals_samples'] = []
        result = apply_review(self.manifest, self.review)
        validate_reviewed_manifest(result)
        self.assertEqual(result['cases'][0]['vad'], [])

    def test_draft_uncertainty_missing_identity_and_model_labels_rejected(self):
        for field, value in [('status', 'DRAFT'), ('method', 'MODEL_PREDICTION'),
                             ('reviewer', ''), ('reviewer', 'person@example.com'),
                             ('reviewed_at', '2020-01-01'),
                             ('reviewed_at', '2999-01-01T00:00:00Z'), ('declaration', '')]:
            changed = copy.deepcopy(self.review); changed[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                apply_review(self.manifest, changed)
        changed = copy.deepcopy(self.review); changed['cases'][0]['status'] = 'UNCERTAIN'
        with self.assertRaises(ValueError): apply_review(self.manifest, changed)

    def test_binding_and_completeness_rejected(self):
        for field, value in [('id', 'f'*24), ('samples', 123), ('pcm_sha256', 'd'*64)]:
            changed = copy.deepcopy(self.review); changed['cases'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                apply_review(self.manifest, changed)
        for rows in ([], self.review['cases']*2):
            changed = copy.deepcopy(self.review); changed['cases'] = rows
            with self.assertRaises(ValueError): apply_review(self.manifest, changed)
        changed = copy.deepcopy(self.manifest); changed['release'] = 'changed'
        with self.assertRaises(ValueError): apply_review(changed, self.review)

    def test_sample_endpoints_strict_and_finite(self):
        for pairs in ([[True, 4]], [[0.1, 2]], [[-1, 4]], [[0, 16001]],
                      [[5, 5]], [[0, 10], [9, 20]], [[20, 30], [0, 10]],
                      [[0, float('nan')]], [[0]], 'bad'):
            changed = copy.deepcopy(self.review); changed['cases'][0]['intervals_samples'] = pairs
            with self.subTest(pairs=pairs), self.assertRaises(ValueError):
                apply_review(self.manifest, changed)

    def test_review_hash_and_derived_intervals_cannot_drift(self):
        result = apply_review(self.manifest, self.review)
        for mutation in ('hash', 'interval', 'pcm'):
            changed = copy.deepcopy(result)
            if mutation == 'hash': changed['annotation_review']['reviewer'] = 'changed'
            if mutation == 'interval': changed['cases'][0]['vad'] = []
            if mutation == 'pcm': changed['cases'][0]['pcm_sha256'] = 'd'*64
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_reviewed_manifest(changed)

    def test_public_marker_alone_cannot_unlock_score(self):
        manifest = copy.deepcopy(self.manifest); manifest['kind'] = 'public_corpus'
        manifest['cases'][0]['annotation_status'] = 'REVIEWED_TIME_ALIGNED'
        self.predictions['adapter']['kind'] = 'native'
        self.predictions['manifest_sha256'] = canonical_digest(manifest)
        with self.assertRaisesRegex(ValueError, 'bound human annotation'):
            report(manifest, self.predictions)
        # Fixture declarations exercise the gate; this is no public-data measurement.
        manifest = apply_review(manifest, reviewed(manifest))
        self.predictions['manifest_sha256'] = canonical_digest(manifest)
        self.assertEqual(report(manifest, self.predictions)['status'], 'MEASURED')

    def test_pack_blinding_script_hash_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); wav = root/'audio.wav'
            case = self.manifest['cases'][0]
            case.update(path='audio.wav', pcm_sha256=write_wav(wav, [0]*RATE), sha256=sha256(wav),
                        reference='SECRET_TRANSCRIPT', speaker='SECRET_SPEAKER', slice='SECRET_CATEGORY')
            out = root/'pack'; value = prepare(self.manifest, root, out)
            html = (out/'review.html').read_text()
            for hidden in ('SECRET_TRANSCRIPT','SECRET_SPEAKER','SECRET_CATEGORY',str(root)):
                self.assertNotIn(hidden, html)
            self.assertEqual(value['status'], 'DRAFT')
            self.assertEqual(value['cases'][0]['status'], 'UNREVIEWED')
            script = html.split('<script>')[1].split('</script>')[0]
            digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
            self.assertIn("'sha256-"+digest+"'", html)
            self.assertIn("connect-src 'none'", html)
            self.assertNotIn('__PACK__', html)
            with self.assertRaises(ValueError): prepare(self.manifest, root, out)

    def test_unknown_fields_cannot_smuggle_transcripts_or_model_outputs(self):
        changed = copy.deepcopy(self.review); changed['transcript'] = 'hidden'
        with self.assertRaises(ValueError): apply_review(self.manifest, changed)
        changed = copy.deepcopy(self.review); changed['cases'][0]['model_prediction'] = []
        with self.assertRaises(ValueError): apply_review(self.manifest, changed)
