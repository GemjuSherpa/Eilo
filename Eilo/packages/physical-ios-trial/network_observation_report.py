"""Validate redacted blocked collection evidence; this schema cannot accept a no-traffic claim."""
import argparse
import json
import re
from pathlib import Path

FIXED = dict(schema_version=1, scope='IOS_CONNECTIONS_ONLY_OBSERVATION_ATTEMPT',
             bundle_id='com.eilo.ForegroundVoiceTrial', status='ATTACHMENT_FAILED',
             network_observation='NOT_RUN', coverage='NOT_ESTABLISHED',
             physical_gate_acceptance='NOT_RUN', connection_count=None, sent_bytes=None,
             received_bytes=None, payload_exported=False, microphone='NOT_OPENED', speaker='NOT_OPENED')
VARIABLE = {'source_app_binary_sha256', 'attempts', 'initial_network_template', 'gui_target'}


def exact(a, b):
    if type(a) is not type(b): return False
    if type(a) is dict: return set(a)==set(b) and all(exact(a[k],b[k]) for k in a)
    return a==b


def validate(report):
    if type(report) is not dict or set(report) != set(FIXED)|VARIABLE:
        raise ValueError('closed aggregate fields required')
    for key, value in FIXED.items():
        if type(report[key]) is not type(value) or report[key] != value:
            raise ValueError('blocked collection cannot claim metrics or acceptance: '+key)
    digest = report['source_app_binary_sha256']
    if type(digest) is not str or not re.fullmatch('[0-9a-f]{64}', digest):
        raise ValueError('source binary digest required')
    attempts = report['attempts']
    if type(attempts) is not list or not 1 <= len(attempts) <= 8:
        raise ValueError('bounded actual attempts required')
    for row in attempts:
        if type(row) is not dict or set(row) != {'template','instrument','target','exit_code','result'}:
            raise ValueError('closed attempt fields required')
        if row['template'] not in ['NONE','Blank'] or row['instrument'] != 'Network Connections':
            raise ValueError('connections-only attempt required')
        expected = {'PID':(21,'PROCESS_NOT_FOUND'), 'EXECUTABLE_NAME':(19,'PROCESS_NAME_NOT_FOUND')}
        if row['target'] not in expected or type(row['exit_code']) is not int or (row['exit_code'],row['result']) != expected[row['target']]:
            raise ValueError('actual attachment failure required')
    if not exact(report['initial_network_template'], dict(disposition='CANCELLED_EXCLUDED_BROADER_HTTP_PROMPT',trace_created=True,local_trace_removed=True,http_contents_inspected=False,http_contents_exported=False,system_logs='NOT_INSPECTED_OR_CLEARED')):
        raise ValueError('initial attempt disposition required')
    if not exact(report['gui_target'], dict(verified='EILO_PID_SELECTED',instrument='Network Connections',recording='NOT_STARTED_RECORD_CONTROL_DISABLED')):
        raise ValueError('GUI target/recording scope required')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('report',type=Path);args=parser.parse_args()
    validate(json.loads(args.report.read_text()));print('Blocked observation evidence valid; no network absence or physical acceptance established.')
