"""输入模拟：全局热键、光标定位、文本输入、剪贴板。"""
import ctypes
import time

from . import winapi as W

user32 = W._user32

ULONG_PTR = ctypes.c_size_t
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_EXTENDEDKEY = 0x0001
INPUT_KEYBOARD = 1
CF_UNICODETEXT = 13
CF_TEXT = 1
CF_OEMTEXT = 7
CF_LOCALE = 16
_TEXT_FORMATS = {CF_TEXT, CF_OEMTEXT, CF_UNICODETEXT, CF_LOCALE}
PASTE_THRESHOLD = 400  # 自动模式下超过该长度改用剪贴板粘贴
GMEM_MOVEABLE = 0x0002
SW_RESTORE = 9
SMTO_ABORTIFHUNG = 0x0002

_EXTENDED_VKS = {0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E,
                 0x5B, 0x5C, 0x6F, 0x90, 0xA3, 0xA5}


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.c_size_t)]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.c_size_t)]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_ushort),
                ("wParamH", ctypes.c_ushort)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT), ("hi", _HARDWAREINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("u", _INPUTUNION)]

    def __init__(self):
        super().__init__()
        self.type = INPUT_KEYBOARD
        self.u.ki.wVk = 0
        self.u.ki.wScan = 0
        self.u.ki.dwFlags = 0
        self.u.ki.time = 0
        self.u.ki.dwExtraInfo = 0


user32.SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(_INPUT), ctypes.c_int]
user32.SendInput.restype = ctypes.c_uint
user32.RegisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
user32.RegisterHotKey.restype = ctypes.c_bool
user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.UnregisterHotKey.restype = ctypes.c_bool
user32.GetGUIThreadInfo.argtypes = [ctypes.c_ulong, ctypes.POINTER(W._GUITHREADINFO)]
user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
user32.GetForegroundWindow.restype = ctypes.c_void_p
user32.GetCursorPos.argtypes = [ctypes.POINTER(W._POINT)]
user32.ClientToScreen.argtypes = [ctypes.c_void_p, ctypes.POINTER(W._POINT)]
user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.IsWindow.argtypes = [ctypes.c_void_p]
user32.GetForegroundWindow.argtypes = []

user32.BringWindowToTop.argtypes = [ctypes.c_void_p]
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
user32.AttachThreadInput.argtypes = [ctypes.c_ulong, ctypes.c_ulong, ctypes.c_bool]
user32.SetFocus.argtypes = [ctypes.c_void_p]
user32.SetActiveWindow.argtypes = [ctypes.c_void_p]
user32.IsIconic.argtypes = [ctypes.c_void_p]
user32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
# 剪贴板：HGLOBAL 在 x64 是 64 位，必须显式声明原型，否则按 int 传递会溢出
user32.OpenClipboard.argtypes = [ctypes.c_void_p]
user32.OpenClipboard.restype = ctypes.c_bool
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = ctypes.c_bool
user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
user32.SetClipboardData.restype = ctypes.c_void_p
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = ctypes.c_bool
user32.GetClipboardData.argtypes = [ctypes.c_uint]
user32.GetClipboardData.restype = ctypes.c_void_p
user32.EnumClipboardFormats.argtypes = [ctypes.c_uint]
user32.EnumClipboardFormats.restype = ctypes.c_uint

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32 = _kernel32
kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
kernel32.GlobalFree.restype = ctypes.c_void_p
kernel32.GetCurrentThreadId.restype = ctypes.c_ulong
kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
kernel32.OpenProcess.restype = ctypes.c_void_p
kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
kernel32.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                                                ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]

# 驱动 SendInput 使用的隐藏窗口（无实际用途，仅需有效句柄以便键盘状态判断）
def _last_input_tick() -> int:
    info = W._LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    user32.GetLastInputInfo(ctypes.byref(info))
    return info.dwTime


def _tick_count() -> int:
    return kernel32.GetTickCount() & 0xFFFFFFFF


_last_inject = 0.0


def clipboard_set_text(text: str) -> bool:
    if not user32.OpenClipboard(None):
        return False
    try:
        if not user32.EmptyClipboard():
            return False
        data = ctypes.create_unicode_buffer(text)
        size = ctypes.sizeof(data)
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
        if not handle:
            return False
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            kernel32.GlobalFree(handle)
            return False
        ctypes.memmove(ptr, ctypes.addressof(data), size)
        kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            kernel32.GlobalFree(handle)
            return False
        return True
    finally:
        user32.CloseClipboard()


