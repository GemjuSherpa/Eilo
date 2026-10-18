"""No models/downloads: reject tampered cache pins and false native acceptance reports."""
import contextlib
import io
import shutil
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_installer as installer
import check_installer_evidence as evidence


def result():
    rows = []
    for phase in installer.PHASES:
        positive = phase in ('speech16', 'speech48')
        denied = phase in ('stale-ticket', 'corrupt-pack')
        asr = positive or phase in ('stop-final', 'replace-final')
        rows.append(dict(case=phase, installed=not denied, vad_opens=int(not denied), vad_closes=int(not denied),
                         vad_calls=int(not denied), asr_opens=int(asr), asr_closes=int(asr), asr_accept_calls=int(asr),
                         asr_finals=int(asr), recognized=int(positive), metadata=int(positive or phase == 'quiet'),
                         source_rate=48000 if phase == 'speech48' else 16000,
                         normalized_samples=10000 if positive else 80000 if phase == 'quiet' else 0,
                         transcript_sha256='a' * 64 if positive else ''))
    return dict(scope='IOS_SIMULATOR_SIGNED_SPEECH_INSTALLER', synthetic=True, worker_verified=True,
                physical='NOT_RUN', production='NOT_ENABLED', lab_signing='EPHEMERAL_ES256', cases=rows)


class InstallerValidation(unittest.TestCase):
    def validate(self, value):
        return installer.validate_result(value, 'IOS_SIMULATOR_SIGNED_SPEECH_INSTALLER')

    def test_complete_synthetic_result_and_missing_cases(self):
        self.validate(result())
        for change in (lambda r: r['cases'].pop(), lambda r: r['cases'].reverse(),
                       lambda r: r.update(worker_verified=False), lambda r: r.update(physical='PASS'),
                       lambda r: r.update(production='ENABLED'), lambda r: r.update(transcript='private'),
                       lambda r: r['cases'][0].update(transcript='private')):
            bad = result(); change(bad)
            with self.assertRaises(ValueError):
                self.validate(bad)

    def test_no_fabricated_positive_or_leaked_stale_result(self):
        for index, key, value in [(0, 'recognized', 0), (1, 'asr_accept_calls', 0), (2, 'asr_opens', 1),
                                  (3, 'recognized', 1), (4, 'transcript_sha256', 'b' * 64),
                                  (5, 'vad_closes', 0), (6, 'installed', True), (7, 'installed', True),
                                  (0, 'normalized_samples', True), (1, 'source_rate', 16000)]:
            bad = result(); bad['cases'][index][key] = value
            with self.subTest(index=index, key=key), self.assertRaises(ValueError):
                self.validate(bad)

    def test_pinned_artifact_tampering_and_complete_inventory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root / 'source'; source.mkdir()
            cache = root / 'cache'; cache.mkdir(); model = cache / 'models'; model.mkdir()
            digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            archive = cache / 'runtime.tar'; archive.write_bytes(b'archive')
            runtime = cache / 'library.a'; runtime.write_bytes(b'library')
            files = []
            for name in sorted(installer.NAMES):
                p = model / name; p.write_bytes(b'model')
                files.append(dict(file=name, bytes=5, local_sha256=digest(p)))
            group = dict(archive=archive.name, publisher_sha256=digest(archive),
                         files=[dict(path=runtime.name, sha256=digest(runtime))])
            record = dict(host=group, ios=copy.deepcopy(group), model=dict(directory='models', files=files))
            manifest = source / 'provenance.json'; manifest.write_text(json.dumps(record))
            with patch.object(installer, 'ASR', source):
                installer.verified_asr(cache)
                runtime.write_bytes(b'tampered')
                with self.assertRaises(ValueError): installer.verified_asr(cache)
                runtime.write_bytes(b'library'); (model / files[0]['file']).write_bytes(b'bad')
                with self.assertRaises(ValueError): installer.verified_asr(cache)
                (model / files[0]['file']).write_bytes(b'model'); record['model']['files'].pop()
                manifest.write_text(json.dumps(record))
                with self.assertRaises(ValueError): installer.verified_asr(cache)


class CommittedEvidenceValidation(unittest.TestCase):
    def test_complete_evidence_and_source_report_tampering(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = evidence.ROOT
            audit_path = Path('packages/vad-runtime/tests/signed-installer-evidence.json')
            audit = json.loads((original / audit_path).read_text())
            paths = [r['path'] for r in audit['sources'] + audit['reports']] + [str(audit_path)]
            for relative in paths:
                target = root / relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original / relative, target)
            with contextlib.redirect_stdout(io.StringIO()): evidence.validate_evidence(root)
            source = root / audit['sources'][0]['path']; saved = source.read_bytes()
            source.write_bytes(saved + b'changed')
            with self.assertRaises(ValueError): evidence.validate_evidence(root)
            source.write_bytes(saved)
            report = root / audit['reports'][0]['path']; value = json.loads(report.read_text())
            value['raw_audio'] = 'unexpected payload'; report.write_text(json.dumps(value))
            audit['reports'][0]['sha256'] = hashlib.sha256(report.read_bytes()).hexdigest()
            (root / audit_path).write_text(json.dumps(audit))
            with self.assertRaises(ValueError): evidence.validate_evidence(root)


if __name__ == '__main__':
    unittest.main()
