#!/usr/bin/env python3
"""Explicit generic persona candidates through the signed native CPU worker.
Existing local pinned assets only; no downloads, microphone, app readiness or
semantic safety/quality pass. Outputs require Gemju Sherpa's rubric review.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'llm-runtime'))
import check_ios as runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--udid', required=True)
    args = parser.parse_args()
    devices = json.loads(subprocess.run(['xcrun', 'simctl', 'list', 'devices', '--json'], check=True, capture_output=True, text=True).stdout)
    selected = [d for group in devices['devices'].values() for d in group if d['udid'] == args.udid and d['state'] == 'Booted' and d.get('isAvailable')]
    if len(selected) != 1:
        raise ValueError('existing booted simulator required')
    runtime.verify_source()
    _, record = runtime.build('iphonesimulator')
    sdk = subprocess.run(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path'], check=True, capture_output=True, text=True).stdout.strip()
    directory = runtime.CACHE / 'build-ios-iphonesimulator'
    executable = directory / 'persona-evaluation'
    sources = sorted((HERE.parent / 'native-test-seam/Sources/NativeTestSeam').glob('*.swift'))
    libraries = [runtime.CACHE / item['file'] for item in record['libraries']]
    runtime.run(['xcrun', '--sdk', 'iphonesimulator', 'swiftc', '-swift-version', '5', '-warnings-as-errors',
                 '-target', 'arm64-apple-ios18.0-simulator', '-sdk', sdk, '-parse-as-library', '-D', 'DEBUG',
                 '-D', 'EILO_LLM_EVALUATION', '-I', runtime.HERE / 'include', *sources,
                 HERE / 'tests/ios_persona.swift', directory / 'eilo_llm.o', *libraries,
                 '-framework', 'Accelerate', '-framework', 'Foundation', '-framework', 'CryptoKit',
                 '-lc++', '-o', executable], 'persona-compile.log')
    model = runtime.PROVENANCE['model']
    model_path = runtime.HERE.parents[1] / '.local/model-build' / model['file']
    fixtures_path = HERE / 'tests/persona-fixtures.json'
    runtime.run(['xcrun', 'simctl', 'spawn', args.udid, executable, model_path,
                 model['sha256'], model['bytes'], fixtures_path], 'persona-evaluation.log', timeout=780)
    cases = [json.loads(line) for line in (runtime.CACHE / 'persona-evaluation.log').read_text().splitlines()]
    fixture = json.loads(fixtures_path.read_text())
    if [case['id'] for case in cases] != [case['id'] for case in fixture['cases']]:
        raise ValueError('candidate set mismatch')
    for case in cases:
        if not 1 <= case['generated_tokens'] <= 96 or not case['output'] or case['review_status'] != 'pending_review':
            raise ValueError('invalid bounded candidate')
        case['may_be_truncated'] = case['generated_tokens'] == 96
        case['ratings'] = None
    report = {'task': 'VC-BEHAV-01', 'policy_version': fixture['policy_version'],
              'fixture_sha256': hashlib.sha256(fixtures_path.read_bytes()).hexdigest(),
              'fixed_system_rules_sha256': hashlib.sha256((fixture['privileged_rules']+json.loads((HERE/'tests/capability-fixtures.json').read_text())['rules']+json.loads((HERE/'tests/danger-fixtures.json').read_text())['rules']).encode()).hexdigest(),
              'purpose': 'S07 final combined-policy regression; semantic acceptance remains pending',
              'platform': 'iOS ARM64 simulator, actual signed-pack/controller CPU worker',
              'model': model, 'runtime': runtime.PROVENANCE['runtime'], 'native_link': record,
              'cases': cases, 'reviewer': 'Gemju Sherpa', 'review_status': 'pending_review',
              'synthetic_pack_trust': True, 'temporary_pack_removed': True,
              'microphone': 'NOT USED', 'speech': 'NOT RELEASED', 'physical': 'NOT RUN',
              'ordinary_app_attachment': 'NOT ENABLED',
              'limits': 'Execution/template checks pass; semantic persona acceptance requires review. Simulator OS-wide network isolation is unverified.'}
    (HERE / 'tests/ios-persona-candidates.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Nine bounded native CPU persona candidates generated; semantic review pending, no speech released.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Persona evaluation unavailable ({type(error).__name__}); see ignored logs.') from None
