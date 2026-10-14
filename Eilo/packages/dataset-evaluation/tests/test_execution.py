import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from audio import write_wav
from benchmark import run_adapter
from extract_subset import member_path
from manifests import sha256


class ExecutionTests(unittest.TestCase):
    def test_archive_traversal_symlink_and_size(self):
        for name, kind, size in [('../escape', tarfile.REGTYPE, 1), ('/absolute', tarfile.REGTYPE, 1),
                                 ('link', tarfile.SYMTYPE, 1), ('large', tarfile.REGTYPE, 100000000)]:
            member = tarfile.TarInfo(name)
            member.type, member.size = kind, size
            with self.assertRaises(ValueError): member_path(member)

    def test_adapter_protocol_has_no_truth_and_binary_is_pinned(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / 'tone.wav'
            write_wav(audio, [1] * 160)
            script = root / 'adapter'
            script.write_text('#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\n'
                              'r=json.loads(Path(sys.argv[1]).read_text())\n'
                              'assert set(r)=={"schema_version","id","task","audio","rate"}\n'
                              'Path(sys.argv[2]).write_text(json.dumps({"id":r["id"],"transcript":"yes"}))\n')
            script.chmod(0o755)
            manifest = {'schema_version': 1, 'rate': 16000, 'kind': 'synthetic', 'dataset': 'synthetic',
                        'release': '1', 'cases': [{'id': 'a' * 24, 'path': audio.name,
                        'sha256': sha256(audio), 'samples': 160, 'reference': 'yes', 'slice': 'test',
                        'split': 'test', 'task': 'asr'}]}
            metadata = {'kind': 'synthetic', 'name': 'protocol fixture', 'binary_sha256': sha256(script),
                        'model_sha256': '0' * 64, 'config_sha256': '1' * 64}
            value = run_adapter(manifest, root, script, metadata)
            self.assertEqual(value['cases'][0]['transcript'], 'yes')
            script.write_text('changed')
            with self.assertRaises(ValueError): run_adapter(manifest, root, script, metadata)
            audio.write_bytes(b'changed')
            with self.assertRaises(ValueError): run_adapter(manifest, root, script, metadata)

    def test_archive_safe_subset_and_checksum_failure(self):
        from extract_subset import extract
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive_path = root / 'corpus.tar.gz'
            with tarfile.open(archive_path, 'w:gz') as archive:
                for name, data in [('LICENSE', b'Attribution 4.0 International'),
                                   ('testing_list.txt', b'yes/test.wav\n'),
                                   ('yes/test.wav', b'fixture'), ('no/train.wav', b'train')]:
                    member = tarfile.TarInfo(name)
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
            receipt = {'schema_version': 1, 'dataset': 'speech_commands', 'version': '0.02',
                       'license': 'CC-BY-4.0', 'permission': 'APPROVED_BY_USER_TEST',
                       'checksum_status': 'LOCAL_OBSERVED', 'sha256': sha256(archive_path),
                       'bytes': archive_path.stat().st_size, 'license_evidence_sha256': '1' * 64}
            output = extract(archive_path, receipt, root / 'out', limit=1)
            self.assertTrue((output / 'yes/test.wav').exists())
            self.assertFalse((output / 'no/train.wav').exists())
            archive_path.write_bytes(b'corrupted')
            with self.assertRaises(ValueError): extract(archive_path, receipt, root / 'bad')

    def test_native_adapter_config_pin_rejected_before_execution(self):
        import os
        from unittest.mock import patch
        from native_asr_adapter import verified_config
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'config.json'
            path.write_text('{}')
            with patch.dict(os.environ, {'EILO_DATA_ADAPTER_CONFIG_SHA256': '0' * 64}):
                with self.assertRaises(ValueError): verified_config(path)

    def test_common_voice_subset_checks_disjoint_speakers(self):
        from extract_subset import extract
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive_path = root / 'cv.tar'
            def archive(train_speaker):
                with tarfile.open(archive_path, 'w') as output:
                    records = {'test.tsv': b'client_id\tpath\tsentence\na\tcase.mp3\thello\n',
                               'train.tsv': ('client_id\tpath\tsentence\n' + train_speaker + '\ttrain.mp3\thi\n').encode(),
                               'dev.tsv': b'client_id\tpath\tsentence\nc\tdev.mp3\thi\n',
                               'clips/case.mp3': b'encoded fixture'}
                    for name, data in records.items():
                        item = tarfile.TarInfo(name)
                        item.size = len(data)
                        output.addfile(item, io.BytesIO(data))
            archive('b')
            receipt = {'schema_version': 1, 'dataset': 'common_voice', 'version': 'test-only',
                       'license': 'CC0-1.0', 'permission': 'APPROVED_BY_USER_TEST',
                       'checksum_status': 'LOCAL_OBSERVED', 'sha256': sha256(archive_path),
                       'bytes': archive_path.stat().st_size, 'license_evidence_sha256': '1' * 64}
            output = extract(archive_path, receipt, root / 'good', 1)
            self.assertTrue((output / 'clips/case.mp3').exists())
            archive('a')
            receipt.update({'sha256': sha256(archive_path), 'bytes': archive_path.stat().st_size})
            with self.assertRaises(ValueError): extract(archive_path, receipt, root / 'bad', 1)
