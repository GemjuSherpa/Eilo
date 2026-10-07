"""Synthetic simulator responses; no device commands or data access."""
import argparse
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('launch', Path(__file__).with_name('verify-ios-launch.py'))
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)


class LaunchVerificationTests(unittest.TestCase):
    def run_check(self, inventory=None, response=None, processes=None):
        args = argparse.Namespace(udid='synthetic', cycles=1, dwell=5)
        replies = [
            inventory or '{"devices":{"test":[{"udid":"synthetic","state":"Booted"}]}}',
            '/synthetic/app', '',
            response if response is not None else launch.BUNDLE + ': 42',
            processes if processes is not None else '42\t0\t' + launch.BUNDLE,
        ]
        with patch.object(launch, 'sim', side_effect=[argparse.Namespace(stdout=x) for x in replies]), patch.object(launch.time, 'sleep'), patch('builtins.print') as output:
            try:
                launch.verify_launches(args)
            except ValueError:
                output.assert_not_called()
                raise
            output.assert_called_once()

    def test_live_matching_pid(self):
        self.run_check()

    def test_unbooted_device_rejected(self):
        with self.assertRaises(ValueError):
            self.run_check(inventory='{"devices":{}}')

    def test_exited_or_different_pid_rejected(self):
        for processes in ('', '43\t0\t' + launch.BUNDLE, '42\t0\tother.app'):
            with self.subTest(processes=processes), self.assertRaises(ValueError):
                self.run_check(processes=processes)

    def test_invalid_launch_output_rejected(self):
        for response in ('', launch.BUNDLE + ': 0', launch.BUNDLE + ': unknown', 'other.app: 42'):
            with self.subTest(response=response), self.assertRaises(ValueError):
                self.run_check(response=response)

    def test_device_commands_have_deadline(self):
        with patch.object(subprocess, 'run') as run:
            launch.sim('list', 'devices')
            self.assertEqual(run.call_args.kwargs['timeout'], 30)


if __name__ == '__main__':
    unittest.main()
