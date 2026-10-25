"""跨平台的小工具：导入/模型准备的独占锁与后台进程存活检查（macOS、Linux、Windows）。"""
import os
import sys


def try_lock(stream):
    """对已打开的锁文件加非阻塞独占锁；已被占用时抛出 BlockingIOError。文件关闭即释放。"""
    if sys.platform == 'win32':
        import msvcrt
        stream.seek(0)
        try: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError: raise BlockingIOError('lock is held by another process') from None
    else:
        import fcntl
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)


def pid_alive(pid):
    """只查询进程是否仍在运行，不发送任何信号。

    Windows 上 os.kill(pid, 0) 会发送 CTRL_C_EVENT，不能用于探测，因此改用进程句柄查询。
    """
    if type(pid) is not int or pid <= 0: return False
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle: return ctypes.get_last_error() == 5  # 拒绝访问说明进程存在
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)): return False
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try: os.kill(pid, 0)
    except ProcessLookupError: return False
    except PermissionError: return True
    return True
