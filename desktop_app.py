"""Self-contained Windows entry point; the browser remains the app's interface."""

import argparse
from contextlib import contextmanager
import ctypes
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser


ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = 8502


def data_directory():
    directory = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share"))) / "EduAI-Audit"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def health_ready(port):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://127.0.0.1:{port}/_stcore/health", timeout=1) as response:
            return response.status == 200 and response.read(32).strip() == b"ok"
    except (OSError, urllib.error.URLError):
        return False


@contextmanager
def process_handle(pid):
    """Open and verify the same Windows process before reuse or termination."""
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000 | 0x0001 | 0x00100000, False, pid)
    try:
        valid = False
        if handle:
            name = ctypes.create_unicode_buffer(32768)
            size = wintypes.DWORD(len(name))
            code = wintypes.DWORD()
            valid = bool(kernel.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size))
                         and kernel.GetExitCodeProcess(handle, ctypes.byref(code)) and code.value == 259
                         and Path(name.value).resolve() == Path(sys.executable).resolve())
        yield (kernel, handle) if valid else None
    finally:
        if handle:
            kernel.CloseHandle(handle)


def saved_process(directory, port):
    try:
        data = json.loads((directory / f"instance-{port}.json").read_text(encoding="utf-8"))
        if data["executable"] == str(Path(sys.executable).resolve()) and type(data["pid"]) is int and data["pid"] > 0:
            return data["pid"]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def own_server_ready(directory, port):
    pid = saved_process(directory, port)
    if pid is None:
        return False
    with process_handle(pid) as process:
        return process is not None and health_ready(port)


@contextmanager
def startup_lock(directory, port):
    import msvcrt

    with (directory / f"startup-{port}.lock").open("a+b") as lock:
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        deadline = time.monotonic() + 90
        while True:
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("EduAI Audit is still starting. Try again shortly.") from None
                time.sleep(.25)
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def serve(port, directory):
    # A windowed frozen executable has no stdout/stderr. Streamlit writes to both.
    with (directory / "app.log").open("a", encoding="utf-8", buffering=1) as log:
        sys.stdout = sys.stderr = log
        from streamlit import config
        from streamlit.web import bootstrap

        script = str(ROOT / "app.py")
        config._main_script_path = script
        options = {"global.developmentMode": False, "server.address": "127.0.0.1", "server.port": port,
                   "server.headless": True, "browser.gatherUsageStats": False, "server.fileWatcherType": "none",
                   "server.runOnSave": False}
        bootstrap.load_config_options(flag_options=options)
        bootstrap.run(script, False, [], options)


def start_app(directory, port, *, open_browser=True):
    with startup_lock(directory, port):
        if not own_server_ready(directory, port):
            # Do not accidentally open another Streamlit project using this port.
            with socket.socket() as probe:
                try:
                    probe.bind(("127.0.0.1", port))
                except OSError:
                    raise RuntimeError(f"Port {port} is in use. Close the other app or start EduAI Audit with --port NUMBER.") from None
            command = [sys.executable]
            if not getattr(sys, "frozen", False):
                command.append(str(Path(__file__).resolve()))
            command.extend(["--serve", "--port", str(port)])
            with (directory / "app.log").open("ab") as log:
                process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            marker = directory / f"instance-{port}.json"
            temporary = marker.with_suffix(".tmp")
            temporary.write_text(json.dumps({"pid": process.pid, "executable": str(Path(sys.executable).resolve())}), encoding="utf-8")
            temporary.replace(marker)
            deadline = time.monotonic() + 90
            while not health_ready(port):
                if process.poll() is not None or time.monotonic() >= deadline:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=10)
                    marker.unlink(missing_ok=True)
                    raise RuntimeError(f"Could not start EduAI Audit. Startup log: {directory / 'app.log'}")
                time.sleep(.25)
    if open_browser and not webbrowser.open(f"http://127.0.0.1:{port}/", new=2):
        raise RuntimeError(f"EduAI Audit is running. Open http://127.0.0.1:{port}/ in your browser.")


def stop_app(directory, port):
    with startup_lock(directory, port):
        pid = saved_process(directory, port)
        if pid is not None:
            with process_handle(pid) as process:
                if process is not None:
                    kernel, handle = process
                    if not kernel.TerminateProcess(handle, 0):
                        raise OSError("Could not stop EduAI Audit.")
                    kernel.WaitForSingleObject(handle, 10000)
            (directory / f"instance-{port}.json").unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="EduAI Audit desktop application")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    action.add_argument("--stop", action="store_true", help="Stop the local application")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    directory = data_directory()
    try:
        if args.serve:
            serve(args.port, directory)
        elif args.stop:
            stop_app(directory, args.port)
        else:
            start_app(directory, args.port, open_browser=not args.no_browser)
    except Exception as exc:
        with (directory / "app.log").open("a", encoding="utf-8") as log:
            import traceback
            traceback.print_exc(file=log)
        if not args.no_browser and not args.serve:
            ctypes.windll.user32.MessageBoxW(None, str(exc), "EduAI Audit", 0x10)
        return 1
    return 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    raise SystemExit(main())
