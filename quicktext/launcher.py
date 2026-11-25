"""应用速启：Spotlight 式搜索栏，按名称、拼音首字母、缩写或别名打开本机应用。"""
import os

from PySide6.QtCore import QEvent, QFileInfo, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QCursor, QFont, QGuiApplication, QIcon,
                           QPainter, QPixmap)
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileIconProvider,
                               QFrame, QHBoxLayout, QInputDialog, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMenu,
                               QPushButton, QVBoxLayout)

from . import inputsim, theme

_ROW_HEIGHT = 46


def _fallback_icon(text, palette):
    """图标取不到时用首字占位，保证每行视觉对齐。"""
    pix = QPixmap(24, 24)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setBrush(QColor(palette.get("primary", "#0D9488")))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, 24, 24, 6, 6)
    painter.setPen(QColor(palette.get("on_primary", "#FFFFFF")))
    font = QFont()
    font.setPixelSize(13)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pix.rect(), Qt.AlignCenter, (text or "?")[:1].upper())
    painter.end()
    return QIcon(pix)


class LauncherDialog(QDialog):
    """搜索栏本体：输入即筛，回车或单击直接打开。"""

    launched = Signal(str)          # 启动成功时带出应用 key

    def __init__(self, index, theme_index=1, parent=None):
        super().__init__(parent)
        self.index = index
        self.launched_app = False
        self.restore_focus = True      # 失焦关闭时不要抢回焦点
        self._theme_index = theme_index
        self._icons = {}
        self._suppress_close = 0
        self._closing = False
        self._provider = QFileIconProvider()
        self._palette = theme.palette(theme_index)
        self.setObjectName("launcher")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle("应用速启")
        self.setStyleSheet(theme.build_stylesheet(theme_index, "launcher"))
        self.resize(600, 460)
        self._build_ui()
        self.reload()

    # ---------------------------------------------------------------- ui
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._card = QFrame()
        self._card.setObjectName("launcherCard")
        root.addWidget(self._card)
        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(8)

        self.search = QLineEdit()
        self.search.setObjectName("launcherSearch")
        self.search.setPlaceholderText("搜索应用：名称、拼音首字母或别名")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(46)
        self.search.textChanged.connect(self.reload)
        self.search.installEventFilter(self)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.setObjectName("launcherList")
        self.list.setIconSize(QSize(28, 28))
        self.list.setUniformItemSizes(False)
        self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list.itemClicked.connect(self._on_click)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._show_menu)
        layout.addWidget(self.list, 1)

        self.error = QLabel("")
        self.error.setObjectName("launcherError")
        self.error.setWordWrap(True)
        self.error.hide()
        layout.addWidget(self.error)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        hint = QLabel("↑↓ 选择 · 回车打开 · Esc 关闭 · 右键可置顶/别名/隐藏")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        bottom.addWidget(hint, 1)
        self.btn_hidden = QPushButton("")
        self.btn_hidden.setObjectName("launcherHidden")
        self.btn_hidden.setCursor(Qt.PointingHandCursor)
        self.btn_hidden.setFlat(True)
        self.btn_hidden.setAutoDefault(False)
        self.btn_hidden.clicked.connect(self._open_hidden)
        bottom.addWidget(self.btn_hidden)
        layout.addLayout(bottom)

    # ------------------------------------------------------------ content
    def _icon_for(self, app):
        key = app["key"]
        icon = self._icons.get(key)
        if icon is not None:
            return icon
        icon = QIcon()
        try:
            icon = self._provider.icon(QFileInfo(app["path"]))
        except Exception:
            icon = QIcon()
        if icon.isNull():
            icon = _fallback_icon(app["name"], self._palette)
        self._icons[key] = icon
        return icon

    def _label_for(self, app):
        label = app["name"]
        if app["alias"]:
            label = "%s    [%s]" % (label, app["alias"])
        if app["pinned"]:
            label = "置顶    " + label
        return label

    def reload(self):
        keyword = self.search.text()
        apps = self.index.search(keyword)
        self.list.clear()
        for app in apps:
            item = QListWidgetItem(self._icon_for(app), self._label_for(app))
            item.setData(Qt.UserRole, app["key"])
            item.setToolTip(app["path"])
            item.setSizeHint(QSize(0, _ROW_HEIGHT))
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)
        else:
            item = QListWidgetItem("没有匹配的应用")
            item.setFlags(Qt.NoItemFlags)
            item.setTextAlignment(Qt.AlignCenter)
            item.setSizeHint(QSize(0, _ROW_HEIGHT))
            self.list.addItem(item)
        hidden = len(self.index.hidden_apps())
        self.btn_hidden.setText("已隐藏 %d 个" % hidden if hidden else "")
        self.btn_hidden.setVisible(hidden > 0)

    # ------------------------------------------------------------ opening
    def _current_key(self):
        item = self.list.currentItem()
        if item is None:
            return ""
        return item.data(Qt.UserRole) or ""

    def _on_click(self, item):
        key = item.data(Qt.UserRole) if item is not None else ""
        if key:
            self._open_key(key)

    def _open_current(self):
        key = self._current_key()
        if key:
            self._open_key(key)

    def _open_key(self, key):
        app = self.index.get(key)
        if app is None:
            return
        if not os.path.exists(app["path"]):
            self._show_error("文件已不存在：%s" % app["name"])
            return
        # 启动瞬间新窗口可能抢走焦点，这里先抑制“失焦即关”，避免误判
        self._suppress_close += 1
        try:
            os.startfile(app["path"])
        except OSError as exc:
            self._show_error("无法启动 %s：%s" % (app["name"], exc))
            return
        finally:
            self._suppress_close -= 1
        self.index.record_use(key)
        self.launched_app = True
        self.launched.emit(key)
        self.close()

    def _show_error(self, message):
        self.error.setText(message)
        self.error.show()

    # --------------------------------------------------------- navigation
    def _move(self, delta):
        count = self.list.count()
        if not count:
            return
        row = (self.list.currentRow() + delta) % count
        self.list.setCurrentRow(row)
        self.list.scrollToItem(self.list.item(row))

    def _page(self, pages):
        row = self.list.currentRow() + pages * 6
        row = max(0, min(row, self.list.count() - 1))
        if row >= 0:
            self.list.setCurrentRow(row)
            self.list.scrollToItem(self.list.item(row))

    def eventFilter(self, obj, event):
        if obj is self.search and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Down:
                self._move(1)
                return True
            if key == Qt.Key_Up:
                self._move(-1)
                return True
            if key in (Qt.Key_PageDown, Qt.Key_PageUp):
                self._page(1 if key == Qt.Key_PageDown else -1)
                return True
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self._open_current()
                return True
            if key == Qt.Key_Escape:
                self.close()
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.close()
            return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            self._open_current()
            return
        if key == Qt.Key_Down:
            self._move(1)
            return
        if key == Qt.Key_Up:
            self._move(-1)
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        self.list.setFocus()
        super().wheelEvent(event)

    def event(self, ev):
        # 点击窗口外（焦点丢失）即关闭；右键菜单或输入框弹出期间不关闭
        if ev.type() == QEvent.WindowDeactivate and not self._closing \
                and self._suppress_close == 0:
            self.restore_focus = False
            self.close()
        return super().event(ev)

    def closeEvent(self, event):
        self._closing = True
        super().closeEvent(event)

    # ----------------------------------------------------- context menu
    def _show_menu(self, pos):
        item = self.list.itemAt(pos)
        key = item.data(Qt.UserRole) if item is not None else ""
        app = self.index.get(key) if key else None
        if app is None:
            return
        menu = QMenu(self)
        act_pin = menu.addAction("取消置顶" if app["pinned"] else "置顶")
        act_alias = menu.addAction("设置别名…")
        menu.addSeparator()
        act_hide = menu.addAction("从列表隐藏")
        self._suppress_close += 1
        try:
            chosen = menu.exec(self.list.viewport().mapToGlobal(pos))
        finally:
            self._suppress_close -= 1
        if chosen is act_pin:
            self.index.set_pinned(key, not app["pinned"])
            self.reload()
        elif chosen is act_alias:
            self._edit_alias(app)
        elif chosen is act_hide:
            self.index.set_hidden(key, True)
            self.reload()

    def _edit_alias(self, app):
        self._suppress_close += 1
        try:
            text, ok = QInputDialog.getText(self, "设置别名",
                                            "搜索别名（留空表示取消）：",
                                            QLineEdit.Normal, app["alias"])
        finally:
            self._suppress_close -= 1
        if ok:
            self.index.set_alias(app["key"], text)
            self.reload()

    def _open_hidden(self):
        self._suppress_close += 1
        try:
            HiddenAppsDialog(self.index, self._theme_index, self).exec()
        finally:
            self._suppress_close -= 1
        self.reload()

    # ------------------------------------------------------------ show
    def show_launcher(self):
        self.error.hide()
        self.search.clear()
        self.reload()
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            x = area.x() + (area.width() - self.width()) // 2
            y = area.y() + max(40, int((area.height() - self.height()) * 0.28))
            self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        # 全局热键唤起时本进程处于后台，Windows 前台锁定会让窗口拿不到焦点：
        # 输入框打不了字，还会立刻失焦被自动关闭（表现为“速启不弹出”）。
        inputsim.restore_window(int(self.winId()))
        self.search.setFocus()
        QTimer.singleShot(0, self.search.setFocus)


