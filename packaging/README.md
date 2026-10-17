# Windows desktop distribution

The installer bundles the Python runtime, Streamlit, audit modules, dependencies,
and the two artificial sample CSVs. It excludes research notebooks, real student
exports, the repository's virtual environment, Git credentials, and user files.

## Build on Windows x64

From the repository root, with the application dependencies already installed:

```powershell
.\.venv\Scripts\python.exe -m pip install -r packaging/requirements-build.txt
.\packaging\build_windows.ps1 -Compiler 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
```

The compiler may also be installed for the current user in another directory;
pass that full path. Obtain it from the official Inno Setup download page.
The output is `dist/EduAI-Audit-Setup-0.1.0.exe` plus a SHA256 file. The adjacent
`dist/EduAI Audit` directory is the portable application: distribute the entire
directory together, not just its executable. `build-info.json` records source
commit, Python and exact package versions. Third-party license notices are
included in `THIRD_PARTY_NOTICES.txt`.

The installer installs for the current user, creates Start menu / optional desktop
shortcuts, and registers an uninstaller. Administrator rights are not required.
The application opens its local browser interface at `127.0.0.1:8502`; the source
checkout continues to use port 8501. Both run locally and can coexist.

Closing the browser tab leaves the local server available for the next launch.
Use **Stop EduAI Audit** in the Start menu to stop it. Uninstall also stops the
installed server. Logs and startup state are in `%LOCALAPPDATA%/EduAI-Audit` so
the application does not need write access to its installed files. CSVs are not
copied there by the launcher; reports are downloaded through the browser.

## Smoke checks for every distribution

1. Launch the executable from a different working directory with Python removed
   from PATH: `"EduAI Audit.exe" --no-browser --port 8512`.
2. Verify local health and that the loaded Python DLL comes from the bundle.
3. Run both one-click examples in a browser; check the known counts, language
   switching, settings import, HTML/ZIP downloads and return to an uploaded CSV.
4. Launch again; confirm the same server PID is reused. Test `--stop --port 8512`.
5. Install into a separate test directory, launch the installed executable, then
   uninstall. Do not overwrite a user's existing installation for a smoke check.

This first distribution is an unsigned preview for Windows 10/11 x64. It is not
code-signed or automatically updated. A successful local smoke check does not
replace testing on a separate Windows computer without a Python installation.

## Publish a preview on GitHub

Updating `packaging/release-request.json` on `main` starts the Windows release
workflow. It installs the pinned runtime and build dependencies, runs the tests,
builds the installer, and checks the bundled examples and downloads in Chrome.
Only after these checks pass does a separate job publish the installer, checksum,
and build information as a GitHub prerelease. The publish job alone has repository
contents write permission. Add matching release notes before requesting a new
version. Existing release assets are not overwritten automatically.
