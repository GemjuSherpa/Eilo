#!/usr/bin/env python3
"""Validate evidence shape; success is not a physical trial/quality pass."""
import argparse
import json
import math
from pathlib import Path


def validate(report):
    if report.get('schema') != 1 or report.get('task') != 'VC-VOICE-06':
        raise ValueError('wrong trial schema/task')
    if report.get('status') not in ('NOT_RUN', 'MEASURED'):
        raise ValueError('unsupported evidence status')
    rows = report.get('platforms', [])
    if [r.get('platform') for r in rows] != ['iOS', 'Android']:
        raise ValueError('both platform records required')
    for row in rows:
        samples = row.get('samples', [])
        if report['status'] == 'NOT_RUN':
            if samples or row.get('first_audible_ms') is not None or row.get('intelligibility') is not None:
                raise ValueError('unrun trial cannot contain measurements')
            continue
        if not samples:  # A platform may remain explicitly unmeasured.
            if row.get('first_audible_ms') is not None or row.get('intelligibility') is not None:
                raise ValueError('metrics require raw samples')
            continue
        if row.get('hardware_kind') != 'physical' or not row.get('hardware_model') or not row.get('os_build'):
            raise ValueError('physical model/OS evidence required')
        voices = {v['id'] for v in row.get('installed_voices', []) if v.get('installed') is True}
        for sample in samples:
            if sample.get('voice_id') not in voices or sample.get('fixture_id') not in {f'voice-{i:02d}' for i in range(1, 13)}:
                raise ValueError('exact installed voice/frozen utterance required')
            if sample.get('airplane_mode') is not True or sample.get('wifi_enabled') is not False or sample.get('network_observation') != 'NO_TRAFFIC_VERIFIED':
                raise ValueError('offline/traffic evidence required')
            if sample.get('first_audible_method') != 'independent_local_audio_timestamp':
                raise ValueError('SDK start is not first audible audio')
            latency = sample.get('first_audible_ms')
            if type(latency) not in (int, float) or not math.isfinite(latency) or latency < 0:
                raise ValueError('invalid measured latency')
            if sample.get('rated_by') != 'Gemju Sherpa' or type(sample.get('intelligibility')) is not int or not 1 <= sample['intelligibility'] <= 5:
                raise ValueError('review rating required')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', nargs='?', type=Path, default=Path(__file__).parent / 'tests/physical-voice-trials.json')
    args = parser.parse_args()
    validate(json.loads(args.report.read_text()))
    print('Voice evidence structure PASS; physical acceptance is not implied.')
