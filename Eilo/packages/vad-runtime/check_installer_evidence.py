"""Validate committed offline evidence without loading models, capture, downloads or native SDKs."""
import json
from check_installer import HERE, validate_result, require, sha256

ROOT = HERE.parents[1]
NATIVE_KEYS = {'scope', 'synthetic', 'worker_verified', 'physical', 'production', 'lab_signing', 'cases'}
COMMON = {'schema_version', 'fixture_sha256', 'vad_model_sha256', 'asr_model_files', 'android_execution',
          'physical_gates', 'source_sha256'}


def validate_evidence(root=ROOT):
    audit = json.loads((root / 'packages/vad-runtime/tests/signed-installer-evidence.json').read_text())
    require(set(audit) == {'schema_version', 'scope', 'sources', 'reports', 'physical_gates', 'production'}, 'audit fields changed')
    require(audit['schema_version'] == 1 and audit['scope'] == 'OFFLINE_SIGNED_SPEECH_INSTALLER'
            and audit['physical_gates'] == 'NOT_RUN' and audit['production'] == 'NOT_ENABLED', 'audit scope changed')
    patterns = ('packages/native-test-seam/Sources/NativeTestSeam/*.swift',
                'apps/mobile/android/app/src/main/java/com/eilo/foundation/*.kt',
                'packages/vad-runtime/eilo_vad*.cc', 'packages/vad-runtime/include/*',
                'packages/asr-runtime/eilo_asr*.cc', 'packages/asr-runtime/include/*')
    expected_sources = {str(p.relative_to(root)) for pattern in patterns for p in root.glob(pattern) if p.is_file()}
    expected_sources.update('packages/' + p for p in (
        'vad-runtime/check_installer.py', 'vad-runtime/check_installer_jvm.py',
        'vad-runtime/tests/swift_installer_probe.swift', 'vad-runtime/tests/jvm/NativeSpeechInstallerRuntimeTest.kt',
        'asr-runtime/provenance.json', 'asr-runtime/tests/fixtures.json', 'vad-runtime/provenance.json'))
    require({r['path'] for r in audit['sources']} == expected_sources
            and len(audit['sources']) == len(expected_sources), 'source coverage missing')
    for item in audit['sources'] + audit['reports']:
        require(set(item) == {'path', 'sha256'}, 'audit pin fields changed')
        path = (root / item['path']).resolve()
        require(path.is_relative_to(root.resolve()) and sha256(path) == item['sha256'], 'evaluated source/report changed')
    expected_reports = {'packages/vad-runtime/tests/signed-installer-' + p + '-results.json' for p in ('ios', 'jvm')}
    require({r['path'] for r in audit['reports']} == expected_reports and len(audit['reports']) == 2, 'report coverage missing')
    model = json.loads((root / 'packages/asr-runtime/provenance.json').read_text())['model']['files']
    vad = json.loads((root / 'packages/vad-runtime/provenance.json').read_text())['model_sha256']
    fixtures = json.loads((root / 'packages/asr-runtime/tests/fixtures.json').read_text())['cases']
    fixture = next(r['sha256'] for r in fixtures if r['id'] == 'question')
    cases = []
    for platform, scope, extra in [('ios', 'IOS_SIMULATOR_SIGNED_SPEECH_INSTALLER', {'probe_sha256', 'asr_wrapper_sha256'}),
                                  ('jvm', 'MACOS_JVM_JNI_SIGNED_SPEECH_INSTALLER', {'runtime_sha256', 'vad_jni_sha256', 'asr_core_sha256', 'asr_jni_sha256'})]:
        report = json.loads((root / ('packages/vad-runtime/tests/signed-installer-' + platform + '-results.json')).read_text())
        require(set(report) == NATIVE_KEYS | COMMON | extra, 'unexpected committed report fields')
        validate_result({k: report[k] for k in NATIVE_KEYS}, scope)
        require(report['schema_version'] == 1 and report['fixture_sha256'] == fixture
                and report['vad_model_sha256'] == vad and report['android_execution'] == 'NOT_RUN'
                and report['physical_gates'] == 'NOT_RUN', 'evidence input/scope changed')
        require(report['asr_model_files'] == [{'file': r['file'], 'sha256': r['local_sha256']} for r in model], 'model inventory changed')
        for path, digest in report['source_sha256'].items():
            require((root / path).resolve().is_relative_to(root.resolve()) and sha256(root / path) == digest, 'probe/runner changed')
        for key in extra:
            require(isinstance(report[key], str) and len(report[key]) == 64 and all(c in '0123456789abcdef' for c in report[key]), 'binary hash missing')
        cases.append(report['cases'])
    require(cases[0] == cases[1], 'platform case counters or transcript hashes diverged')
    print('Committed eight-case simulator/host-JNI evidence and source pins PASS; physical NOT_RUN.')


if __name__ == '__main__':
    validate_evidence()
