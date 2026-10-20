"""Validate aggregate-only human rubric ratings; never infer full physical acceptance."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re

FIXED = dict(schema_version=1, scope='IOS_MODEL_QUALITY_COLLECTION',
             fixture_manifest_sha256='0e6bfb28b2bb8f93dfd6a06838fddc0f43a15c8bb1d824ee0988bb3f70ef5746',
             runtime_revision='8345f333951c661d166b00e6f9362e553768f292',
             rating_source='HUMAN_OPERATOR_UI', quality_scale='FROZEN_RUBRIC_1_TO_5',
             raw_text_exported=False, raw_audio_saved=False, audio_devices='NOT_OPENED',
             physical_gate_acceptance='NOT_RUN', network_observation='NOT_RUN',
             context_tokens=4096, output_token_limit=256, threads=2, sampler='greedy', enable_thinking=False)
VARIABLE = {'model_sha256', 'model_bytes', 'session_id', 'os_build', 'updated_utc', 'attempts'}


def require(value, message):
    if not value:raise ValueError(message)


def validate(report):
    require(type(report) is dict and set(report) == set(FIXED) | VARIABLE, 'report fields')
    for key, value in FIXED.items():
        require(type(report[key]) is type(value) and report[key] == value, 'fixed field: '+key)
    pins = json.loads(Path(__file__).with_name('tests').joinpath('model-comparison-pins.json').read_text())
    require(any(report['model_sha256'] == p['sha256'] and type(report['model_bytes']) is int and report['model_bytes'] == p['bytes'] for p in pins), 'unknown model')
    require(type(report['session_id']) is str and re.fullmatch(r'[0-9A-F]{8}(-[0-9A-F]{4}){3}-[0-9A-F]{12}', report['session_id']), 'session UUID')
    require(type(report['os_build']) is str and re.fullmatch(r'Version [0-9.]+ \(Build [A-Za-z0-9]+\)', report['os_build']), 'OS build')
    require(type(report['updated_utc']) is str and report['updated_utc'].endswith('Z'), 'UTC timestamp')
    datetime.fromisoformat(report['updated_utc'].replace('Z', '+00:00'))
    rows = report['attempts']
    require(type(rows) is list and len(rows) <= 18, 'attempt count')
    next_fixture, attempts = 1, 0
    for i, row in enumerate(rows):
        require(type(row) is dict and set(row) in ({'fixture_id', 'attempt', 'model_status'}, {'fixture_id', 'attempt', 'model_status', 'rubric_quality'}), 'attempt fields')
        require(next_fixture <= 6 and row['fixture_id'] == f'compare-{next_fixture:02d}', 'fixture order')
        attempts += 1
        require(attempts <= 3 and type(row['attempt']) is int and row['attempt'] == i+1, 'attempt sequence/limit')
        require(row['model_status'] in ('GENERATING', 'GENERATED', 'FAILED', 'CANCELLED'), 'model status')
        if 'rubric_quality' in row:
            require(row['model_status'] == 'GENERATED' and type(row['rubric_quality']) is int and 1 <= row['rubric_quality'] <= 5, 'human score')
            next_fixture += 1;attempts = 0
        elif row['model_status'] in ('GENERATING', 'GENERATED'):
            require(i == len(rows)-1, 'unresolved attempt')
    return report


def validate_pair(reports):
    require(type(reports) is list and len(reports) == 2, 'two reports required')
    for report in reports:
        validate(report)
        require(sum('rubric_quality' in row for row in report['attempts']) == 6, 'six genuine ratings per candidate required')
    pins = json.loads(Path(__file__).with_name('tests').joinpath('model-comparison-pins.json').read_text())
    require({r['model_sha256'] for r in reports} == {p['sha256'] for p in pins}, 'distinct candidates')
    require(reports[0]['session_id'] != reports[1]['session_id'] and reports[0]['os_build'] == reports[1]['os_build'], 'distinct sessions and same OS required')
    return reports


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path);parser.add_argument('--pair', action='store_true');args = parser.parse_args()
    (validate_pair if args.pair else validate)(json.loads(args.report.read_text()))
    print('Human rubric aggregate valid; full comparison acceptance remains NOT_RUN')
