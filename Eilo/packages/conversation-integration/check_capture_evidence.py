"""Offline source/report audit for the file-fed capture-to-reply evaluation; no native SDK needed."""
import json
from check_capture_ios import ROOT, HERE, validate, sha256, require

NATIVE_KEYS = {'scope', 'physical', 'production', 'microphone', 'confidence', 'voice_evidence', 'cases', 'temporary_pack_removed'}
EXTRA_KEYS = {'schema_version', 'fixture_sha256', 'vad_model_sha256', 'llm_model_sha256', 'binary_sha256', 'source_sha256', 'llm_libraries'}


def source_paths(root):
    patterns = ('packages/native-test-seam/Sources/NativeTestSeam/*.swift',
        'packages/vad-runtime/eilo_vad.cc', 'packages/vad-runtime/eilo_vad_onnx.cc', 'packages/vad-runtime/include/*',
        'packages/asr-runtime/eilo_asr.cc', 'packages/asr-runtime/include/*',
        'packages/llm-runtime/eilo_llm.cc', 'packages/llm-runtime/include/*')
    paths = {str(p.relative_to(root)) for pattern in patterns for p in root.glob(pattern)
             if p.is_file()}
    paths.update('packages/' + name for name in ('conversation-integration/check_capture_ios.py',
        'conversation-integration/tests/ios_capture.swift', 'vad-runtime/check_installer.py',
        'vad-runtime/check_native.py', 'asr-runtime/provenance.json', 'asr-runtime/tests/fixtures.json',
        'vad-runtime/provenance.json', 'llm-runtime/provenance.json', 'llm-runtime/tests/ios-results.json'))
    return paths


def check_evidence(root=ROOT):
    report_path = root / 'packages/conversation-integration/tests/ios-capture-results.json'
    audit = json.loads((root / 'packages/conversation-integration/tests/capture-evidence.json').read_text())
    require(set(audit) == {'schema_version', 'report_sha256', 'inputs'} and audit['schema_version'] == 1, 'audit schema changed')
    require(sha256(report_path) == audit['report_sha256'], 'joined report changed')
    require(isinstance(audit['inputs'], list) and {r['path'] for r in audit['inputs']} == source_paths(root)
            and len(audit['inputs']) == len(source_paths(root)), 'evaluated source inventory changed')
    for item in audit['inputs']:
        require(set(item) == {'path', 'sha256'}, 'unexpected source fields')
        path = (root / item['path']).resolve()
        require(path.is_relative_to(root.resolve()) and sha256(path) == item['sha256'], 'evaluated source changed')
    result = json.loads(report_path.read_text())
    require(set(result) == NATIVE_KEYS | EXTRA_KEYS and result['schema_version'] == 1, 'unexpected committed fields')
    validate({k: result[k] for k in NATIVE_KEYS})
    fixtures = json.loads((root / 'packages/asr-runtime/tests/fixtures.json').read_text())['cases']
    require(result['fixture_sha256'] == next(r['sha256'] for r in fixtures if r['id'] == 'question'), 'fixture pin changed')
    for package, key, field in [('vad-runtime', 'vad_model_sha256', 'model_sha256'), ('llm-runtime', 'llm_model_sha256', 'model')]:
        value = json.loads((root / ('packages/' + package + '/provenance.json')).read_text())[field]
        require(result[key] == (value['sha256'] if isinstance(value, dict) else value), 'model pin changed')
    require(result['source_sha256'] == sha256(root / 'packages/conversation-integration/tests/ios_capture.swift'), 'probe hash changed')
    libraries = result['llm_libraries']
    names = {'llm-build/src/libllama.a'} | {'llm-build/ggml/src/lib' + n + '.a' for n in ('ggml', 'ggml-cpu', 'ggml-base')}
    require(len(libraries) == 4 and {r['file'] for r in libraries} == names, 'LLM library inventory changed')
    for value in [result['binary_sha256'], *[r['sha256'] for r in libraries]]:
        require(isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value), 'binary digest missing')
    require(all(set(r) == {'file', 'sha256'} for r in libraries), 'unexpected library fields')
    print('Joined capture evidence/source pins PASS; physical NOT_RUN, confidence/voice evidence synthetic.')


if __name__ == '__main__':
    check_evidence()
