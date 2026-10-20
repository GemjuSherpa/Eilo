"""Plan a bounded, process-targeted local trace; never starts recording or infers offline acceptance."""
import argparse
import json
import re
from pathlib import Path

BUNDLE = 'com.eilo.ForegroundVoiceTrial'
MAX_SECONDS = 1200


def plan(device, pid, seconds, output):
    if type(device) is not str or not re.fullmatch(r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{16}", device):
        raise ValueError("explicit physical iPhone UDID required")
    if type(pid) is not int or not 1 <= pid <= 2**31-1:
        raise ValueError('verified live Eilo PID required')
    if type(seconds) is not int or not 30 <= seconds <= MAX_SECONDS:
        raise ValueError('recording duration must be 30..1200 seconds')
    output = Path(output)
    if not output.is_absolute() or output.suffix != '.trace' or output.exists():
        raise ValueError('new absolute local .trace path required')
    return {
        'schema_version': 1, 'scope': 'EILO_PROCESS_TARGETED_NETWORK_TRACE_PLAN',
        'bundle_id': BUNDLE, 'pid': pid, 'duration_seconds': seconds,
        'recording': 'NOT_RUN', 'permission': 'EXPLICIT_OPERATOR_APPROVAL_REQUIRED',
        'privacy': 'MAY_INCLUDE_HTTP_CONTENT_AND_RELATED_SYSTEM_METADATA_KEEP_LOCAL',
        'export_policy': 'REDACTED_COUNTS_AND_PROVENANCE_ONLY_NO_HAR_OR_PAYLOAD_EXPORT',
        'coverage': 'NOT_ESTABLISHED', 'physical_gate_acceptance': 'NOT_RUN',
        'command': ['xcrun', 'xctrace', 'record', '--template', 'Network',
                    '--device', device, '--attach', str(pid),
                    '--time-limit', f'{seconds}s', '--output', str(output)],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', required=True)
    parser.add_argument('--pid', required=True, type=int)
    parser.add_argument('--seconds', default=300, type=int)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(plan(args.device, args.pid, args.seconds, args.output), indent=2))
