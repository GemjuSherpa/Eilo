"""Audit the joined, relocated framework simulator execution without native caches."""
import argparse
import html
import json
from pathlib import Path
from check_framework_capture import HERE, source_pins, validate as native_validate, sha256, require, framework_module

NATIVE = set('scope physical production microphone confidence voice_evidence cases temporary_pack_removed'.split())
EXTRA = set('schema_version fixture_sha256 vad_model_sha256 llm_model_sha256 binary_sha256 source_sha256 source_pins framework client_rpaths sdk_speech_gain relocation llm_libraries'.split())
FLAGS = dict(physical='NOT_RUN', ordinary_app='NOT_ENABLED', release='HOLD', persistent_memory='DISABLED',
             calibration='NOT_ESTABLISHED', threshold='NOT_GRANTED', pack_trust='SYNTHETIC_EVALUATOR_ONLY', signing='NOT_REVIEWED', distribution='NOT_APPROVED')


def digest(value):
    require(type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value), 'invalid digest')


def validate(r):
    require(type(r) is dict and set(r)==NATIVE|EXTRA, 'unexpected report fields')
    native_validate({k:r[k] for k in NATIVE})
    require(type(r['schema_version']) is int and r['schema_version']==1 and r['source_pins']==source_pins(), 'source inventory changed')
    require(type(r['sdk_speech_gain']) is int and r['sdk_speech_gain']==0, 'speech must be muted')
    require(r['relocation']=='EXECUTED_WITH_ORIGINAL_CLIENT_DIRECTORY_ABSENT', 'relocation missing')
    require(type(r['client_rpaths']) is list and len(r['client_rpaths'])==2 and set(r['client_rpaths'])=={'/usr/lib/swift','@executable_path/Frameworks'}, 'unsafe loader paths')
    f=framework_module(); expected=f.read(HERE.parent/'asr-runtime/framework-results.json')
    require(expected['source_pins']==f.pins() and r['framework']==expected['frameworks']['iphonesimulator'], 'framework provenance changed')
    fixture=next(v for v in f.read(HERE.parent/'asr-runtime/tests/fixtures.json')['cases'] if v['id']=='question')
    require(r['fixture_sha256']==fixture['sha256'], 'fixture changed')
    require(r['vad_model_sha256']==f.read(HERE.parent/'vad-runtime/provenance.json')['model_sha256'], 'VAD model changed')
    require(r['llm_model_sha256']==f.read(HERE.parent/'llm-runtime/provenance.json')['model']['sha256'], 'LLM model changed')
    require(r['source_sha256']==sha256(HERE/'tests/ios_framework_capture.swift'), 'probe changed')
    digest(r['binary_sha256'])
    libraries=r['llm_libraries']; names=['llm-build/src/libllama.a', *['llm-build/ggml/src/lib'+n+'.a' for n in ('ggml','ggml-cpu','ggml-base')]]
    require(type(libraries) is list and len(libraries)==4 and [v['file'] for v in libraries]==names, 'library inventory changed')
    for v in libraries:
        require(type(v) is dict and set(v)=={'file','sha256'}, 'unexpected library fields');digest(v['sha256'])
    return dict(scope=r['scope'],cases=r['cases'],sdk_speech_gain=0,relocation=r['relocation'],
                confidence=r['confidence'],voice_evidence=r['voice_evidence'],microphone=r['microphone'],**FLAGS)


def export(r,out):
    summary=validate(r);require(not out.exists(), 'output already exists');out.mkdir(parents=True)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'summary.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Joined framework simulator evaluation</title><h1>Joined framework simulator evaluation</h1><p>File-fed VAD and framework ASR, signed evaluator packs, loaded CPU replies and real muted SDK speech. Synthetic confidence and voice evidence; no physical, production, signing or release acceptance.</p><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre></html>\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,default=HERE/'tests/ios-framework-capture-results.json');p.add_argument('--output',type=Path)
    a=p.parse_args();f=framework_module();r=f.read(a.report)
    print(json.dumps(export(r,a.output) if a.output else validate(r),indent=2))
