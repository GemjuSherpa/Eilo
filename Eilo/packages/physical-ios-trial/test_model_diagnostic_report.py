import copy
import unittest
from model_diagnostic_report import FIXED, validate, validate_pair


def sample():
    return dict(FIXED, phase='COMPLETED', process_id='12345678-1234-1234-1234-123456789ABC',
                model_sha256='c0efea3254c2363a9559e32ac76e9987aff3a68c31b84a3e65c12aa5c01bd120', model_bytes=1282439424,
                os_build='Version 26.6.1 (Build 23G83)', physical_memory_bytes=12262113280, updated_utc='2026-10-19T12:00:00Z',
                cases=[dict(fixture_id=f'compare-{i:02d}', prompt_tokens=100, native_piece_count=10, output_bytes=40,
                            verified_open_and_load_ms=100, begin_wall_ms=1000, first_native_piece_from_begin_ms=1100,
                            generation_wall_ms=3000, memory=dict(current_phys_footprint_bytes=1000000000, process_lifetime_peak_bytes=1100000000)) for i in range(1, 7)])


class DiagnosticTests(unittest.TestCase):
    def test_complete_and_stopped(self):
        validate(sample())
        for phase in ('RUNNING', 'CANCELLED', 'INFERENCE_FAILED'):
            report = sample();report.update(phase=phase, cases=[]);validate(report)

    def test_rejects_content_and_acceptance(self):
        changes = [('quality', 'PASS'), ('network_observation', 'NO_TRAFFIC_VERIFIED'), ('physical_gate_acceptance', 'PASS'), ('raw_text_exported', True), ('transcript', 'content'), ('model_sha256', '0'*64), ('threads', True)]
        for key, value in changes:
            report = sample();report[key] = value
            with self.assertRaises(ValueError):validate(report)

    def test_missing_duplicate_order_and_partial(self):
        for mode in ('missing', 'duplicate', 'reordered', 'partial'):
            report = sample()
            if mode == 'missing':report['cases'].pop()
            elif mode == 'duplicate':report['cases'][1] = copy.deepcopy(report['cases'][0])
            elif mode == 'reordered':report['cases'].reverse()
            else:report['phase'] = 'CANCELLED'
            with self.assertRaises(ValueError):validate(report)

    def test_pair_requires_distinct_candidates_and_processes(self):
        import json
        from pathlib import Path
        reports = [sample(), sample()]
        with self.assertRaises(ValueError):validate_pair(reports)
        pin = json.loads(Path(__file__).with_name('tests').joinpath('model-comparison-pins.json').read_text())[1]
        reports[1].update(model_sha256=pin['sha256'], model_bytes=pin['bytes'])
        with self.assertRaises(ValueError):validate_pair(reports)
        reports[1]['process_id'] = '87654321-1234-1234-1234-123456789ABC'
        validate_pair(reports)
        reports[1].update(phase='RUNNING', cases=[])
        with self.assertRaises(ValueError):validate_pair(reports)

    def test_timing_and_memory(self):
        for key, value in [('begin_wall_ms', float('nan')), ('generation_wall_ms', 1), ('native_piece_count', 257), ('prompt_tokens', True), ('output_bytes', 999999)]:
            report = sample();report['cases'][0][key] = value
            with self.assertRaises(ValueError):validate(report)
        report = sample();report['cases'][1]['memory']['process_lifetime_peak_bytes'] = 1000000000
        with self.assertRaises(ValueError):validate(report)
        report = sample();report['cases'][0]['memory']['transcript'] = 'denied'
        with self.assertRaises(ValueError):validate(report)


if __name__ == '__main__':unittest.main()
