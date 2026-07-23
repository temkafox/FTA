# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PIL import Image
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable,
    VarFileInfo, VarStruct, VSVersionInfo,
)


ROOT = Path(SPECPATH)
RUNTIME = ROOT / "src" / "actpilot"
BUILD_DIR = ROOT / "build"
BUILD_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(ROOT))
from version import __version__

_parts = tuple(int(part) for part in __version__.split("."))[:4]
_version_numbers = _parts + (0,) * (4 - len(_parts))

version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=_version_numbers, prodvers=_version_numbers),
    kids=[
        StringFileInfo([
            StringTable("040904B0", [
                StringStruct("CompanyName", "temkafox"),
                StringStruct("ProductName", "ActPilot"),
                StringStruct("FileDescription", "ActPilot - Path of Exile 1 leveling overlay"),
                StringStruct("FileVersion", __version__),
                StringStruct("ProductVersion", __version__),
                StringStruct("InternalName", "ActPilot-PoE1"),
                StringStruct("OriginalFilename", "ActPilot-PoE1.exe"),
            ]),
        ]),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)

png_icon = RUNTIME / "assets" / "exelogo.png"
ico_icon = BUILD_DIR / "exelogo.ico"
if png_icon.is_file():
    Image.open(png_icon).convert("RGBA").save(
        ico_icon,
        format="ICO",
        sizes=[(256, 256), (64, 64), (32, 32), (16, 16)],
    )


def include_directory(source_root, destination_root):
    result = []
    for source in source_root.rglob("*"):
        if source.is_file():
            relative_parent = source.relative_to(source_root).parent
            destination = Path(destination_root) / relative_parent
            result.append((str(source), str(destination)))
    return result


datas = [
    (str(RUNTIME / "steps.json"), "."),
    (str(RUNTIME / "steps_poe2.json"), "."),
]
datas += include_directory(RUNTIME / "assets", "assets")
datas += include_directory(RUNTIME / "data" / "poe1", "data/poe1")

a = Analysis(
    [str(ROOT / "app.py")],
    pathex=[str(ROOT / "src"), str(RUNTIME)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ActPilot-PoE1",
    icon=str(ico_icon) if ico_icon.is_file() else None,
    version=version_info,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX-сжатие — частый триггер антивирусных эвристик на неподписанных exe
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
