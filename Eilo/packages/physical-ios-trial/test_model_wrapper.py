import unittest
from pathlib import Path
from model_wrapper import PINS, wrapper


class WrapperTests(unittest.TestCase):
    def test_only_reviewed_size_literal_changes(self):
        source = Path(__file__).parents[1].joinpath('llm-runtime/eilo_llm.cc').read_bytes()
        for model, (size, digest) in PINS.items():
            result, evidence = wrapper(source, dict(model=model, bytes=size, sha256=digest))
            self.assertEqual(result, source.replace(b'kModelBytes = 1282439424;', ('kModelBytes = '+str(size)+';').encode()))
            self.assertEqual(evidence['required_model_bytes'], size)
            self.assertIn(b'info.st_size != kModelBytes', result)
            self.assertIn(b'std::strcmp(architecture, "qwen3")', result)
            self.assertIn(b'std::strcmp(quantization, "15")', result)
        default, _ = wrapper(source, dict(model='Qwen3-1.7B-Q4_K_M', bytes=PINS['Qwen3-1.7B-Q4_K_M'][0], sha256=PINS['Qwen3-1.7B-Q4_K_M'][1]))
        self.assertEqual(default, source)

    def test_unreviewed_source_or_candidate_denied(self):
        source = Path(__file__).parents[1].joinpath('llm-runtime/eilo_llm.cc').read_bytes()
        pin = dict(model='Qwen3-0.6B-Q4_K_M', bytes=484219808, sha256=PINS['Qwen3-0.6B-Q4_K_M'][1])
        with self.assertRaises(ValueError):wrapper(source+b'\n', pin)
        for key, value in [('model', 'arbitrary'), ('bytes', True), ('bytes', 484219809), ('sha256', '0'*64)]:
            with self.assertRaises(ValueError):wrapper(source, dict(pin, **{key:value}))


if __name__ == '__main__':unittest.main()
