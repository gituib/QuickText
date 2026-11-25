"""公共工具：配置目录、文案、热键文本化。"""
import os
import shutil
import sys

APP_NAME = "QuickText"
APP_TITLE = "QuickText 文本自动输入器"
ORG_NAME = "QuickText"

_win = sys.platform == "win32"
if _win:
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_char))]

    _crypt32.CryptProtectData.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.c_void_p,
                                          ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                                          ctypes.c_void_p]
    _crypt32.CryptProtectData.restype = wintypes.BOOL
    _crypt32.CryptUnprotectData.argtypes = _crypt32.CryptProtectData.argtypes
    _crypt32.CryptUnprotectData.restype = wintypes.BOOL
    _kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    _kernel32.GlobalFree.restype = ctypes.c_void_p

    class _MSG(ctypes.Structure):
        _fields_ = [("hWnd", wintypes.HWND), ("message", wintypes.UINT),
                    ("wParam", wintypes.WPARAM), ("lParam", wintypes.LPARAM),
                    ("time", wintypes.DWORD), ("pt_x", wintypes.LONG),
                    ("pt_y", wintypes.LONG)]

    class _GUITHREADINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD),
                    ("hwndActive", wintypes.HWND), ("hwndFocus", wintypes.HWND),
                    ("hwndCapture", wintypes.HWND), ("hwndMenuOwner", wintypes.HWND),
                    ("hwndMoveSize", wintypes.HWND), ("hwndCaret", wintypes.HWND),
                    ("rcCaret_left", wintypes.LONG), ("rcCaret_top", wintypes.LONG),
                    ("rcCaret_right", wintypes.LONG), ("rcCaret_bottom", wintypes.LONG)]

    class _POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    class _LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]
else:
    _MSG = _GUITHREADINFO = _POINT = _LASTINPUTINFO = _DATA_BLOB = None


DATA_SUBDIR = "data"
LEGACY_FILES = ("phrases.json", "phrases.json.bak", "apps.json")


def _user_data_dir() -> str:
    """旧版数据位置，也是安装目录不可写时的回退位置。"""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, ORG_NAME, "AutoTyper")


def _writable(path: str) -> bool:
    probe = os.path.join(path, ".write-test")
    try:
        with open(probe, "w", encoding="utf-8"):
            pass
        os.remove(probe)
        return True
    except OSError:
        return False


def _install_data_dir():
    """打包运行时数据随程序放在安装目录的 data 子目录下。

    开发模式没有 exe 同级目录；选择「为所有用户安装」时程序落在 Program Files，
    普通权限写不进去。这两种情况返回 None，由调用方回退到用户目录。
    """
    if not getattr(sys, "frozen", False):
        return None
    path = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), DATA_SUBDIR)
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        return None
    return path if _writable(path) else None


def _import_legacy(new_dir: str) -> None:
    """首次启动时把旧版存放在 %APPDATA% 的数据复制过来，原文件保留不动。"""
    old_dir = _user_data_dir()
    if not os.path.isdir(old_dir):
        return
    for name in LEGACY_FILES:
        src = os.path.join(old_dir, name)
        dst = os.path.join(new_dir, name)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
            except OSError:
                pass


def config_dir() -> str:
    path = _install_data_dir()
    if path is None:
        path = _user_data_dir()
        os.makedirs(path, exist_ok=True)
    else:
        _import_legacy(path)
    return path


def data_file() -> str:
    return os.path.join(config_dir(), "phrases.json")


def app_icon_path() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(base, "assets", "app.ico")
    return p if os.path.exists(p) else ""


# ---------------------------------------------------------------------------
# DPAPI 数据加密：密文与当前 Windows 用户账户绑定，不需要管理密钥
# ---------------------------------------------------------------------------
_CRYPTPROTECT_UI_FORBIDDEN = 0x01


def encryption_available() -> bool:
    return _win


def protect(data: bytes) -> bytes:
    if not _win:
        raise RuntimeError("当前系统不支持 DPAPI 加密。")
    raw = bytes(data)
    # 输入缓冲区必须由局部变量持有，否则调用期间可能被回收
    buf = ctypes.create_string_buffer(raw, len(raw))
    blob_in = _DATA_BLOB(len(raw), buf)
    blob_out = _DATA_BLOB()
    if not _crypt32.CryptProtectData(ctypes.byref(blob_in), None, None, None, None,
                                     _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        _kernel32.GlobalFree(blob_out.pbData)


def unprotect(data: bytes) -> bytes:
    if not _win:
        raise RuntimeError("当前系统不支持 DPAPI 解密。")
    raw = bytes(data)
    buf = ctypes.create_string_buffer(raw, len(raw))
    blob_in = _DATA_BLOB(len(raw), buf)
    blob_out = _DATA_BLOB()
    if not _crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None,
                                       _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        _kernel32.GlobalFree(blob_out.pbData)


# ---------------------------------------------------------------------------
# 热键文本化
# ---------------------------------------------------------------------------
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

_VK_NAMES = {
    0x08: "Backspace", 0x09: "Tab", 0x0D: "Enter", 0x13: "Pause",
    0x14: "Caps Lock", 0x1B: "Esc", 0x20: "Space", 0x21: "Page Up",
    0x22: "Page Down", 0x23: "End", 0x24: "Home", 0x25: "Left",
    0x26: "Up", 0x27: "Right", 0x28: "Down", 0x2C: "Print Screen",
    0x2D: "Insert", 0x2E: "Delete", 0x5B: "Win", 0x5C: "Win",
    0x90: "Num Lock", 0x91: "Scroll Lock",
    0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-", 0xBE: ".", 0xBF: "/",
    0xC0: "`", 0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'",
}
for _i in range(1, 25):
    _VK_NAMES[0x70 + _i - 1] = "F%d" % _i
for _i in range(0x30, 0x3A):
    _VK_NAMES[_i] = chr(_i)
for _i in range(0x41, 0x5B):
    _VK_NAMES[_i] = chr(_i)
for _i in range(0x60, 0x6A):
    _VK_NAMES[_i] = "Num %d" % (_i - 0x60)
_VK_NAMES[0x6A] = "Num *"
_VK_NAMES[0x6B] = "Num +"
_VK_NAMES[0x6D] = "Num -"
_VK_NAMES[0x6E] = "Num ."
_VK_NAMES[0x6F] = "Num /"


def vk_name(vk: int) -> str:
    if vk in _VK_NAMES:
        return _VK_NAMES[vk]
    if 0x41 <= vk <= 0x5A:
        return chr(vk)
    return "VK 0x%02X" % vk


def hotkey_text(mods: int, vk: int) -> str:
    if not vk:
        return ""
    parts = []
    if mods & MOD_WIN:
        parts.append("Win")
    if mods & MOD_CONTROL:
        parts.append("Ctrl")
    if mods & MOD_ALT:
        parts.append("Alt")
    if mods & MOD_SHIFT:
        parts.append("Shift")
    parts.append(vk_name(vk))
    return "+".join(parts)


def modifiers_of(mods: int) -> int:
    return mods & (MOD_ALT | MOD_CONTROL | MOD_SHIFT | MOD_WIN)