def clipboard_text():
    """返回剪贴板中的纯文本；无法读取时返回 None，空剪贴板返回空串。"""
    if not user32.OpenClipboard(None):
        return None
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def clipboard_has_rich_content() -> bool:
    """剪贴板是否包含图片、文件等非纯文本内容。"""
    if not user32.OpenClipboard(None):
        return False
    try:
        fmt = 0
        while True:
            fmt = user32.EnumClipboardFormats(fmt)
            if not fmt:
                return False
            if fmt not in _TEXT_FORMATS:
                return True
    finally:
        user32.CloseClipboard()


def _send_unicode(text: str) -> int:
    """以 Unicode 扫描码的方式逐字符输入，不依赖输入法状态。"""
    if not text:
        return 0
    size = ctypes.sizeof(_INPUT)
    sent = 0
    for ch in text:
        code = ord(ch)
        arr = (_INPUT * 2)()
        arr[0].type = INPUT_KEYBOARD
        arr[0].u.ki.wVk = 0
        arr[0].u.ki.wScan = code
        arr[0].u.ki.dwFlags = KEYEVENTF_UNICODE
        arr[1].type = INPUT_KEYBOARD
        arr[1].u.ki.wVk = 0
        arr[1].u.ki.wScan = code
        arr[1].u.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
        if user32.SendInput(2, arr, size) == 2:
            sent += 1
        time.sleep(0.001)
    return sent


def _send_vk(vk: int, down: bool):
    arr = (_INPUT * 1)()
    arr[0].type = INPUT_KEYBOARD
    arr[0].u.ki.wVk = vk
    arr[0].u.ki.wScan = 0
    arr[0].u.ki.dwFlags = 0 if down else KEYEVENTF_KEYUP
    user32.SendInput(1, arr, ctypes.sizeof(_INPUT))


def _pump(ms: int):
    """让热键窗口处理注册热键，避免阻塞消息循环时的按键丢失。"""
    end = time.time() + ms / 1000.0
    while time.time() < end:
        time.sleep(0.005)


class Typer:
    def __init__(self, mods: int):
        self.mods = mods & (W.MOD_ALT | W.MOD_CONTROL | W.MOD_SHIFT | W.MOD_WIN)

    def release_modifiers(self):
        for vk, mask in ((0x11, W.MOD_CONTROL), (0x12, W.MOD_ALT),
                         (0x10, W.MOD_SHIFT), (0x5B, W.MOD_WIN), (0x5C, W.MOD_WIN)):
            if self.mods & mask:
                _send_vk(vk, False)
        if self.mods:
            time.sleep(0.02)

    def type_text(self, text: str, paste: bool = False) -> int:
        """输入整段文本；paste=True 时走剪贴板粘贴并在结束后还原剪贴板。"""
        self.release_modifiers()
        if paste:
            return self.paste_text(text)
        return _send_unicode(text)

    def paste_text(self, text: str) -> int:
        previous = clipboard_text()
        if not clipboard_set_text(text):
            return _send_unicode(text)
        try:
            _send_vk(0x11, True)
            _send_vk(0x56, True)
            _send_vk(0x56, False)
            _send_vk(0x11, False)
            time.sleep(0.3)
        finally:
            if previous is not None:
                clipboard_set_text(previous)
        return len(text)

    def type_linebreak(self):
        self.release_modifiers()
        _send_vk(0x0D, True)
        _send_vk(0x0D, False)

    def run_commands(self, commands: list):
        """commands: [(mods, vk)] 依次执行，非文本命令（如粘贴）用剪贴板实现。"""
        for mods, vk in commands:
            self.release_modifiers()
            if vk == 0x56 and (mods & W.MOD_CONTROL) and not (mods & ~(W.MOD_CONTROL | W.MOD_SHIFT | W.MOD_ALT)):
                _send_vk(0x11, True)
                _send_vk(0x56, True)
                _send_vk(0x56, False)
                _send_vk(0x11, False)
            else:
                pressed = []
                if mods & W.MOD_CONTROL:
                    pressed.append(0x11)
                if mods & W.MOD_ALT:
                    pressed.append(0x12)
                if mods & W.MOD_SHIFT:
                    pressed.append(0x10)
                if mods & W.MOD_WIN:
                    pressed.append(0x5B)
                for v in pressed:
                    _send_vk(v, True)
                _send_vk(vk, True)
                _send_vk(vk, False)
                for v in reversed(pressed):
                    _send_vk(v, False)
            _pump(15)


