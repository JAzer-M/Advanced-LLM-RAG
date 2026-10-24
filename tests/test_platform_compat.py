# 跨平台锁与进程检查：macOS/Linux 用 fcntl 与 os.kill(pid, 0)，Windows 用 msvcrt 与进程句柄。
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.platform_compat import pid_alive, try_lock


class PlatformCompatTests(unittest.TestCase):
    def test_second_handle_cannot_take_a_held_lock_until_it_is_released(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)/'import.lock'
            with path.open('a') as first:
                try_lock(first)
                with path.open('a') as second, self.assertRaises(BlockingIOError):
                    try_lock(second)
            with path.open('a') as third:
                try_lock(third)

    def test_running_and_finished_processes_are_told_apart_without_signalling(self):
        self.assertTrue(pid_alive(os.getpid()))
        child = subprocess.Popen([sys.executable, '-c', 'pass'])
        child.wait()
        self.assertFalse(pid_alive(child.pid))
        self.assertFalse(pid_alive(0))
        self.assertFalse(pid_alive('123'))


if __name__ == '__main__':
    unittest.main()
