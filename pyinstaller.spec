# PyInstaller spec for llama-gui
# Build with: pyinstaller pyinstaller.spec

block_cipher = None

a = Analysis(
    ["src/llama_app/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        ("src/llama_app/resources/icon.png", "llama_app/resources"),
    ],
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "psutil",
        "pynvml",
        "httpx",
        "pyqtgraph",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="llama-gui",
    icon="src/llama_app/resources/icon.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
