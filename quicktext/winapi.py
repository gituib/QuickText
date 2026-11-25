"""公共工具：配置目录、文案、热键文本化。"""
import os
import sys

APP_NAME = "QuickText"
APP_TITLE = "QuickText 文本自动输入器"
ORG_NAME = "QuickText"

_win = sys.platform == "win32"
if _win:
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)

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
    _MSG = _GUITHREADINFO = _POINT = _LASTINPUTINFO = None


def config_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, ORG_NAME, "AutoTyper")
    os.makedirs(path, exist_ok=True)
    return path


def data_file() -> str:
    return os.path.join(config_dir(), "phrases.json")


def app_icon_path() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(base, "assets", "app.ico")
    return p if os.path.exists(p) else ""


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
