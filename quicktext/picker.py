"""选择器：在文本光标旁弹出，按一行直接输入。"""
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFontMetrics, QGuiApplication
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QVBoxLayout)

from . import theme, winapi as W
from .store import mask_text

# palette 不可用时的兜底配色（浅色·湖青）
_FALLBACK_PALETTE = {
    "primary": "#0D9488", "accent": "#0D9488", "surface": "#FFFFFF",
    "bg": "#F8FAFC", "text": "#0F172A", "muted_text": "#64748B", "border": "#E2E8F0",
}


def _palette(index: int) -> dict:
    try:
        fn = getattr(theme, "palette", None)
        if fn is not None:
            c = fn(index)
            if isinstance(c, dict) and "surface" in c and "border" in c:
                return c
    except Exception:
        pass
    return dict(_FALLBACK_PALETTE)


class PickerDialog(QDialog):
    picked = Signal(str)

    def __init__(self, store, theme_index=1, anchor=None, parent=None):
        super().__init__(parent)
        self.store = store
        self._theme_index = theme_index
        self.setObjectName("picker")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)
        self.setWindowTitle("选择短语")
        # 先铺 dialog 通用样式，再用 picker 覆盖（QDialog#picker 需要透明背景才能露出圆角卡片）
        self.setStyleSheet(theme.build_stylesheet(theme_index, "dialog")
                           + theme.build_stylesheet(theme_index, "picker")
                           + theme.card_stylesheet(theme_index))
        self.resize(460, 440)
        self._build_ui()
        self._populate()
        self._anchor = anchor
        self._closing = False
        self._shown_once = False

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 圆角卡片容器（样式兜底，theme 有覆盖时以 theme 为准）
        self._card = QFrame()
        self._card.setObjectName("pickerCard")
        root.addWidget(self._card)
        c = _palette(self._theme_index)
        if "pickerCard" not in self.styleSheet():
            self._card.setStyleSheet(
                "QFrame#pickerCard { background: %s; border: 1px solid %s; border-radius: 12px; }"
                % (c.get("surface", "#FFFFFF"), c.get("border", "#E2E8F0")))

        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(8)
        title = QLabel("插入短语")
        title.setObjectName("pickerTitle")
        head.addWidget(title)
        head.addStretch(1)
        hint = QLabel("Enter 插入 · Esc 关闭")
        hint.setObjectName("pickerHint")
        head.addWidget(hint)
        layout.addLayout(head)

        self.search = QLineEdit()
        self.search.setObjectName("pickerSearch")
        self.search.setPlaceholderText("搜索名称、缩写、拼音首字母或内容")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(38)
        self.search.textChanged.connect(self._populate)
        layout.addWidget(self.search)
        self.list = QListWidget()
        self.list.setObjectName("pickerList")
        self.list.setIconSize(QSize(0, 0))
        self.list.itemActivated.connect(self._on_item)
        self.list.itemClicked.connect(self._on_item)
        layout.addWidget(self.list, 1)
        foot = QLabel("点击一行即可插入到当前光标位置")
        foot.setObjectName("hint")
        foot.setWordWrap(True)
        layout.addWidget(foot)

    def _populate(self):
        keyword = self.search.text()
        items = [p for p in self.store.search(keyword) if p["enabled"]]
        recent_first = bool(self.store.settings.get("pickerRecentFirst", True))
        if recent_first:
            items.sort(key=lambda p: -int(p.get("lastUsed") or 0))
        hide_text = bool(self.store.settings.get("hidePhraseText", True))
        self.list.clear()
        # 行宽预算：优先给快捷键留出空间，主体文本按剩余宽度省略，避免出现“Ctrl+Al…”
        fm = QFontMetrics(self.list.font())
        vw = self.list.viewport().width()
        if vw < 120:  # 尚未布局完成时用窗口宽度估算
            vw = self.width() - 56
        total_w = max(180, vw - 28)
        for phrase in items:
            if hide_text:
                text = mask_text(phrase["text"])
            else:
                text = phrase["text"].replace("\r\n", " / ").replace("\n", " / ")
            label = phrase["name"] or text
            if phrase["name"]:
                label = "%s    %s" % (phrase["name"], text)
            group = phrase.get("group") or ""
            if group:
                label = "%s   ·   %s" % (group, label)
            hotkey = self.hotkey_text(phrase)
            if hotkey:
                hk_w = fm.horizontalAdvance(hotkey) + 16
                label = "%s    %s" % (fm.elidedText(label, Qt.ElideRight, max(80, total_w - hk_w)),
                                      hotkey)
            else:
                label = fm.elidedText(label, Qt.ElideRight, total_w)
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, phrase["id"])
            item.setToolTip("内容已隐藏" if hide_text else phrase["text"])
            item.setSizeHint(QSize(0, 40))
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)
        else:
            # 无匹配：插入一条不可选提示
            item = QListWidgetItem("没有匹配的短语")
            item.setFlags(Qt.NoItemFlags)
            item.setTextAlignment(Qt.AlignCenter)
            item.setSizeHint(QSize(0, 40))
            self.list.addItem(item)
        self.list.setFocus()

    @staticmethod
    def hotkey_text(phrase):
        """把快捷键转换成可读文本，例如 Ctrl+Alt+A（行尾徽标）。"""
        return W.hotkey_text(int(phrase.get("hotkeyMods") or 0), int(phrase.get("hotkeyVk") or 0))

    def _on_item(self, item):
        if item is None:
            return
        phrase_id = item.data(Qt.UserRole)
        if not phrase_id:
            return
        for phrase in self.store.phrases:
            if phrase["id"] == phrase_id:
                self.picked.emit(phrase["text"])
                self.store.touch(phrase_id)
                self.close()
                return

    def showEvent(self, event):
        super().showEvent(event)
        if not self._shown_once:
            self._shown_once = True
            # 首次显示后控件才拿到真实宽度与样式字体，重新排版一次避免行尾被截断
            self._populate()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._on_item(self.list.currentItem())
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        # 列表为空时鼠标滚轮也能滚动
        self.list.setFocus()
        super().wheelEvent(event)

    def show_at(self):
        screen = QGuiApplication.primaryScreen()
        if self._anchor:
            x, y, valid = self._anchor
            # anchor 来自 Win32（caret_screen_rect），单位是物理像素：不能直接当
            # Qt 逻辑坐标用。先按各屏 devicePixelRatio 把 logicalGeometry 还原成
            # 物理几何做包含测试，命中后再把 anchor 除以该屏 devicePixelRatio 换算
            # 成逻辑坐标，最后 clamp 到该屏 availableGeometry（逻辑坐标）。
            for scr in QGuiApplication.screens():
                dpr = scr.devicePixelRatio()
                geo = scr.geometry()
                left, top = geo.x() * dpr, geo.y() * dpr
                if left <= x < left + geo.width() * dpr and top <= y < top + geo.height() * dpr:
                    screen = scr
                    x, y = x / dpr, y / dpr
                    break
        else:
            x, y, valid = 0, 0, False
        geo = screen.availableGeometry()
        x = max(geo.left() + 4, min(int(x), geo.right() - self.width() - 4))
        y = max(geo.top() + 4, min(int(y), geo.bottom() - self.height() - 4))
        self.move(int(x), int(y))
        self.show()
        self.raise_()
        self.activateWindow()
        self.search.setFocus()
