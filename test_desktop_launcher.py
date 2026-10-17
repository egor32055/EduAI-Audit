"""Desktop startup must use its own runtime and never reuse an unrelated server."""

from contextlib import nullcontext
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import desktop_app


class DesktopLauncherTests(unittest.TestCase):
    def test_frozen_start_needs_no_python_installation_and_records_owned_process(self):
        process = Mock(pid=12345)
        process.poll.return_value = None
        with TemporaryDirectory() as folder, \
             patch.object(desktop_app, "startup_lock", return_value=nullcontext()), \
             patch.object(desktop_app, "own_server_ready", return_value=False), \
             patch.object(desktop_app.socket, "socket"), \
             patch.object(desktop_app, "health_ready", side_effect=[False, True]), \
             patch.object(desktop_app.time, "sleep"), \
             patch.object(sys, "frozen", True, create=True), \
             patch.object(desktop_app.subprocess, "Popen", return_value=process) as spawn:
            desktop_app.start_app(Path(folder), 8512, open_browser=False)
            self.assertEqual(spawn.call_args.args[0], [sys.executable, "--serve", "--port", "8512"])
            saved = json.loads((Path(folder) / "instance-8512.json").read_text())
            self.assertEqual(saved["pid"], 12345)
            self.assertEqual(saved["executable"], str(Path(sys.executable).resolve()))

    def test_second_click_opens_existing_owned_server_without_spawning(self):
        with TemporaryDirectory() as folder, \
             patch.object(desktop_app, "startup_lock", return_value=nullcontext()), \
             patch.object(desktop_app, "own_server_ready", return_value=True), \
             patch.object(desktop_app.subprocess, "Popen") as spawn, \
             patch.object(desktop_app.webbrowser, "open", return_value=True) as browser:
            desktop_app.start_app(Path(folder), 8512)
            spawn.assert_not_called()
            browser.assert_called_once_with("http://127.0.0.1:8512/", new=2)

    def test_unrelated_busy_port_is_rejected_instead_of_opened(self):
        with TemporaryDirectory() as folder, \
             patch.object(desktop_app, "startup_lock", return_value=nullcontext()), \
             patch.object(desktop_app, "own_server_ready", return_value=False), \
             patch.object(desktop_app.socket, "socket") as socket, \
             patch.object(desktop_app.subprocess, "Popen") as spawn, \
             patch.object(desktop_app.webbrowser, "open") as browser:
            socket.return_value.__enter__.return_value.bind.side_effect = OSError("busy")
            with self.assertRaisesRegex(RuntimeError, "Port 8512 is in use"):
                desktop_app.start_app(Path(folder), 8512)
            spawn.assert_not_called()
            browser.assert_not_called()

    def test_failed_server_does_not_leave_a_reusable_instance_marker(self):
        process = Mock(pid=12345)
        process.poll.return_value = 1
        with TemporaryDirectory() as folder, \
             patch.object(desktop_app, "startup_lock", return_value=nullcontext()), \
             patch.object(desktop_app, "own_server_ready", return_value=False), \
             patch.object(desktop_app.socket, "socket"), \
             patch.object(desktop_app, "health_ready", return_value=False), \
             patch.object(desktop_app.subprocess, "Popen", return_value=process):
            with self.assertRaisesRegex(RuntimeError, "Startup log"):
                desktop_app.start_app(Path(folder), 8512, open_browser=False)
            self.assertFalse((Path(folder) / "instance-8512.json").exists())

    def test_foreign_instance_marker_is_not_accepted(self):
        with TemporaryDirectory() as folder:
            marker = Path(folder) / "instance-8512.json"
            marker.write_text(json.dumps({"pid": 12345, "executable": "some-other-program.exe"}))
            self.assertIsNone(desktop_app.saved_process(Path(folder), 8512))


if __name__ == "__main__":
    unittest.main()
