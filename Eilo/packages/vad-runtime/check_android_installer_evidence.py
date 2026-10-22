"""Validate Android ART aggregate evidence offline; never executes a device/model."""
import json
from pathlib import Path
from check_installer import HERE, validate_result, sha256, require
from check_installer_evidence import NATIVE_KEYS
from check_installer_android import LIBRARIES, SCOPE

ROOT = HERE.parents[1]
EXTRA = {'schema_version', 'runtime_profile', 'ort_header_commit', 'abi', 'android_api', 'library_sha256',
         'evaluation_apk_sha256', 'normal_apk_sha256', 'temporary_files_removed', 'normal_app_restored',
         'internet_permission', 'microphone_permission', 'fixture_sha256', 'vad_model_sha256',
         'vad_source_model_sha256', 'vad_conversion', 'asr_model_files',
         'controller_permission_and_readiness', 'network_acceptance'}


def digest(value):
    require(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value), 'invalid digest')


def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'duplicate JSON key')
        value[key] = item
    return value


def load(path):
    with path.open('rb') as stream:
        raw = stream.read(524289)
    require(len(raw) <= 524288, 'evidence too large')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique)


def source_paths(root):
    patterns = ('apps/mobile/android/app/src/main/java/com/eilo/*.kt',
                'apps/mobile/android/app/src/main/java/com/eilo/foundation/*.kt',
                'packages/vad-runtime/tests/android-device/*',
                'packages/vad-runtime/eilo_vad*.cc', 'packages/vad-runtime/include/*',
                'packages/asr-runtime/eilo_asr*.cc', 'packages/asr-runtime/include/*')
    paths = {str(p.relative_to(root)) for pattern in patterns for p in root.glob(pattern) if p.is_file()}
    paths.update('packages/' + p for p in ('vad-runtime/check_installer_android.py',
        'vad-runtime/vad_backend.h', 'vad-runtime/provenance.json', 'vad-runtime/android-ort-header-provenance.json',
        'asr-runtime/provenance.json', 'asr-runtime/tests/fixtures.json'))
    return paths


def validate_report(report, root=ROOT):
    require(type(report) is dict and set(report) == NATIVE_KEYS | EXTRA, 'closed ART report required')
    validate_result({k: report[k] for k in NATIVE_KEYS}, SCOPE)
    require(type(report['schema_version']) is int and report['schema_version'] == 1
            and type(report['android_api']) is int and report['android_api'] == 35 and report['abi'] == 'arm64-v8a', 'wrong emulator configuration')
    require(report['runtime_profile'] == 'SINGLE_PINNED_MOONSHINE_ORT_1_23_2'
            and report['controller_permission_and_readiness'] == 'SYNTHETIC'
            and report['network_acceptance'] == 'NOT_RUN', 'scope promotion forbidden')
    require(report['temporary_files_removed'] is True and report['normal_app_restored'] is True
            and report['internet_permission'] == 'ABSENT' and report['microphone_permission'] == 'ABSENT', 'cleanup/permission boundary missing')
    headers = load(root / 'packages/vad-runtime/android-ort-header-provenance.json')
    require(report['ort_header_commit'] == headers['commit'] and headers['version'] == 'v1.23.2'
            and headers['source'] == 'microsoft/onnxruntime' and headers['license'] == 'MIT', 'header source mismatch')
    model = load(root / 'packages/asr-runtime/provenance.json')
    fixture = next(row['sha256'] for row in load(root / 'packages/asr-runtime/tests/fixtures.json')['cases'] if row['id'] == 'question')
    require(report['fixture_sha256'] == fixture, 'wrong fixture')
    require(report['vad_source_model_sha256'] == load(root / 'packages/vad-runtime/provenance.json')['model_sha256'], 'wrong source model')
    digest(report['vad_model_sha256'])
    conversion = report['vad_conversion']
    require(type(conversion) is dict and set(conversion) == {'runtime', 'format', 'optimization', 'converter_sha256', 'bytes'}, 'conversion record required')
    require(conversion['runtime'] == '1.23.0' and conversion['format'] == 'ORT' and conversion['optimization'] == 'DISABLED'
            and type(conversion['bytes']) is int and 0 < conversion['bytes'] < 8000000
            and conversion['converter_sha256'] == sha256(root / 'packages/vad-runtime/tests/android-device/convert_vad_model.cc'), 'conversion source/options changed')
    require(report['asr_model_files'] == [{'file': row['file'], 'sha256': row['local_sha256']} for row in model['model']['files']], 'ASR inventory changed')
    libraries = report['library_sha256']
    require(type(libraries) is dict and set(libraries) == set(LIBRARIES), 'native library inventory required')
    for value in [*libraries.values(), report['evaluation_apk_sha256'], report['normal_apk_sha256']]:
        digest(value)
    for name in ('libmoonshine.so', 'libonnxruntime.so'):
        expected = next(row['sha256'] for row in model['android']['files'] if row['path'] == 'android-0.1.5/jni/arm64-v8a/' + name)
        require(libraries[name] == expected, 'vendor binary modified')
    require(report['evaluation_apk_sha256'] != report['normal_apk_sha256'], 'normal/evaluation APK distinction missing')
    require(report['cases'] == load(root / 'packages/vad-runtime/tests/signed-installer-jvm-results.json')['cases'], 'frozen native case parity changed')
    return {'scope': SCOPE, 'cases': 8, 'evidence_structure': 'PASS', 'physical': 'NOT_RUN',
            'network_acceptance': 'NOT_RUN', 'production': 'NOT_ENABLED'}


def check_evidence(root=ROOT):
    report_path = root / 'packages/vad-runtime/tests/signed-installer-android-results.json'
    audit = load(root / 'packages/vad-runtime/tests/signed-installer-android-evidence.json')
    require(type(audit) is dict and set(audit) == {'schema_version', 'report_sha256', 'sources'}
            and type(audit['schema_version']) is int and audit['schema_version'] == 1, 'wrong audit schema')
    require(audit['report_sha256'] == sha256(report_path), 'ART report changed')
    require(type(audit['sources']) is list and len(audit['sources']) == len(source_paths(root))
            and {row['path'] for row in audit['sources']} == source_paths(root), 'source coverage changed')
    for row in audit['sources']:
        require(type(row) is dict and set(row) == {'path', 'sha256'}, 'wrong source fields')
        path = (root / row['path']).resolve()
        require(path.is_relative_to(root.resolve()) and sha256(path) == row['sha256'], 'evaluated source changed')
    return validate_report(load(report_path), root)


if __name__ == '__main__':
    try:
        print(json.dumps(check_evidence(), sort_keys=True))
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        raise SystemExit('Android ART evidence rejected; no acceptance inferred.') from None