class HiddenAppsDialog(QDialog):
    """已隐藏应用的恢复入口。"""

    def __init__(self, index, theme_index=1, parent=None):
        super().__init__(parent)
        self.index = index
        self.setWindowTitle("已隐藏的应用")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setStyleSheet(theme.build_stylesheet(theme_index, "launcher"))
        self.resize(460, 340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)
        title = QLabel("勾选需要恢复的应用")
        title.setObjectName("hiddenTitle")
        layout.addWidget(title)

        self.list = QListWidget()
        self.list.setObjectName("hiddenList")
        for app in index.hidden_apps():
            item = QListWidgetItem(app["name"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, app["key"])
            item.setToolTip(app["path"])
            item.setSizeHint(QSize(0, 32))
            self.list.addItem(item)
        if not self.list.count():
            item = QListWidgetItem("没有已隐藏的应用")
            item.setFlags(Qt.NoItemFlags)
            item.setTextAlignment(Qt.AlignCenter)
            self.list.addItem(item)
        self.list.itemClicked.connect(self._toggle_item)
        layout.addWidget(self.list, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_cancel)
        self.btn_restore = QPushButton("恢复所选")
        self.btn_restore.setDefault(True)
        self.btn_restore.clicked.connect(self._restore)
        self.btn_restore.setEnabled(bool(index.hidden_apps()))
        buttons.addWidget(self.btn_restore)
        layout.addLayout(buttons)

    def _toggle_item(self, item):
        if item.flags() & Qt.ItemIsUserCheckable:
            state = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
            item.setCheckState(state)

    def _restore(self):
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.checkState() == Qt.Checked:
                self.index.set_hidden(item.data(Qt.UserRole), False)
        self.accept()
