"""热键编辑框：按下组合键即记录。"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLineEdit

from . import winapi as W

# 不适合单独作为热键主键的按键
_FORBID_KEYS = {Qt.Key_Tab, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space, Qt.Key_Backspace}
# Win32 虚拟键码：Ctrl / Alt / Shift / Win / CapsLock / NumLock / ScrollLock / Insert / Delete
_FORBID = {0x10, 0x11, 0x12, 0x5B, 0x5C, 0x14, 0x90, 0x91, 0x2D, 0x2E}


class HotkeyEdit(QLineEdit):
    hotkeyChanged = Signal(int, int)

    def __init__(self, mods=0, vk=0, allow_empty=True, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self._allow_empty = allow_empty
        self._idle_placeholder = "按下快捷键（可留空）" if allow_empty else "按下快捷键"
        self.setPlaceholderText(self._idle_placeholder)
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self._mods = 0
        self._vk = 0
        self._pending_mods = 0
        self._last_mods = 0
        self._last_vk = 0
        self.set_hotkey(mods, vk)

    def set_hotkey(self, mods, vk):
        self._mods = W.modifiers_of(mods)
        self._vk = int(vk or 0)
        self.setText(W.hotkey_text(self._mods, self._vk))
        self.hotkeyChanged.emit(self._mods, self._vk)

    def hotkey(self):
        return self._mods, self._vk

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.text():
            self._last_mods, self._last_vk = self._mods, self._vk
        self._mods = 0
        self._vk = 0
        self._pending_mods = 0
        self.clear()
        self.setPlaceholderText("请按快捷键…")
        self.grabKeyboard()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.releaseKeyboard()
        self._pending_mods = 0
        if not self.text() and not self._allow_empty:
            self.set_hotkey(self._last_mods, self._last_vk)
        self.setPlaceholderText(self._idle_placeholder)

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            self._pending_mods |= {Qt.Key_Control: W.MOD_CONTROL, Qt.Key_Shift: W.MOD_SHIFT,
                                   Qt.Key_Alt: W.MOD_ALT, Qt.Key_Meta: W.MOD_WIN}[key]
            return
        if key == Qt.Key_Escape:
            self.releaseKeyboard()
            event.ignore()
            return
        if key == Qt.Key_Backspace or key == Qt.Key_Delete:
            self.set_hotkey(0, 0)
            self.releaseKeyboard()
            return
        vk = native_vk(event)
        if (key in _FORBID_KEYS and self._pending_mods == 0) or vk in _FORBID:
            return
        self.set_hotkey(self._pending_mods, vk)
        self.releaseKeyboard()


def native_vk(event) -> int:
    """把 Qt 按键转换成 Win32 虚拟键码。"""
    vk = event.nativeVirtualKey() if hasattr(event, "nativeVirtualKey") else 0
    if vk:
        return int(vk)
    key = event.key()
    if Qt.Key_F1 <= key <= Qt.Key_F24:
        return 0x70 + (key - Qt.Key_F1)
    if Qt.Key_A <= key <= Qt.Key_Z:
        return 0x41 + (key - Qt.Key_A)
    if Qt.Key_0 <= key <= Qt.Key_9:
        return 0x30 + (key - Qt.Key_0)
    return 0