def foreground_window() -> int:
    return int(user32.GetForegroundWindow() or 0)


_SHELL_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
                  "DV2ControlHost", "Windows.UI.Core.CoreWindow", "MultitaskingViewFrame",
                  "TaskSwitcherWnd", "NotifyIconOverflowWindow", "XamlExplorerHostIslandWindow"}

_SHELL_NAMES = {"workbuddy.exe", "explorer.exe", "trae cn.exe", "trae.exe", "windowsterminal.exe"}


def _is_tool_host(hwnd: int, pid: int = 0) -> bool:
    """判断窗口是否属于宿主/终端类程序（这些程序会抢占前台，不应作为输入目标）。"""
    if not pid:
        pid = window_pid(hwnd)
    if not pid:
        return False
    path = ctypes.create_unicode_buffer(1024)
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    try:
        size = ctypes.c_ulong(1024)
        if kernel32.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
            name = path.value.rsplit("\\", 1)[-1].lower()
            return name in _SHELL_NAMES
        return False
    finally:
        kernel32.CloseHandle(handle)


# 前台窗口判定缓存：轮询定时器每 300ms 触发一次，窗口未变化时省去开进程等系统调用
_fg_cache = (0, 0, False, False)   # hwnd, pid, is_shell, is_host


def last_tracked_foreign_window(exclude_pids=()) -> int:
    """返回最近一次属于其他普通程序的前台窗口（用于选择器/面板关闭后回填文本）。"""
    global _fg_cache
    hwnd = foreground_window()
    if not hwnd:
        return 0
    pid = window_pid(hwnd)
    if pid in exclude_pids:
        return 0
    cached_hwnd, cached_pid, is_shell, is_host = _fg_cache
    if hwnd != cached_hwnd or pid != cached_pid:
        cls = ctypes.create_unicode_buffer(128)
        user32.GetClassNameW(hwnd, cls, 128)
        is_shell = cls.value in _SHELL_CLASSES
        is_host = _is_tool_host(hwnd, pid)
        _fg_cache = (hwnd, pid, is_shell, is_host)
    if is_shell or is_host:
        return 0
    return hwnd


def window_pid(hwnd: int) -> int:
    if not hwnd:
        return 0
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), ctypes.byref(pid))
    return pid.value


def caret_screen_rect() -> tuple:
    """返回当前前台线程光标位置（屏幕坐标），不可用时返回鼠标位置。"""
    hwnd = foreground_window()
    pt = W._POINT()
    if hwnd:
        tid = user32.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), None)
        gti = W._GUITHREADINFO()
        gti.cbSize = ctypes.sizeof(gti)
        if user32.GetGUIThreadInfo(tid, ctypes.byref(gti)) and gti.hwndCaret:
            pt.x = gti.rcCaret_left
            pt.y = gti.rcCaret_top
            user32.ClientToScreen(ctypes.c_void_p(gti.hwndCaret), ctypes.byref(pt))
            return pt.x, pt.y, True
    if user32.GetCursorPos(ctypes.byref(pt)):
        return pt.x, pt.y, False
    return 0, 0, False


def restore_window(hwnd: int):
    """把目标窗口切到前台（跳过前台锁定限制），用于选择器/面板的“输入”动作。"""
    if not hwnd or not user32.IsWindow(ctypes.c_void_p(hwnd)):
        return False
    h = ctypes.c_void_p(hwnd)
    fg = user32.GetForegroundWindow()
    current_tid = _kernel32.GetCurrentThreadId()
    fg_tid = user32.GetWindowThreadProcessId(ctypes.c_void_p(fg), None) if fg else 0
    target_tid = user32.GetWindowThreadProcessId(h, None)
    attached = []
    for tid in {fg_tid, target_tid}:
        if tid and tid != current_tid:
            if user32.AttachThreadInput(current_tid, tid, True):
                attached.append(tid)
    try:
        if user32.IsIconic(h):
            user32.ShowWindow(h, SW_RESTORE)
        user32.BringWindowToTop(h)
        user32.SetForegroundWindow(h)
        user32.SetActiveWindow(h)
    finally:
        for tid in attached:
            user32.AttachThreadInput(current_tid, tid, False)
    return user32.GetForegroundWindow() == hwnd
