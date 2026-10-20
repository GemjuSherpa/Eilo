import hashlib
from pathlib import Path
import unittest
from phase_wrapper import phase_wrapper, KEYS
from model_wrapper import PINS, wrapper


class PhaseWrapperTests(unittest.TestCase):
    def test_exact_source_pins_cleanup_and_distinct_optional_variant(self):
        source = Path(__file__).parents[1].joinpath('llm-runtime/eilo_llm.cc').read_bytes()
        for model, (size, digest) in PINS.items():
            pin = dict(model=model, bytes=size, sha256=digest)
            base, _ = wrapper(source, pin)
            result, evidence = phase_wrapper(source, pin)
            self.assertNotEqual(result, base)
            self.assertEqual(evidence['size_specialized_source_sha256'], hashlib.sha256(base).hexdigest())
            self.assertEqual(evidence['compiled_source_sha256'], hashlib.sha256(result).hexdigest())
            self.assertEqual(evidence['timing_fields'], list(KEYS))
            # Retain entire lifecycle erasure block and all existing metadata checks.
            cleanup = source[source.index(b'  void clear() {'):source.index(b'  ~EiloLlm()')]
            self.assertIn(cleanup, result)
            for guard in [b'info.st_size != kModelBytes', b'std::strcmp(architecture, "qwen3")', b'std::strcmp(quantization, "15")']:
                self.assertIn(guard, result)
            self.assertIn(b'thread_local TrialMetrics', result)

    def test_unknown_source_and_candidates_fail_closed(self):
        source = Path(__file__).parents[1].joinpath('llm-runtime/eilo_llm.cc').read_bytes()
        pin = dict(model='Qwen3-0.6B-Q4_K_M', bytes=484219808, sha256=PINS['Qwen3-0.6B-Q4_K_M'][1])
        with self.assertRaises(ValueError):phase_wrapper(source+b'\n', pin)
        for key, value in [('model', 'arbitrary'), ('bytes', True), ('sha256', '0'*64)]:
            with self.assertRaises(ValueError):phase_wrapper(source, dict(pin, **{key:value}))


if __name__ == '__main__':unittest.main()
