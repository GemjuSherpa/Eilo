import tempfile
import unittest
from pathlib import Path
from network_trace import plan

DEVICE = "00008150-0000000000000001"


class NetworkTraceTests(unittest.TestCase):
    def test_only_explicit_bounded_device_process_target_without_execution(self):
        with tempfile.TemporaryDirectory() as d:
            p = plan(DEVICE, 123, 300, Path(d)/'local.trace')
            command = p['command']
            self.assertEqual(command[command.index('--attach')+1], '123')
            self.assertEqual(command[command.index('--device')+1], DEVICE)
            self.assertEqual(command[command.index('--time-limit')+1], '300s')
            for prohibited in ['--all-processes', '--no-prompt', '--har', '--launch']:
                self.assertNotIn(prohibited, command)
            self.assertEqual(p['recording'], 'NOT_RUN')
            self.assertEqual(p['coverage'], 'NOT_ESTABLISHED')
            self.assertEqual(p['physical_gate_acceptance'], 'NOT_RUN')

    def test_unbounded_target_duration_and_existing_trace_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            new = Path(d)/'new.trace'
            for pid in [True, 0, -1, 1.5, '123', 2**31]:
                with self.assertRaises(ValueError): plan(DEVICE, pid, 300, new)
            for seconds in [True, 0, 29, 1201, 30.5, '300']:
                with self.assertRaises(ValueError): plan(DEVICE, 123, seconds, new)
            for path in [Path('relative.trace'), Path(d)/'wrong.har']:
                with self.assertRaises(ValueError): plan(DEVICE, 123, 300, path)
            for device in [None, "", "all", "iPhone", "00008150-0000000000000001; command"]:
                with self.assertRaises(ValueError): plan(device, 123, 300, new)
            new.mkdir()
            with self.assertRaises(ValueError): plan(DEVICE, 123, 300, new)
