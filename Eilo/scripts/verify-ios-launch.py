#!/usr/bin/env python3
"""Eilo-only launch regression check; preserves simulator data/consent."""
import argparse
import json
import subprocess
import time

BUNDLE = 'org.reactjs.native.example.Eilo'
parser = argparse.ArgumentParser()
parser.add_argument('--udid', required=True, help='Explicit already-booted simulator UUID')
parser.add_argument('--cycles', type=int, choices=(1, 2, 3), default=3)
parser.add_argument('--dwell', type=int, choices=(5, 10, 30), default=5)


def sim(*commands, check=True):
    return subprocess.run(['xcrun', 'simctl', *commands], text=True,
                          capture_output=True, check=check, timeout=30)


def verify_launches(args):
    inventory = json.loads(sim('list', 'devices', 'booted', '--json').stdout)
    if not any(device['udid'] == args.udid and device['state'] == 'Booted'
               for devices in inventory['devices'].values() for device in devices):
        raise ValueError('Requested simulator is not booted')
    sim('get_app_container', args.udid, BUNDLE, 'app')
    for cycle in range(args.cycles):
        sim('terminate', args.udid, BUNDLE, check=False)
        launched = sim('launch', args.udid, BUNDLE)
        label, separator, pid = launched.stdout.strip().rpartition(': ')
        if label != BUNDLE or not separator or not pid.isdecimal() or int(pid) <= 0:
            raise ValueError('Unexpected Eilo launch response')
        time.sleep(args.dwell)
        processes = sim('spawn', args.udid, 'launchctl', 'list').stdout.splitlines()
        if not any(line.startswith(pid + '\t') and BUNDLE in line for line in processes):
            raise ValueError('Eilo exited during launch check')
        print(f'Cold launch {cycle + 1}: PASS after {args.dwell}s', flush=True)


if __name__ == '__main__':
    try:
        verify_launches(parser.parse_args())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        # Command output may contain device diagnostics; print only a safe category.
        parser.exit(1, f'Launch verification failed ({type(error).__name__}).\n')
