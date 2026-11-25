# -*- mode: python ; coding: utf-8 -*-
import os
import re
import sys

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable,
    VarFileInfo, VarStruct, VSVersionInfo)

block_cipher = None
root = os.path.abspath(os.getcwd())


def _read_app_version():
    """版本号唯一来源是 quicktext/version.py，此处只读取不重复硬编码。"""
    path = os.path.join(root, 'quicktext', 'version.py')
    with open(path, encoding='utf-8') as fh:
        match = re.search(r'''^__version__\s*=\s*['"]([^'"]+)['"]''', fh.read(), re.M)
    if not match:
        raise SystemExit('QuickText.spec: quicktext/version.py 中找不到 __version__')
    return match.group(1)


APP_VERSION = _read_app_version()


def _ver_num(part):
    try:
        return int(part)
    except ValueError:
        return 0


# Windows 版本资源要求四段数字，不足四位补零
_VERSION_TUPLE = tuple(_ver_num(p) for p in (APP_VERSION.split('.') + ['0', '0', '0', '0'])[:4])

# 直接构造 VSVersionInfo 对象传给 EXE，省掉外置的 version_info.txt
_version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=_VERSION_TUPLE,
        prodvers=_VERSION_TUPLE,
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo([
            StringTable(
                u'080404B0',
                [StringStruct(u'CompanyName', u'QuickText'),
                 StringStruct(u'FileDescription', u'QuickText 文本自动输入器'),
                 StringStruct(u'FileVersion', APP_VERSION),
                 StringStruct(u'InternalName', u'QuickText'),
                 StringStruct(u'LegalCopyright', u'Copyright (C) 2026'),
                 StringStruct(u'OriginalFilename', u'QuickText.exe'),
                 StringStruct(u'ProductName', u'QuickText 文本自动输入器'),
                 StringStruct(u'ProductVersion', APP_VERSION)]),
        ]),
        VarFileInfo([VarStruct(u'Translation', [2052, 1200])]),
    ],
)


a = Analysis(
    [os.path.join(root, 'quicktext', 'main.py')],
    pathex=[root],
    binaries=[],
    datas=[(os.path.join(root, 'quicktext', 'assets'), 'quicktext/assets')],
    hiddenimports=['quicktext', 'quicktext.app', 'quicktext.mainwindow',
                   'quicktext.floating', 'quicktext.picker',
                   'quicktext.phrase_dialog', 'quicktext.settings_dialog',
                   'quicktext.inputsim', 'quicktext.hotkeyedit',
                   'quicktext.appindex', 'quicktext.launcher',
                   'quicktext.store', 'quicktext.theme', 'quicktext.winapi',
                   'quicktext.pinyin', 'quicktext.pinyin_data', 'quicktext.tokens',
                   'quicktext.version',
                   'PySide6.QtNetwork'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
              'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.QtQml',
              'PySide6.Qt3DCore', 'PySide6.QtMultimedia', 'PySide6.QtPdf',
              'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtOpenGL',
              'PySide6.QtOpenGLWidgets', 'PySide6.QtBluetooth', 'PySide6.QtSerialPort',
              'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtXml', 'PySide6.QtSvg',
              'PySide6.QtSvgWidgets', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ---------------------------------------------------------------- 体积裁剪
# PyInstaller 的 PySide6 钩子会把整个 Qt 平台插件与全部语言翻译都收进来：
# 本程序只用 QtWidgets，可安全移除 QtQuick/Qml/PDF/虚拟键盘等动态库、
# 无需的多媒体/图片格式插件，以及除简体中文外的 200 多个翻译文件。
_DROP_NAMES = {
    'opengl32sw.dll',                  # 软件渲染回退，纯 Widgets 程序用不到（20MB）
    'qt6qml.dll', 'qt6qmlmodels.dll', 'qt6qmlmeta.dll', 'qt6qmlworkerscript.dll',
    'qt6quick.dll', 'qt6quickwidgets.dll', 'qt6quickcontrols2.dll',
    'qt6quicktemplates2.dll', 'qt6quickcontrols2impl.dll',
    'qt6opengl.dll', 'qt6pdf.dll', 'qt6virtualkeyboard.dll',
}

_DROP_PREFIXES = (
    'pyside6\\plugins\\platforminputcontexts\\',   # 虚拟键盘（会连带 Qml/Quick）
    'pyside6\\plugins\\tls\\',                     # 本程序不联网
    'pyside6\\plugins\\networkinformation\\',
    'pyside6\\plugins\\generic\\',
    'pyside6\\plugins\\platforms\\qdirect2d',
    'pyside6\\plugins\\platforms\\qminimal',
    'pyside6\\plugins\\platforms\\qoffscreen',
)

# 图片格式插件只保留 ico（窗口图标）与 svg（QSS 图标）
_KEEP_IMAGEFORMATS = {'qico.dll', 'qsvg.dll'}

_KEEP_TRANSLATIONS = {'qtbase_zh_cn.qm'}


def _keep(entry):
    name = (entry[0] or '').replace('/', '\\').lower()
    base = name.rsplit('\\', 1)[-1]
    if base in _DROP_NAMES:
        return False
    for prefix in _DROP_PREFIXES:
        if name.startswith(prefix):
            return False
    if '\\imageformats\\' in name and base not in _KEEP_IMAGEFORMATS:
        return False
    if '\\translations\\' in name and base not in _KEEP_TRANSLATIONS:
        return False
    return True


a.binaries = [b for b in a.binaries if _keep(b)]
a.datas = [d for d in a.datas if _keep(d)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='QuickText',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(root, 'quicktext', 'assets', 'app.ico'),
    version=_version_info,
)
