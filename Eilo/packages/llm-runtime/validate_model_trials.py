#!/usr/bin/env python3
"""Validate model-comparison evidence shape, never infer a device/performance pass."""
import argparse
import json
import math
import re
from pathlib import Path


def validate(report):
    if report.get('schema') != 1 or report.get('task') != 'VC-LLM-06' or report.get('status') not in ('NOT_RUN', 'MEASURED'):
        raise ValueError('wrong comparison schema/task/status')
    rows = report.get('platforms', [])
    if [r.get('platform') for r in rows] != ['iOS', 'Android']:
        raise ValueError('both platform records required')
    for row in rows:
        samples = row.get('samples', [])
        if report['status'] == 'NOT_RUN' or not samples:
            if samples or any(row.get(k) is not None for k in ('quality', 'prefill_ms', 'first_token_ms', 'peak_memory_bytes')):
                raise ValueError('unrun comparison cannot contain metrics')
            continue
        if row.get('hardware_kind') != 'physical' or not row.get('hardware_model') or not row.get('os_build'):
            raise ValueError('physical hardware/OS evidence required')
        models = row.get('models', [])
        if {m.get('id') for m in models} != {'qwen3-1.7b-q4-k-m', 'qwen3-0.6b-q4-k-m'} or len(models) != 2:
            raise ValueError('both exact candidates required')
        for model in models:
            if not re.fullmatch('[0-9a-f]{64}', model.get('sha256', '')) or type(model.get('bytes')) is not int or model['bytes'] <= 0 or not model.get('license_evidence') or not model.get('runtime_revision'):
                raise ValueError('verified model/runtime provenance required')
        if {s.get('model_id') for s in samples} != {m['id'] for m in models}:
            raise ValueError('samples for both candidates required')
        for sample in samples:
            if sample.get('fixture_id') not in {f'compare-{i:02d}' for i in range(1, 7)} or sample.get('backends') != 'CPU only' or sample.get('enable_thinking') is not False:
                raise ValueError('frozen CPU/non-thinking configuration required')
            if sample.get('context_tokens') != 4096 or not 1 <= sample.get('output_tokens', 0) <= 256:
                raise ValueError('bounded generation required')
            if sample.get('execution_mode') not in ('foreground', 'permitted_background') or (sample['execution_mode'] == 'permitted_background' and sample.get('OS_background_permission_evidence') is not True):
                raise ValueError('permitted execution mode required')
            if sample.get('memory_method') != 'native_OS_peak_footprint' or sample.get('network_observation') != 'NO_TRAFFIC_VERIFIED':
                raise ValueError('native memory and offline evidence required')
            for key in ('prefill_ms', 'first_token_ms', 'peak_memory_bytes'):
                value = sample.get(key)
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (key == 'peak_memory_bytes' and value == 0):
                    raise ValueError('invalid raw measurement')
            if sample.get('rated_by') != 'Gemju Sherpa' or type(sample.get('quality')) is not int or not 1 <= sample['quality'] <= 5:
                raise ValueError('review quality rating required')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', nargs='?', type=Path, default=Path(__file__).parent / 'tests/physical-model-comparison.json')
    args = parser.parse_args()
    validate(json.loads(args.report.read_text()))
    print('Comparison evidence structure PASS; phone performance/acceptance is not implied.')
