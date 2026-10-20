import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch
from resident_wrapper import resident_wrapper
from model_wrapper import PINS


class ResidentWrapperTests(unittest.TestCase):
    def test_exact_derivation_keeps_generation_erasure_and_candidate_inventory(self):
        source=Path(__file__).parents[1].joinpath('llm-runtime/eilo_llm.cc').read_bytes()
        compiled,e=resident_wrapper(source)
        self.assertEqual(hashlib.sha256(compiled).hexdigest(),e['compiled_source_sha256'])
        self.assertEqual([(x['model'],x['bytes'],x['sha256']) for x in e['candidates']],[(m,*p) for m,p in PINS.items()])
        cleanup=source[source.index(b'    if (batch)'):source.index(b'    if (model)')]
        self.assertIn(cleanup,compiled)
        for guard in [b'std::strcmp(architecture, "qwen3")',b'std::strcmp(quantization, "15")',b'trial_residency.generations >= 3',b'info.st_ino != trial_residency.inode']:
            self.assertIn(guard,compiled)
        self.assertIn(b'if (reason != EILO_LLM_DONE) trial_residency.drop()',compiled)

    def test_changed_candidate_inventory_rejected(self):
        source=Path(__file__).parents[1].joinpath('llm-runtime/eilo_llm.cc').read_bytes()
        with patch.dict(PINS, {'Qwen3-0.6B-Q4_K_M':(484219808,'0'*64)}):
            with self.assertRaises(ValueError):resident_wrapper(source)

    def test_unreviewed_base_rejected(self):
        source=Path(__file__).parents[1].joinpath('llm-runtime/eilo_llm.cc').read_bytes()
        with self.assertRaises(ValueError):resident_wrapper(source+b'\n')


if __name__=='__main__':unittest.main()
