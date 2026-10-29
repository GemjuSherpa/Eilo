import importlib.util
from pathlib import Path
import subprocess
import signal
import time
import os
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('ci_dependencies', Path(__file__).with_name('ci-dependencies.py'))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class DependencyPreparationTests(unittest.TestCase):
    def test_retry_retains_completed_preparation(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'attempt'
            command = [sys.executable, '-c',
                       'from pathlib import Path; import sys; p=Path(sys.argv[1]); old=p.exists(); p.write_text("cached"); sys.exit(0 if old else 7)', str(marker)]
            self.assertEqual(c.prepare(command, attempts=2, timeout=5, delay=0), 0)
            self.assertEqual(marker.read_text(), 'cached')

    def test_failure_does_not_become_success(self):
        self.assertEqual(c.prepare([sys.executable, '-c', 'raise SystemExit(9)'], attempts=2, timeout=5, delay=0), 9)

    def test_success_is_not_repeated(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'count'
            command = [sys.executable, '-c',
                       'from pathlib import Path; import sys; p=Path(sys.argv[1]); p.write_text(p.read_text()+"x" if p.exists() else "x")', str(marker)]
            self.assertEqual(c.prepare(command, timeout=5), 0)
            self.assertEqual(marker.read_text(), 'x')

    def test_deadline_stops_downloader_child(self):
        import time
        with tempfile.TemporaryDirectory() as folder:
            ready, late = Path(folder) / 'ready', Path(folder) / 'late'
            child = 'from pathlib import Path; import sys,time; Path(sys.argv[1]).write_text("ready"); time.sleep(2); Path(sys.argv[2]).write_text("survived")'
            parent = 'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",sys.argv[1],sys.argv[2],sys.argv[3]]); time.sleep(60)'
            command = [sys.executable, '-c', parent, child, str(ready), str(late)]
            self.assertEqual(c.prepare(command, attempts=1, timeout=1, delay=0), 124)
            self.assertTrue(ready.exists())
            time.sleep(2)
            self.assertFalse(late.exists(), 'downloader survived timeout cleanup')

    def test_cancellation_stops_preparation_children(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ready, late = root / 'ready', root / 'late'
            tool = root / 'bundle'
            tool.write_text('#!' + sys.executable + '\nimport os,time\nfrom pathlib import Path\nPath(os.environ["READY"]).write_text("ready")\ntime.sleep(2)\nPath(os.environ["LATE"]).write_text("survived")\n')
            tool.chmod(0o700)
            env = dict(os.environ, PATH=str(root)+os.pathsep+os.environ['PATH'], READY=str(ready), LATE=str(late))
            process = subprocess.Popen([sys.executable, str(Path(c.__file__)), 'pods'], env=env)
            try:
                deadline = time.monotonic() + 5
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(ready.exists())
                process.send_signal(signal.SIGTERM)
                self.assertEqual(process.wait(timeout=5), 130)
                time.sleep(2)
                self.assertFalse(late.exists())
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()

    def test_only_dependency_commands_and_locked_pods(self):
        android = c.command_for('android')
        self.assertIn('ciResolveAndroidDependencies', android)
        self.assertFalse(any('assemble' in x or 'testDebug' in x for x in android))
        self.assertEqual(c.command_for('pods'), ['bundle', 'exec', 'pod', 'install', '--deployment'])


if __name__ == '__main__':
    unittest.main()
