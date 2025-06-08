# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ("./templates/widget.html", "./templates"),
        ("./static/images/Spotify.png", "./static/images"),
        ("./static/index.css", "./static"),
        ("./static/Rainbow.css", "./static"),
        ("./static/socket.io.min.js", "./static"),
        ("./static/vibrant_default.js", "./static"),
        ("./static/vibrant.js", "./static"),
        ("./static/widget.js", "./static"),
    ],
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
        'dns.versioned'
    ],
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
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
