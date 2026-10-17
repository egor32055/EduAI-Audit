"""Record exact bundled versions and their license notices, without user data."""

import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
destination = root / "dist" / "EduAI Audit"
excluded = {"pip", "pyinstaller", "pyinstaller-hooks-contrib", "altgraph", "pefile", "pywin32-ctypes", "setuptools"}
packages = sorted((d for d in metadata.distributions() if d.metadata["Name"].lower() not in excluded), key=lambda d: d.metadata["Name"].lower())
info = {"application": "EduAI-Audit", "version": sys.argv[1], "python": platform.python_version(),
        "architecture": platform.machine(), "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "packages": {d.metadata["Name"]: d.version for d in packages}}
(destination / "build-info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
notices = ["EduAI-Audit bundles the following third-party packages. Their license notices follow.\n"]
for distribution in packages:
    notices.append(f"\n{'=' * 72}\n{distribution.metadata['Name']} {distribution.version}\n")
    for file in distribution.files or []:
        if ".dist-info/" in str(file).replace("\\", "/") and any(word in str(file).lower() for word in ("license", "copying", "notice")):
            path = Path(distribution.locate_file(file))
            if path.is_file():
                notices.append(path.read_text(encoding="utf-8", errors="replace"))
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.exists():
    notices.extend(["\nPython license\n", python_license.read_text(encoding="utf-8")])
(destination / "THIRD_PARTY_NOTICES.txt").write_text("\n".join(notices), encoding="utf-8")
