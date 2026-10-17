"""Desktop entry point: reuse a running local app or start it without a console."""

import argparse
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser


ROOT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8501/"
LOG = ROOT / ".venv" / "eduai-app.log"


def app_ready():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(URL + "_stcore/health", timeout=1) as response:
            return response.status == 200 and response.read(32).strip() == b"ok"
    except (OSError, urllib.error.URLError):
        return False


@contextmanager
def startup_lock():
    """Two consecutive clicks share one startup, including on a cold launch."""
    with (ROOT / ".venv" / "eduai-startup.lock").open("a+b") as lock:
        if sys.platform == "win32":
            import msvcrt
            if lock.tell() == 0:
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            if sys.platform == "win32":
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def start_app(open_browser=True):
    python = ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.exists():
        raise RuntimeError("Среда Python не найдена. Выполните установку по инструкции README.md.")
    with startup_lock():
        if not app_ready():
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            with LOG.open("ab") as log:
                process = subprocess.Popen(
                    [str(python), "-m", "streamlit", "run", str(ROOT / "app.py"),
                     "--server.address=127.0.0.1", "--server.port=8501", "--server.headless=true"],
                    cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                    creationflags=flags, start_new_session=sys.platform != "win32",
                )
            deadline = time.monotonic() + 45
            while not app_ready():
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError(f"Не удалось запустить EduAI Audit. Журнал запуска: {LOG}")
                time.sleep(.25)
    if open_browser:
        if not webbrowser.open(URL, new=2):
            raise RuntimeError(f"Приложение запущено. Откройте в браузере: {URL}")


def main():
    parser = argparse.ArgumentParser(description="Start the local EduAI Audit app")
    parser.add_argument("--no-browser", action="store_true", help="Check startup without opening a browser")
    args = parser.parse_args()
    try:
        start_app(open_browser=not args.no_browser)
    except (OSError, RuntimeError) as exc:
        if sys.platform == "win32" and not args.no_browser:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, str(exc), "EduAI Audit", 0x10)
        elif sys.stderr:
            print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
