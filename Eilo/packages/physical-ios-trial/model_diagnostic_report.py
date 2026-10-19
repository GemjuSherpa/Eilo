"""Closed aggregate-only CPU diagnostic schema; never promotes full comparison acceptance."""
import argparse
import json
import math
from pathlib import Path
import re
from datetime import datetime

FIXED = {
    'schema_version': 1, 'scope': 'IOS_CPU_MODEL_DIAGNOSTIC',
    'fixture_manifest_sha256': '0e6bfb28b2bb8f93dfd6a06838fddc0f43a15c8bb1d824ee0988bb3f70ef5746',
    'runtime_revision': '8345f333951c661d166b00e6f9362e553768f292',
    'context_tokens': 4096, 'output_token_limit': 256, 'threads': 2,
    'sampler': 'greedy', 'enable_thinking': False, 'backend': 'CPU',
    'model_open': 'FRESH_HANDLE_PER_PROMPT_OS_CACHES_UNCONTROLLED',
    'memory_scope': 'PROCESS_LIFETIME_INCLUDING_PREPARATION',
    'timing_scope': 'BEGIN_INCLUDES_TOKENIZATION_CONTEXT_AND_PREFILL_FIRST_PIECE_INCLUDES_NATIVE_NEXT_DECODE',
    'microphone': 'NOT_OPENED', 'speaker': 'NOT_OPENED', 'raw_text_exported': False,
    'network_observation': 'NOT_RUN', 'quality': 'NOT_RUN', 'physical_gate_acceptance': 'NOT_RUN',
}
VARIABLE = {'phase', 'process_id', 'model_sha256', 'model_bytes', 'os_build', 'physical_memory_bytes', 'updated_utc', 'cases'}
ROW = {'fixture_id', 'prompt_tokens', 'native_piece_count', 'output_bytes', 'verified_open_and_load_ms', 'begin_wall_ms', 'first_native_piece_from_begin_ms', 'generation_wall_ms', 'memory'}


def require(value, message):
    if not value:
        raise ValueError(message)


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def validate(report):
    require(type(report) is dict and set(report) == set(FIXED) | VARIABLE, 'report fields')
    for key, value in FIXED.items():
        require(type(report[key]) is type(value) and report[key] == value, 'fixed field: ' + key)
    pins = json.loads(Path(__file__).with_name('tests').joinpath('model-comparison-pins.json').read_text())
    require(any(report['model_sha256'] == p['sha256'] and type(report['model_bytes']) is int and report['model_bytes'] == p['bytes'] for p in pins), 'unknown model')
    require(type(report['process_id']) is str and re.fullmatch(r'[0-9A-F]{8}(-[0-9A-F]{4}){3}-[0-9A-F]{12}', report['process_id']), 'process UUID')
    require(type(report['os_build']) is str and re.fullmatch(r'Version [0-9.]+ \(Build [A-Za-z0-9]+\)', report['os_build']), 'OS build')
    require(integer(report['physical_memory_bytes'], 1, 128 * 1024**3), 'physical memory')
    require(type(report['updated_utc']) is str and report['updated_utc'].endswith('Z'), 'UTC timestamp')
    datetime.fromisoformat(report['updated_utc'].replace('Z', '+00:00'))
    require(report['phase'] in ('RUNNING', 'COMPLETED', 'CANCELLED', 'INFERENCE_FAILED'), 'phase')
    rows = report['cases']
    require(type(rows) is list, 'cases')
    require([r.get('fixture_id') for r in rows if type(r) is dict] == ([f'compare-{i:02d}' for i in range(1, 7)] if report['phase'] == 'COMPLETED' else []), 'case order/count')
    require(report['phase'] == 'COMPLETED' or not rows, 'partial rows denied')
    peak = 0
    for row in rows:
        require(type(row) is dict and set(row) == ROW, 'row fields')
        require(integer(row['prompt_tokens'], 1, 3840) and integer(row['native_piece_count'], 1, 256), 'token counts')
        require(integer(row['output_bytes'], row['native_piece_count'], row['native_piece_count'] * 1024), 'piece bytes')
        for key in ('verified_open_and_load_ms', 'begin_wall_ms', 'first_native_piece_from_begin_ms', 'generation_wall_ms'):
            n = row[key]
            require(type(n) in (int, float) and math.isfinite(n) and 0 < n <= 600000, 'timing')
        require(row['begin_wall_ms'] <= row['first_native_piece_from_begin_ms'] <= row['generation_wall_ms'], 'timing order')
        memory = row['memory']
        require(type(memory) is dict and set(memory) == {'current_phys_footprint_bytes', 'process_lifetime_peak_bytes'}, 'memory fields')
        current, high = memory['current_phys_footprint_bytes'], memory['process_lifetime_peak_bytes']
        require(integer(current, 1, report['physical_memory_bytes']) and integer(high, current, report['physical_memory_bytes']) and high >= peak, 'OS memory peak')
        peak = high
    return report


def validate_pair(reports):
    require(type(reports) is list and len(reports) == 2, 'two candidate reports required')
    for report in reports:
        validate(report)
        require(report['phase'] == 'COMPLETED', 'both candidates must complete')
    pins = json.loads(Path(__file__).with_name('tests').joinpath('model-comparison-pins.json').read_text())
    require({r['model_sha256'] for r in reports} == {p['sha256'] for p in pins}, 'distinct pinned candidates required')
    require(reports[0]['process_id'] != reports[1]['process_id'], 'fresh process required per candidate')
    require(reports[0]['os_build'] == reports[1]['os_build'] and reports[0]['physical_memory_bytes'] == reports[1]['physical_memory_bytes'], 'device metadata differs')
    return reports


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--pair', action='store_true')
    args = parser.parse_args()
    (validate_pair if args.pair else validate)(json.loads(args.report.read_text()))
    print('CPU diagnostic aggregate valid; full physical acceptance remains NOT_RUN')
