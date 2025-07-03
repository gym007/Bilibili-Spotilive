# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

# 自动收集 static/queue_widget 和 static/nowplaying_widget 下的所有文件
datas = []
for widget in ('queue_widget', 'nowplaying_widget'):
    src_dir = os.path.join('static', widget)
    for root, _, files in os.walk(src_dir):
        for fname in files:
            src_path = os.path.join(root, fname)
            # dest_dir 是 exe 内的相同路径
            dest_dir = root  # root 已经是相对路径 like 'static/queue_widget/...'
            datas.append((src_path, dest_dir))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'gevent',
        'gevent-websocket',
        'gevent.ssl',
        'gevent.builtins',
        'threading',
        'engineio.async_drivers.threading',
        'dns.rdtypes.dnskeybase',
        'dns.namedict',
        'dns.tsigkeyring',
        'dns.versioned',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=True,
)
