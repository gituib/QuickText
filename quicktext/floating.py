"""悬浮面板：常驻桌面的短语速填窗口。"""
from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QFontMetrics, QGuiApplication
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QMenu, QPushButton, QScrollArea, QSizePolicy,
                               QSlider, QSpinBox, QToolButton, QVBoxLayout, QWidget)

from . import theme
from .store import StoreError, mask_text

# palette 不可用时的兜底配色（浅色·湖青），保证界面在最坏情况下也不难看
_FALLBACK_PALETTE = {
    "primary": "#0D9488", "primary_hover": "#0F766E", "primary_pressed": "#115E59",
    "on_primary": "#FFFFFF", "accent": "#0D9488", "accent_hover": "#0F766E",
    "bg": "#F8FAFC", "surface": "#FFFFFF", "surface_alt": "#F1F5F9",
    "text": "#0F172A", "text_soft": "#334155", "muted": "#E2E8F0",
    "muted_text": "#64748B", "border": "#E2E8F0", "border_strong": "#CBD5E1",
    "selected": "#CCFBF1", "selected_text": "#134E4A", "row_hover": "#F1F5F9",
    "header_bg": "#FFFFFF", "header_text": "#0F172A", "scroll": "#CBD5E1",
    "disabled": "#94A3B8", "danger": "#DC2626", "warn": "#D97706", "success": "#16A34A",
}


def palette(index: int) -> dict:
    """取当前主题配色；theme.palette 不存在时使用本地兜底。"""
    keys = ("primary", "border", "surface", "text", "muted_text", "warn", "header_bg")
    try:
        fn = getattr(theme, "palette", None)
        if fn is not None:
            c = fn(index)
            if isinstance(c, dict) and all(k in c for k in keys):
                return c
    except Exception:
        pass
    return dict(_FALLBACK_PALETTE)


class _ElideLabel(QLabel):
    """多行预览文本：按当前宽度自动补省略号，避免被硬裁切。"""

    def __init__(self, rows, parent=None):
        super().__init__("\n".join(rows), parent)
        self._rows = list(rows)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        fm = QFontMetrics(self.font())
        width = max(24, self.width() - 4)
        super().setText("\n".join(fm.elidedText(t, Qt.ElideRight, width) for t in self._rows))


