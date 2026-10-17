"""Build with: python -m PyInstaller packaging/eduai.spec --noconfirm."""

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

root = Path(SPECPATH).parent
modules = [path.stem for path in root.glob("eduai_*.py")]
datas = [(str(root / "app.py"), "."), (str(root / "examples"), "examples")]
datas += collect_data_files("streamlit")
datas += collect_data_files("altair")
datas += collect_data_files("pydeck")
datas += copy_metadata("streamlit", recursive=True)
datas += copy_metadata("scikit-learn", recursive=True)
hidden = modules + collect_submodules("streamlit", filter=lambda name: ".testing" not in name and ".hello" not in name)
hidden += ["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.h11_impl",
           "uvicorn.protocols.websockets.websockets_impl", "uvicorn.lifespan.on", "websockets.legacy.server"]

a = Analysis([str(root / "desktop_app.py")], pathex=[str(root)], binaries=[], datas=datas,
             hiddenimports=hidden, hookspath=[], runtime_hooks=[],
             excludes=["pytest", "IPython", "notebook", "jupyter", "matplotlib", "tkinter"], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="EduAI Audit", debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=False,
          disable_windowed_traceback=False)
collect = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="EduAI Audit")
