"""Bounded retries for dependency preparation only; builds/tests run separately once."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def terminate(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    # A downloader child may remain after its shell exits.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def prepare(command, attempts=3, timeout=480, delay=5):
    for attempt in range(1, attempts + 1):
        print(f'Dependency preparation attempt {attempt}/{attempts}', flush=True)
        process = subprocess.Popen(command, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            print('Dependency preparation deadline exceeded; stopping download children.', flush=True)
            code = 124
        finally:
            terminate(process)
        if code == 0:
            return 0
        if attempt < attempts:
            time.sleep(delay)
    return code


def command_for(mode):
    if mode == 'android':
        return ['./gradlew', '--no-daemon', '--init-script',
                str(Path(__file__).with_name('ci-resolve-android.gradle').resolve()),
                '-Dorg.gradle.internal.http.connectionTimeout=30000',
                '-Dorg.gradle.internal.http.socketTimeout=60000',
                'ciResolveAndroidDependencies', '--max-workers=2']
    return ['bundle', 'exec', 'pod', 'install', '--deployment']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['android', 'pods'])
    args = parser.parse_args()
    def interrupted(_signal, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    try:
        sys.exit(prepare(command_for(args.mode)))
    except KeyboardInterrupt:
        sys.exit(130)
