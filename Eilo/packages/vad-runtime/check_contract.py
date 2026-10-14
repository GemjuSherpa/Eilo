"""Build/run bounded native contracts with sanitizers; no models, downloads or microphone."""
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent

if __name__ == '__main__':
    compiler = shutil.which('clang++') or shutil.which('c++')
    if not compiler:
        raise SystemExit('C++17 compiler unavailable')
    with tempfile.TemporaryDirectory(prefix='eilo-vad-contract-') as temp:
        target = str(Path(temp) / 'contract')
        subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-I', str(HERE / 'include'), '-I', str(HERE), str(HERE / 'eilo_vad.cc'),
                        str(HERE / 'tests/contract.cc'), '-o', target], check=True, timeout=120)
        subprocess.run([target], check=True, timeout=30)
    print('Native VAD contract PASS under address/undefined-behavior sanitizers; no acoustic claim.')
