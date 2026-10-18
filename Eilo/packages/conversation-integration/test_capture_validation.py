"""No models/SDK: reject incomplete, content-bearing or false joined acceptance reports."""
import unittest
from check_capture_ios import validate


def result():
    rows = []
    for phase in ('speech16', 'followup48', 'quiet'):
        positive = phase != 'quiet'
        rows.append(dict(case=phase, recognized=int(positive), llm_starts=int(positive), metadata=1,
            normalized_samples=29184 if positive else 80000, reply_submitted=positive, completed=positive,
            transcript_sha256='a' * 64 if positive else '', context_messages=2 if phase == 'speech16' else 4,
            inference_worker_verified=True))
    return dict(scope='IOS_SIMULATOR_SIGNED_CAPTURE_REPLY', physical='NOT_RUN', production='NOT_ENABLED',
        microphone='NOT_USED', confidence='SYNTHETIC_0_95', voice_evidence='SYNTHETIC_EXACT_VOICE_OS',
        temporary_pack_removed=True, cases=rows)


class JoinedCaptureValidation(unittest.TestCase):
    def test_complete_synthetic_scope(self):
        validate(result())
        for key, value in [('physical', 'PASS'), ('production', 'ENABLED'), ('confidence', 'CALIBRATED'),
                           ('temporary_pack_removed', False), ('transcript', 'unexpected')]:
            bad = result(); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): validate(bad)

    def test_real_capture_reply_context_and_quiet_required(self):
        for index, key, value in [(0, 'recognized', 0), (1, 'llm_starts', 0), (0, 'metadata', 0), (1, 'normalized_samples', 0),
            (1, 'context_messages', 2), (2, 'reply_submitted', True), (2, 'recognized', 1),
            (2, 'transcript_sha256', 'a'*64), (1, 'inference_worker_verified', False),
            (0, 'recognized', True), (0, 'raw_audio', 'unexpected')]:
            bad = result(); bad['cases'][index][key] = value
            with self.subTest(index=index, key=key), self.assertRaises(ValueError): validate(bad)
        bad = result(); bad['cases'][1]['transcript_sha256'] = 'b' * 64
        with self.assertRaises(ValueError): validate(bad)

    def test_exact_case_coverage(self):
        for rows in ([], result()['cases'][:2], list(reversed(result()['cases']))):
            bad = result(); bad['cases'] = rows
            with self.assertRaises(ValueError): validate(bad)


if __name__ == '__main__':
    unittest.main()
