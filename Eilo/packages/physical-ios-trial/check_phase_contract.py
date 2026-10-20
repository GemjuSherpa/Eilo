"""Offline lab telemetry ASan/UBSan checks against a verified existing runtime source cache."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from phase_wrapper import phase_wrapper
from model_wrapper import PINS

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--llm-cache', type=Path, required=True)
    a = p.parse_args()
    llm = HERE.parent / 'llm-runtime'
    prov = json.loads((llm / 'provenance.json').read_text())
    archive = a.llm_cache / 'llama-v0.6.0.tar.gz'
    source = a.llm_cache / ('llama.cpp-' + prov['runtime']['commit'])
    with archive.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != prov['runtime']['source_archive_sha256']:
            raise ValueError('runtime archive changed')
    spec = importlib.util.spec_from_file_location('phase_host', llm / 'check_host.py')
    host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)
    host.verify_tree(archive, source, source.name)
    size, digest = PINS['Qwen3-1.7B-Q4_K_M']
    compiled, _ = phase_wrapper((llm / 'eilo_llm.cc').read_bytes(), dict(model='Qwen3-1.7B-Q4_K_M', bytes=size, sha256=digest))
    with tempfile.TemporaryDirectory(prefix='eilo-phase-contract-') as folder:
        folder = Path(folder)
        wrapper = folder / 'phase.cc'; wrapper.write_bytes(compiled)
        backend = (llm / 'tests/contract.cc').read_text()
        if backend.count('int main() {') != 1:
            raise ValueError('scripted backend boundary changed')
        extra = folder / 'phase_contract.cc'
        extra.write_text(backend.split('int main() {')[0] + (HERE / 'tests/phase_contract.cc').read_text())
        base = ['xcrun', 'clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                '-I'+str(HERE / 'include'), '-I'+str(llm / 'include'), '-I'+str(source / 'include'), '-I'+str(source / 'ggml/include'), str(wrapper)]
        for label, contract in [('original', llm / 'tests/contract.cc'), ('phase', extra)]:
            executable = folder / label
            subprocess.run([*base, str(contract), '-o', str(executable)], check=True, timeout=60)
            subprocess.run([str(executable)], check=True, timeout=60)


if __name__ == '__main__':main()
