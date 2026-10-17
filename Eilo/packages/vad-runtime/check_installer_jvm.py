"""Offline macOS JVM/JNI signed speech evaluation; no Android device, capture or download."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from check_installer import ASR, HERE, NAMES, run, verify, verified_asr, verify_fixture, validate_result, sha256, require


def compile_host(output, cache, java):
    moon = cache / 'moonshine-voice-macos-arm64'
    exports = output / 'asr.exports'
    names = {'_eilo_asr_' + name for name in ('create', 'accept', 'text', 'destroy')}
    exports.write_text('\n'.join(sorted(names)) + '\n')
    core = output / 'libeilo_installer_asr_host.dylib'
    run(['clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-dynamiclib',
         '-I', ASR / 'include', '-I', moon / 'include', ASR / 'eilo_asr.cc', moon / 'lib/libmoonshine.a',
         '-framework', 'Accelerate', '-framework', 'Foundation', '-Wl,-twolevel_namespace',
         '-Wl,-exported_symbols_list,' + str(exports), '-Wl,-install_name,@rpath/' + core.name, '-o', core])
    require(set(run(['nm', '-gUj', core]).splitlines()) == names and 'TWOLEVEL' in run(['otool', '-hv', core]),
            'host ASR isolation failed')
    jni = output / 'libeilo_installer_asr_jni.dylib'
    run(['clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-dynamiclib',
         '-I', ASR / 'include', '-I', java / 'include', '-I', java / 'include/darwin',
         ASR / 'eilo_asr_jni.cc', core, '-Wl,-rpath,@loader_path', '-o', jni])
    return core, jni


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('asr-cache', 'vad-cache', 'vad-model', 'jni-build', 'java-home', 'android-sdk', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    cache, vad, model, jni, java, sdk, output = [p.resolve() for p in
        (args.asr_cache, args.vad_cache, args.vad_model, args.jni_build, args.java_home, args.android_sdk, args.output)]
    verify(vad, model)
    asr_model, record = verified_asr(cache)
    raw, fixture = verify_fixture(cache)
    jni_record = json.loads((jni / 'results.json').read_text())
    wrapper = jni / 'libeilo_vad_jni.dylib'
    require(sha256(wrapper) == jni_record['host_jni_sha256'], 'VAD JNI binary changed')
    for name, digest in jni_record['source_sha256'].items():
        require(sha256(HERE / name) == digest, 'VAD JNI source changed')
    require(not output.exists(), 'refusing to overwrite evidence')
    output.mkdir(parents=True)
    core, asr_jni = compile_host(output, cache, java)
    runtime = vad / 'sherpa-onnx-v1.13.8-osx-arm64-shared-no-tts/lib/libonnxruntime.dylib'
    with tempfile.TemporaryDirectory(prefix='eilo-speech-jni-') as folder:
        stage = Path(folder)
        staged = {}
        for source in (core, asr_jni, runtime, wrapper):
            target = stage / source.name
            shutil.copy2(source, target)
            require(sha256(source) == sha256(target), 'staged runtime changed')
            staged[source] = target
        pins = [dict(id='asr-' + str(i), filename=r['file'], source=str(asr_model / r['file']),
                     sha256=r['local_sha256'], bytes=r['bytes']) for i, r in enumerate(record['model']['files'])]
        pins.append(dict(id='vad', filename='silero.onnx', source=str(model), sha256=sha256(model), bytes=model.stat().st_size))
        manifest = stage / 'pins.json'; manifest.write_text(json.dumps(pins))
        audio = stage / 'synthetic.f32'; audio.write_bytes(raw)
        properties = {'manifest': str(manifest), 'audio': str(audio), 'result': str(output / 'native-results.json')}
        for name, source in [('runtime', runtime), ('vadJni', wrapper), ('asrCore', core), ('asrJni', asr_jni)]:
            properties[name] = str(staged[source]); properties[name + 'Sha'] = sha256(source)
        init = output / 'installer.init.gradle'
        text = 'gradle.afterProject { p ->\n if (p.path == ":app") {\n'
        text += ' p.android.sourceSets.test.java.srcDir(' + json.dumps(str(HERE / 'tests/jvm')) + ')\n'
        text += ' p.tasks.withType(org.gradle.api.tasks.testing.Test).configureEach {\n'
        for key, value in properties.items():
            text += ' systemProperty ' + json.dumps('eilo.installer.' + key) + ', ' + json.dumps(value) + '\n'
        init.write_text(text + ' }\n }\n}\n')
        project = HERE.parents[1] / 'apps/mobile/android'
        completed = subprocess.run([str(project / 'gradlew'), '-p', str(project), '-I', str(init),
            ':app:testDebugUnitTest', '--tests', 'com.eilo.foundation.NativeSpeechInstallerRuntimeTest',
            '--offline', '--max-workers=2'], env=dict(os.environ, JAVA_HOME=str(java), ANDROID_HOME=str(sdk)),
            capture_output=True, text=True, timeout=300)
        (output / 'jvm-build.log').write_text(completed.stdout + completed.stderr)
        require(completed.returncode == 0, 'host JNI evaluation failed; inspect local build log')
        result = json.loads((output / 'native-results.json').read_text())
    validate_result(result, 'MACOS_JVM_JNI_SIGNED_SPEECH_INSTALLER')
    result.update(schema_version=1, fixture_sha256=fixture['sha256'], vad_model_sha256=sha256(model),
        asr_model_files=[dict(file=r['file'], sha256=r['local_sha256']) for r in record['model']['files']],
        runtime_sha256=sha256(runtime), vad_jni_sha256=sha256(wrapper), asr_core_sha256=sha256(core),
        asr_jni_sha256=sha256(asr_jni), android_execution='NOT_RUN', physical_gates='NOT_RUN')
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Real signed VAD/ASR installer: macOS JVM/JNI eight-case PASS; Android device/physical NOT_RUN.')


if __name__ == '__main__':
    main()