class _PhraseRow(QFrame):
    typeClicked = Signal(str)
    copyClicked = Signal(str)
    rowClicked = Signal(str)
    rowActivated = Signal(str)
    menuRequested = Signal(str, QPoint)

    def __init__(self, phrase, lines, show_copy, show_type, parent=None, tag_color=None,
                 hide_text=False):
        super().__init__(parent)
        self.setObjectName("phraseRow")
        self.setAttribute(Qt.WA_Hover, True)
        self.phrase_id = phrase["id"]
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        # 左侧 3px 色条：视觉上区分短语行
        bar = QFrame()
        bar.setObjectName("rowAccent")
        bar.setFixedWidth(3)
        bar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        lay.addWidget(bar)

        inner = QHBoxLayout()
        inner.setContentsMargins(12, 10, 10, 10)
        inner.setSpacing(6)
        group = phrase.get("group") or ""
        if group:
            tag = QLabel(group)
            tag.setObjectName("rowTag")
            tag.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            tag.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            inner.addWidget(tag, 0, Qt.AlignVCenter)
        if hide_text:
            rows = [mask_text(phrase["text"])]
        else:
            text = phrase["text"].replace("\r\n", "\n").replace("\r", "\n")
            rows = text.split("\n")[:max(1, lines)]
        label = _ElideLabel(rows)
        label.setObjectName("phraseText")
        label.setTextInteractionFlags(Qt.NoTextInteraction)
        label.setWordWrap(False)
        label.setMinimumWidth(1)
        label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        label.setToolTip("内容已隐藏" if hide_text else phrase["text"])
        label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        inner.addWidget(label, 1)
        if show_copy:
            btn = QPushButton("复制")
            btn.setObjectName("rowAction")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(54, 26)
            btn.clicked.connect(lambda: self.copyClicked.emit(phrase["id"]))
            inner.addWidget(btn, 0, Qt.AlignVCenter)
        if show_type:
            btn = QPushButton("输入")
            btn.setObjectName("rowType")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(54, 26)
            btn.clicked.connect(lambda: self.typeClicked.emit(phrase["id"]))
            inner.addWidget(btn, 0, Qt.AlignVCenter)
        lay.addLayout(inner, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.rowClicked.emit(self.phrase_id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.rowActivated.emit(self.phrase_id)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        self.menuRequested.emit(self.phrase_id, self.mapToGlobal(event.pos()))
        event.accept()


class FloatingPanel(QWidget):
    typeRequested = Signal(str)
    copyRequested = Signal(str)
    editRequested = Signal(str)
    toggleRequested = Signal(str)
    deleteRequested = Signal(str)
    pausedChanged = Signal(bool)
    settingsChanged = Signal()

    def __init__(self, store, theme_index=1):
        super().__init__(None)
        self.store = store
        self._theme_index = theme_index
        self._filter = ""
        self._rows = []
        self._current = -1
        self.setObjectName("floatingPanel")
        self.paused = False
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self._always_on_top = True
        self._suppress_hide_persist = False
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet(theme.floating_stylesheet(theme_index))
        # 透明背景 + panelCard 圆角；窗口样式为直角时由 panelCard 铺满
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._drag_offset = None
        # 搜索/分组输入做短延迟合并，避免每次按键都重建全部行控件
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(120)
        self._reload_timer.timeout.connect(self.reload_phrases)
        self._build_ui()
        self._apply_palette()
        self.apply_settings()
        self.reload_phrases()

    # ----------------------------------------------------------------- ui
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 圆角容器：包裹头部与主体（面板外层兜底样式，theme 有覆盖时以 theme 为准）
        self._card = QFrame()
        self._card.setObjectName("panelCard")
        root.addWidget(self._card)
        card = QVBoxLayout(self._card)
        card.setContentsMargins(0, 0, 0, 0)
        card.setSpacing(0)

        header = QWidget()
        header.setObjectName("floatingHeader")
        header.setFixedHeight(48)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 0, 8, 0)
        hl.setSpacing(7)

        self._dot = QLabel()
        self._dot.setObjectName("statusDot")
        self._dot.setFixedSize(8, 8)
        self._dot.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        hl.addWidget(self._dot, 0, Qt.AlignVCenter)

        title = QLabel("速填面板")
        title.setObjectName("floatingTitle")
        title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        hl.addWidget(title)

        self._status = QLabel("运行中")
        self._status.setObjectName("statusText")
        self._status.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        hl.addWidget(self._status, 0, Qt.AlignVCenter)
        hl.addStretch(1)

        self.btn_pause = QPushButton("暂停快键")
        self.btn_pause.setObjectName("primaryPause")
        self.btn_pause.setProperty("paused", "false")
        self.btn_pause.setCursor(Qt.PointingHandCursor)
        self.btn_pause.setFixedHeight(28)
        self.btn_pause.setMinimumWidth(84)
        self.btn_pause.clicked.connect(self.toggle_pause)
        hl.addWidget(self.btn_pause, 0, Qt.AlignVCenter)

        self.btn_settings = QToolButton()
        self.btn_settings.setObjectName("titleAction")
        self.btn_settings.setText("···")
        self.btn_settings.setFixedSize(30, 28)
        self.btn_settings.setCheckable(True)
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.setToolTip("面板设置")
        self.btn_settings.clicked.connect(self._toggle_settings)
        hl.addWidget(self.btn_settings, 0, Qt.AlignVCenter)

        self.btn_hide = QToolButton()
        self.btn_hide.setObjectName("titleAction")
        self.btn_hide.setText("×")
        self.btn_hide.setFixedSize(30, 28)
        self.btn_hide.setCursor(Qt.PointingHandCursor)
        self.btn_hide.setToolTip("隐藏面板")
        self.btn_hide.clicked.connect(self.hide)
        hl.addWidget(self.btn_hide, 0, Qt.AlignVCenter)

        card.addWidget(header)
        self._header = header
        header.installEventFilter(self)

        body = QWidget()
        body.setObjectName("floatingBody")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(10, 8, 8, 10)
        bl.setSpacing(8)

        # 顶部筛选行：搜索框 + 分组，合并为一行节省面板高度
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("筛选短语")
        self.search.setToolTip("↑↓ 选择，回车输入；右键短语可编辑、停用或删除")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(32)
        self.search.textChanged.connect(self._on_filter_changed)
        self.search.installEventFilter(self)
        filter_row.addWidget(self.search, 1)

        self.group_filter = QComboBox()
        self.group_filter.setObjectName("groupFilter")
        self.group_filter.setFixedHeight(32)
        self.group_filter.setFixedWidth(118)
        self.group_filter.addItem("全部分组", "")
        self.group_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.group_filter)
        bl.addLayout(filter_row)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("phraseScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.host = QWidget()
        self.host.setMinimumWidth(1)
        self.host.setObjectName("listHost")
        self.host.setAutoFillBackground(False)
        self.list_layout = QVBoxLayout(self.host)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.host)
        self.scroll.viewport().setObjectName("phraseViewport")
        self.scroll.viewport().setAutoFillBackground(False)
        bl.addWidget(self.scroll, 1)

        # 空状态提示：与列表叠放在同一位置
        self.empty = QLabel("暂无可用短语\n在「速填面板设置」里可调整显示选项", body)
        self.empty.setObjectName("emptyHint")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setWordWrap(True)
        self.empty.hide()

        card.addWidget(body, 1)
        self._body = body
        self._body_layout = bl

        self._settings_popup = self._build_settings_popup()
        self._settings_popup.hide()

    def _apply_palette(self):
        """控件级兜底取色：仅用于 theme 尚未覆盖的状态点。"""
        self._update_dot()

    def _update_dot(self):
        c = palette(self._theme_index)
        color = c["warn"] if self.paused else c["primary"]
        self._dot.setStyleSheet(
            "QLabel#statusDot { background: %s; border: none; border-radius: 4px; }" % color)
        if hasattr(self, "_status"):
            self._status.setText("已暂停" if self.paused else "运行中")
            if self.paused:
                self._status.setStyleSheet(
                    "QLabel#statusText { background: %s; color: %s; border: 1px solid %s;"
                    " border-radius: 8px; padding: 1px 7px; font-size: 10px;"
                    " font-weight: 600; }" % (c["warn"], c["on_primary"], c["warn"]))
            else:
                self._status.setStyleSheet("")

    def _build_settings_popup(self):
        popup = QFrame(self)
        popup.setObjectName("settingsPopup")
        popup.setFixedWidth(320)
        lay = QVBoxLayout(popup)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        lab = QLabel("面板设置")
        lab.setObjectName("settingsLabel")
        lay.addWidget(lab)

        for text, key, attr in (("显示“复制”按钮", "floatingPanelShowCopy", "chk_copy"),
                                ("显示“输入”按钮", "floatingPanelShowType", "chk_type"),
                                ("吸附到屏幕边缘", "floatingPanelSnapToEdge", "chk_snap")):
            chk = QCheckBox(text)
            chk.toggled.connect(lambda v, k=key: self._save(k, v))
            lay.addWidget(chk)
            setattr(self, attr, chk)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        lb1 = QLabel("每条显示行数")
        lb1.setFixedWidth(84)
        lb1.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row1.addWidget(lb1)
        self.spin_lines = QSpinBox()
        self.spin_lines.setRange(1, 10)
        self.spin_lines.setFixedWidth(64)
        self.spin_lines.setFixedHeight(26)
        self.spin_lines.valueChanged.connect(lambda v: self._save("floatingPanelTextLines", v))
        row1.addWidget(self.spin_lines)
        row1.addStretch(1)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        lb2 = QLabel("不透明度")
        lb2.setFixedWidth(84)
        lb2.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row2.addWidget(lb2)
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(30, 100)
        self.slider_opacity.setSingleStep(1)
        self.slider_opacity.valueChanged.connect(self._on_opacity)
        self.spin_opacity = QSpinBox()
        self.spin_opacity.setRange(30, 100)
        self.spin_opacity.setSuffix("%")
        self.spin_opacity.setFixedWidth(64)
        self.spin_opacity.setFixedHeight(26)
        self.spin_opacity.valueChanged.connect(self._on_opacity)
        row2.addWidget(self.slider_opacity, 1)
        row2.addWidget(self.spin_opacity)
        lay.addLayout(row2)
        popup.adjustSize()
        return popup

    def _on_filter_changed(self, _value=None):
        self._filter = (self.search.text() or "").strip()
        self._reload_timer.start()

    def set_theme(self, theme_index):
        if theme_index == self._theme_index:
            return
        self._theme_index = theme_index
        self.setStyleSheet(theme.floating_stylesheet(theme_index))
        self._update_dot()

    def _sync_groups(self):
        """分组下拉随数据变化刷新，同时保留当前选择。"""
        current = self.group_filter.currentData() or ""
        groups = self.store.groups()
        self.group_filter.blockSignals(True)
        try:
            self.group_filter.clear()
            self.group_filter.addItem("全部分组", "")
            for group in groups:
                self.group_filter.addItem(group, group)
            index = self.group_filter.findData(current)
            self.group_filter.setCurrentIndex(index if index >= 0 else 0)
        finally:
            self.group_filter.blockSignals(False)

    # ------------------------------------------------------- row navigation
    def _select_row(self, phrase_id, focus=True):
        for index, (_row, pid) in enumerate(self._rows):
            if pid == phrase_id:
                self._set_current(index)
                if focus:
                    self.setFocus(Qt.MouseFocusReason)
                return

    def _set_current(self, index):
        if not self._rows:
            return
        index = max(0, min(index, len(self._rows) - 1))
        self._current = index
        for i, (row, _pid) in enumerate(self._rows):
            row.setProperty("current", i == index)
            row.style().unpolish(row)
            row.style().polish(row)
        self.scroll.ensureWidgetVisible(self._rows[index][0], 0, 8)

    def _show_row_menu(self, phrase_id, pos):
        phrase = next((p for p in self.store.phrases if p["id"] == phrase_id), None)
        if phrase is None:
            return
        menu = QMenu(self)
        try:
            menu.setStyleSheet(theme.build_stylesheet(self._theme_index, "dialog"))
        except Exception:
            pass
        act_type = menu.addAction("输入")
        act_copy = menu.addAction("复制")
        menu.addSeparator()
        act_edit = menu.addAction("编辑…")
        act_toggle = menu.addAction("停用" if phrase["enabled"] else "启用")
        menu.addSeparator()
        act_delete = menu.addAction("删除")
        chosen = menu.exec(pos)
        if chosen is act_type:
            self.typeRequested.emit(phrase_id)
        elif chosen is act_copy:
            self.copyRequested.emit(phrase_id)
        elif chosen is act_edit:
            self.editRequested.emit(phrase_id)
        elif chosen is act_toggle:
            self.toggleRequested.emit(phrase_id)
        elif chosen is act_delete:
            self.deleteRequested.emit(phrase_id)

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Down, Qt.Key_Up) and self._rows:
            if self._current < 0:
                self._set_current(0 if key == Qt.Key_Down else len(self._rows) - 1)
            else:
                step = 1 if key == Qt.Key_Down else -1
                self._set_current(self._current + step)
            return
        if key in (Qt.Key_Return, Qt.Key_Enter) and self._current >= 0:
            self.typeRequested.emit(self._rows[self._current][1])
            return
        if key == Qt.Key_Escape:
            if self.search.text():
                self.search.clear()
            else:
                self.hide()
            return
        super().keyPressEvent(event)

    def _on_opacity(self, value):
        self.setWindowOpacity(max(0.3, value / 100.0))
        if self.slider_opacity.value() != value:
            self.slider_opacity.blockSignals(True)
            self.slider_opacity.setValue(value)
            self.slider_opacity.blockSignals(False)
        if self.spin_opacity.value() != value:
            self.spin_opacity.blockSignals(True)
            self.spin_opacity.setValue(value)
            self.spin_opacity.blockSignals(False)
        self._save("floatingPanelOpacity", int(value), reload=False)

    def _save(self, key, value, reload=True):
        self.store.settings[key] = value
        try:
            self.store.save()
        except StoreError:
            pass
        if reload and key in ("floatingPanelShowCopy", "floatingPanelShowType",
                              "floatingPanelTextLines"):
            self.reload_phrases()
        self.settingsChanged.emit()

    def _toggle_settings(self):
        if self._settings_popup.isVisible():
            self._settings_popup.hide()
            self.btn_settings.setChecked(False)
            return
        # 面板较窄时收窄弹层，左右各留 8px 边距
        self._settings_popup.setFixedWidth(max(240, min(320, self.width() - 16)))
        self._settings_popup.adjustSize()
        x = max(0, self.width() - self._settings_popup.width() - 8)
        self._settings_popup.move(x, self._header.height() + 4)
        self._settings_popup.show()
        self._settings_popup.raise_()
        self.btn_settings.setChecked(True)

    # ------------------------------------------------------------ actions
    def toggle_pause(self):
        self.paused = not self.paused
        self.btn_pause.setText("恢复快键" if self.paused else "暂停快键")
        self.btn_pause.setProperty("paused", "true" if self.paused else "false")
        self.btn_pause.style().unpolish(self.btn_pause)
        self.btn_pause.style().polish(self.btn_pause)
        self._update_dot()
        self.pausedChanged.emit(self.paused)

    def set_paused(self, paused):
        if paused != self.paused:
            self.toggle_pause()

    def apply_settings(self):
        s = self.store.settings
        self.chk_copy.setChecked(bool(s.get("floatingPanelShowCopy", True)))
        self.chk_type.setChecked(bool(s.get("floatingPanelShowType", True)))
        self.chk_snap.setChecked(bool(s.get("floatingPanelSnapToEdge", True)))
        self.spin_lines.setValue(int(s.get("floatingPanelTextLines", 2) or 2))
        opacity = int(s.get("floatingPanelOpacity", 97) or 97)
        self.slider_opacity.blockSignals(True)
        self.spin_opacity.blockSignals(True)
        self.slider_opacity.setValue(opacity)
        self.spin_opacity.setValue(opacity)
        self.slider_opacity.blockSignals(False)
        self.spin_opacity.blockSignals(False)
        self.setWindowOpacity(max(0.3, opacity / 100.0))
        w = int(s.get("floatingPanelWidth", 320) or 320)
        h = int(s.get("floatingPanelHeight", 420) or 420)
        self.resize(w, h)
        x = int(s.get("floatingPanelX", 0) or 0)
        y = int(s.get("floatingPanelY", 0) or 0)
        pos = self._clamped_position(x, y, w, h) if (x or y) else None
        if pos:
            self.move(*pos)
        else:
            screen = self.screen().availableGeometry() if self.screen() else None
            if screen:
                self.move(screen.right() - w - 24, screen.top() + 80)

    def _clamped_position(self, x, y, w, h):
        """把保存过的位置收进所有屏幕的可用区域；原屏幕已拔掉时返回 None 走默认位置。"""
        areas = [scr.availableGeometry() for scr in QGuiApplication.screens()]
        if not areas:
            return (x, y)
        left = min(a.left() for a in areas)
        top = min(a.top() for a in areas)
        right = max(a.right() for a in areas)
        bottom = max(a.bottom() for a in areas)
        if x + w <= left or x >= right or y + h <= top or y >= bottom:
            return None
        return (max(left, min(x, right - w)), max(top, min(y, bottom - h)))

    def reload_phrases(self):
        # 过滤文本在面板内部使用，不影响 store
        self._sync_groups()
        keyword = self._filter.lower()
        group = self.group_filter.currentData() or ""
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        lines = int(self.store.settings.get("floatingPanelTextLines", 2) or 2)
        show_copy = bool(self.store.settings.get("floatingPanelShowCopy", True))
        show_type = bool(self.store.settings.get("floatingPanelShowType", True))
        self._rows = []
        self._current = -1
        count = 0
        hide_text = bool(self.store.settings.get("hidePhraseText", True))
        tag_color = palette(self._theme_index).get("muted_text", "#64748B")
        for phrase in self.store.phrases:
            if not phrase["enabled"]:
                continue
            if group and (phrase.get("group") or "") != group:
                continue
            if not self.store.matches(phrase, keyword):
                continue
            row = _PhraseRow(phrase, lines, show_copy, show_type, tag_color=tag_color,
                             hide_text=hide_text)
            row.typeClicked.connect(self.typeRequested.emit)
            row.copyClicked.connect(self.copyRequested.emit)
            row.rowClicked.connect(lambda pid: self._select_row(pid))
            row.rowActivated.connect(self.typeRequested.emit)
            row.menuRequested.connect(self._show_row_menu)
            self.list_layout.addWidget(row)
            self._rows.append((row, phrase["id"]))
            count += 1
        self.list_layout.addStretch(1)
        # 空状态：列表区居中提示
        if count:
            self.empty.hide()
            self.scroll.show()
        else:
            self.scroll.hide()
            self.empty.show()
            self._empty_relayout()
            self.empty.raise_()

    def _empty_relayout(self):
        if self.empty.isVisible():
            self.empty.setGeometry(self._body_layout.geometry().x() + 10,
                                   self.scroll.geometry().top(),
                                   max(1, self._body.width() - 18),
                                   max(1, self.scroll.geometry().height()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._empty_relayout()

    def showEvent(self, event):
        super().showEvent(event)
        self._empty_relayout()

    def hideEvent(self, event):
        super().hideEvent(event)
        # ×/Esc 关闭面板时同步设置，避免托盘勾选与重启恢复不一致
        if (not self._suppress_hide_persist
                and self.store.settings.get("showFloatingPanel", False)):
            self.store.settings["showFloatingPanel"] = False
            try:
                self.store.save()
            except StoreError:
                pass

    def set_always_on_top(self, on_top):
        """临时取消置顶，避免面板盖住以主窗口为父的模态对话框。"""
        if bool(on_top) == self._always_on_top:
            return
        self._always_on_top = bool(on_top)
        visible = self.isVisible()
        # 改窗口标志会触发一次 hide/show，不能让它写成“面板已关闭”
        self._suppress_hide_persist = True
        try:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, self._always_on_top)
            if visible:
                self.show()
        finally:
            self._suppress_hide_persist = False

    # -------------------------------------------------------- interactions
    def eventFilter(self, obj, event):
        if obj is self.search and event.type() == event.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key_Down, Qt.Key_Return, Qt.Key_Enter) and self._rows:
                self._set_current(0 if self._current < 0 else self._current)
                self.setFocus(Qt.TabFocusReason)
                if key in (Qt.Key_Return, Qt.Key_Enter):
                    self.typeRequested.emit(self._rows[self._current][1])
                return True
        if obj is self._header:
            if event.type() == event.Type.MouseButtonPress and event.button() == Qt.LeftButton:
                # 只有标题空白/状态点区域可拖动，头部内按钮保持可点击
                child = self._header.childAt(event.position().toPoint())
                if child is not None and child not in (self._header, self._dot):
                    return False
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if event.type() == event.Type.MouseMove and self._drag_offset is not None:
                self.move(event.globalPosition().toPoint() - self._drag_offset)
                return True
            if event.type() == event.Type.MouseButtonRelease and self._drag_offset is not None:
                self._drag_offset = None
                self._snap()
                self._save_position()
                return True
        return super().eventFilter(obj, event)

    def _snap(self):
        if not self.store.settings.get("floatingPanelSnapToEdge", True):
            return
        geo = self.screen().availableGeometry()
        x, y = self.x(), self.y()
        margin = 12
        if abs(x - geo.left()) < 20:
            x = geo.left() + margin
        if abs((x + self.width()) - geo.right()) < 20:
            x = geo.right() - self.width() - margin
        if abs(y - geo.top()) < 20:
            y = geo.top() + margin
        self.move(x, y)

    def _save_position(self):
        s = self.store.settings
        s["floatingPanelX"] = self.x()
        s["floatingPanelY"] = self.y()
        s["floatingPanelWidth"] = self.width()
        s["floatingPanelHeight"] = self.height()
        try:
            self.store.save()
        except StoreError:
            pass
