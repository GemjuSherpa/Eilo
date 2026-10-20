"""Validate blocked RVI evidence and render a content-free review summary.

This is an offline report tool. It never starts an observer or grants acceptance.
"""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path


COMMON = dict(schema_version=1, packet_count=None, sent_bytes=None,
              received_bytes=None, target_attribution='NOT_ESTABLISHED',
              network_observation='NOT_RUN', physical_gate_acceptance='NOT_RUN')
PREFLIGHT = dict(
    scope='IOS_RVI_ATTRIBUTION_PREFLIGHT',
    permission='USER_APPROVED_MAX_180_SECONDS_METADATA_ONLY',
    status='PKTAP_AND_PROCESS_FILTER_SUPPORTED_NOT_CALIBRATED',
    apple_helper='USER_LOADED_VERIFIED', rvi_start='SUCCEEDED', rvi_stop='SUCCEEDED',
    link_type_query='PKTAP_AND_RAW_SUPPORTED', process_filter_query='COMPILED_SUCCESSFULLY',
    packet_capture='NOT_STARTED', next_action='BOUNDED_POSITIVE_PROCESS_ATTRIBUTION_CALIBRATION',
    persistent_security_setting_changes=False)
CALIBRATION = dict(
    scope='EILO_LOOPBACK_ATTRIBUTION_CALIBRATION', status='ATTRIBUTION_NOT_CALIBRATED',
    packet_lines_retained=False, packet_files_created=False, observer_ready=True,
    interface_stopped=True, marker_send_result_bytes=41, inference_started=False)


def fixed_fields(report, fixed, variable=()):
    if type(report) is not dict or set(report) != set(fixed) | set(variable):
        raise ValueError('Closed redacted evidence fields required')
    for key, value in fixed.items():
        if type(report[key]) is not type(value) or report[key] != value:
            raise ValueError('Blocked evidence cannot change prerequisite or acceptance: ' + key)


def validate(preflight, calibration):
    fixed_fields(preflight, {**COMMON, **PREFLIGHT})
    fixed_fields(calibration, {**COMMON, **CALIBRATION},
                 ('matching_marker_count', 'metadata_marker_count', 'elapsed_seconds', 'limitation'))
    matches = calibration['matching_marker_count']
    attributed = calibration['metadata_marker_count']
    if type(matches) is not int or type(attributed) is not int or not 0 <= attributed <= matches:
        raise ValueError('Marker counts must be nonnegative integers with attributed <= matching')
    if attributed != 0:
        raise ValueError('Positive attribution needs a separately reviewed evidence schema')
    duration = calibration['elapsed_seconds']
    if type(duration) not in (int, float) or not math.isfinite(duration) or not 0 < duration <= 180:
        raise ValueError('Observation must respect the approved 180-second bound')
    # Do not echo arbitrary diagnostic text into generated reports.
    limitation = calibration['limitation']
    if type(limitation) is not str or not 1 <= len(limitation) <= 240 or any(
            token in limitation for token in ('<', '>', '\n', '://', '@')):
        raise ValueError('Bounded redacted diagnostic text required')
    return dict(
        schema_version=1, scope='IOS_RVI_BLOCKED_EVIDENCE_REVIEW',
        network_observation='NOT_RUN', physical_gate_acceptance='NOT_RUN',
        target_attribution='NOT_ESTABLISHED', packet_count=None, sent_bytes=None,
        received_bytes=None, matching_marker_count=matches, metadata_marker_count=attributed,
        observer_seconds=duration, interface_stopped=True,
        conclusion='Calibration did not establish Eilo attribution. Marker counts are not traffic counts.')


def load(path):
    raw = path.read_bytes()
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique), hashlib.sha256(raw).hexdigest()


def render(report):
    # Only validated, selected aggregate fields are rendered. No input path or free text.
    rows = ''.join('<tr><th scope="row">' + html.escape(key.replace('_', ' ')) +
                   '</th><td>' + html.escape('unavailable' if value is None else str(value)) + '</td></tr>'
                   for key, value in report.items() if key != 'conclusion')
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Eilo USB observer review</title><style>body{font:17px system-ui;'
            'max-width:62rem;margin:2rem auto;padding:0 1rem;color:#182332;background:#fff}'
            'table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:.6rem;'
            'border-bottom:1px solid #ccd3da;overflow-wrap:anywhere}h1{font-size:1.7rem}</style>'
            '<h1>Network verification: NOT_RUN</h1><p>' + html.escape(report['conclusion']) +
            '</p><table><caption>Redacted calibration evidence</caption>' + rows + '</table></html>\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('preflight', type=Path)
    parser.add_argument('calibration', type=Path)
    parser.add_argument('--json-output', type=Path)
    parser.add_argument('--html-output', type=Path)
    args = parser.parse_args()
    destinations = [p.resolve() for p in (args.json_output, args.html_output) if p]
    sources = {args.preflight.resolve(), args.calibration.resolve()}
    if len(set(destinations)) != len(destinations) or sources.intersection(destinations):
        parser.error('Outputs must be distinct from one another and from source evidence')
    preflight, preflight_sha = load(args.preflight)
    calibration, calibration_sha = load(args.calibration)
    report = validate(preflight, calibration)
    report.update(preflight_sha256=preflight_sha, calibration_sha256=calibration_sha)
    if args.json_output:
        args.json_output.write_text(json.dumps(report, indent=2) + '\n')
    if args.html_output:
        args.html_output.write_text(render(report))
    print('RVI evidence valid; attribution not calibrated; network verification NOT_RUN.')


if __name__ == '__main__':
    main()
