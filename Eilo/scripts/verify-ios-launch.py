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
args = parser.parse_args()


def sim(*commands, check=True):
    return subprocess.run(['xcrun', 'simctl', *commands], text=True,
                          capture_output=True, check=check)


inventory = json.loads(sim('list', 'devices', 'booted', '--json').stdout)
assert any(device['udid'] == args.udid and device['state'] == 'Booted'
           for devices in inventory['devices'].values() for device in devices), 'Requested simulator is not booted'
sim('get_app_container', args.udid, BUNDLE, 'app')
for cycle in range(args.cycles):
    sim('terminate', args.udid, BUNDLE, check=False)
    launched = sim('launch', args.udid, BUNDLE)
    pid = launched.stdout.strip().rsplit(': ', 1)[1]
    time.sleep(args.dwell)
    processes = sim('spawn', args.udid, 'launchctl', 'list').stdout.splitlines()
    assert any(line.startswith(pid + '\t') and BUNDLE in line for line in processes), 'Eilo exited during launch check'
    print(f'Cold launch {cycle + 1}: PASS after {args.dwell}s', flush=True)
