# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

BLOCK_CIPHER_HOOKS = ["Crypto", "Cryptodome"]

# Collect all litellm hidden imports and data files
litellm_imports = collect_submodules('litellm')
litellm_datas = collect_data_files('litellm', include_py_files=False)

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('rules', 'rules'),
        ('prompts', 'prompts'),
        ('alembic', 'alembic'),
        ('alembic.ini', '.'),
    ] + litellm_datas,
    hiddenimports=[
        'sqlalchemy',
        'sqlalchemy.sql',
        'sqlalchemy.orm',
        'alembic',
        'alembic.config',
        'alembic.script',
        'alembic.runtime',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'httpx',
        'httpx._transports',
        'yaml',
        'yaml.parser',
        'yaml.scanner',
        'jinja2',
        'jinja2.ext',
        'multipart',
        'tiktoken_ext',
        'tiktoken_ext.openai_public',
    ] + litellm_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'PIL',
        'cv2',
        'numpy',
        'tensorflow',
        'torch',
        'notebook',
        'jupyter',
        'distutils',
        'setuptools',
        'pip',
    ],
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
    name='fluxdesk-ai',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
