"""主窗口。"""
from PySide6.QtCore import QItemSelectionModel, QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QIcon, QKeySequence
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMainWindow, QMenu, QPushButton, QTableWidget,
                               QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from . import winapi as W
from . import theme
from .phrase_dialog import PhraseDialog
from .settings_dialog import SettingsDialog
from .store import PhraseStore, StoreError, mask_text
from .version import __version__


def _action(parent, text, slot=None, shortcut=None, checkable=False, checked=False):
    act = QAction(text, parent)
    act.setCheckable(checkable)
    if checkable:
        act.setChecked(checked)
    if shortcut:
        act.setShortcut(QKeySequence(shortcut))
    if slot:
        act.triggered.connect(slot)
    return act


class PhraseTable(QTableWidget):
    """支持拖拽调整顺序的短语表格。"""
    orderChanged = Signal(list)

    def __init__(self, rows, cols, parent=None):
        super().__init__(rows, cols, parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setDefaultDropAction(Qt.MoveAction)

    def dropEvent(self, event):
        if not self.dragEnabled():
            event.ignore()
            return
        source = self.currentRow()
        index = self.indexAt(event.position().toPoint())
        target = index.row() if index.isValid() else self.rowCount() - 1
        if source < 0 or target < 0 or source == target:
            event.ignore()
            return
        ids = [self.item(row, 0).data(Qt.UserRole) for row in range(self.rowCount())]
        if source >= len(ids):
            event.ignore()
            return
        moved = ids.pop(source)
        ids.insert(min(target, len(ids)), moved)
        event.accept()
        # 拖放过程中重建表格不安全，等 drop 结束后再刷新
        QTimer.singleShot(0, lambda: self.orderChanged.emit(ids))


class GroupList(QListWidget):
    """侧栏分组列表：真实分组可拖拽排序，「全部短语 / 未分组」等固定项不参与。"""

    orderChanged = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

    def dropEvent(self, event):
        if not self.dragEnabled():
            event.ignore()
            return
        row = self.currentRow()
        item = self.item(row)
        if item is None or not item.data(Qt.UserRole):
            # 拖的是固定项，交给基线处理会打乱顺序，直接取消
            event.ignore()
            return
        super().dropEvent(event)
        names = self.group_order()
        QTimer.singleShot(0, lambda: self.orderChanged.emit(names))

    def group_order(self):
        """按当前视觉顺序返回真实分组名，固定项（全部短语 / 未分组）不参与。"""
        names = []
        for i in range(self.count()):
            value = self.item(i).data(Qt.UserRole)
            if value:
                names.append(str(value))
        return names


class MainWindow(QMainWindow):
    addRequested = Signal()
    editRequested = Signal()
    deleteRequested = Signal()
    importRequested = Signal()
    exportRequested = Signal()
    settingsRequested = Signal()
    optionsRequested = Signal()
    launcherRequested = Signal()
    pauseRequested = Signal()
    floatingPanelRequested = Signal(bool)
    quitRequested = Signal()
    enableRequested = Signal(bool)
    copyRequested = Signal(str)
    reorderRequested = Signal(list)
    groupAddRequested = Signal()
    groupRenameRequested = Signal(str)
    groupDeleteRequested = Signal(str)
    groupOrderRequested = Signal(list)
    phrasesMoveRequested = Signal(list, str)
    privacyChanged = Signal(bool)

    def __init__(self, store: PhraseStore):
        super().__init__()
        self.store = store
        self.paused = False
        self.setWindowTitle(W.APP_TITLE)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        icon = W.app_icon_path()
        if icon:
            self.setWindowIcon(QIcon(icon))
        self.resize(1080, 700)
        self.setMinimumSize(760, 520)
        # 搜索/分组输入做短延迟合并，避免每个按键都重建整张表格
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(120)
        self._refresh_timer.timeout.connect(self.refresh)
        self._build_ui()
        self.apply_theme(refresh=False)
        self.refresh()

    # ------------------------------------------------------------------ ui
    def _build_ui(self):
        central = QWidget(self)
        central.setObjectName("central")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())

        content = QWidget()
        content.setObjectName("content")
        outer = QVBoxLayout(content)
        outer.setContentsMargins(26, 22, 26, 14)
        outer.setSpacing(14)
        root.addWidget(content, 1)

        # 页头：标题 + 统计 + 更多 / 新建
        header = QHBoxLayout()
        header.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(3)
        self.lbl_page_title = QLabel("短语库")
        self.lbl_page_title.setObjectName("pageTitle")
        self.lbl_page_sub = QLabel("共 0 条短语 · 0 条已启用")
        self.lbl_page_sub.setObjectName("pageSubtitle")
        titles.addWidget(self.lbl_page_title)
        titles.addWidget(self.lbl_page_sub)
        header.addLayout(titles, 1)

        self.btn_more = QToolButton()
        self.btn_more.setObjectName("moreButton")
        self.btn_more.setText("•••")
        self.btn_more.setFixedSize(36, 36)
        self.btn_more.setCursor(Qt.PointingHandCursor)
        self.btn_more.setPopupMode(QToolButton.InstantPopup)
        self.btn_more.setToolTip("更多操作")
        header.addWidget(self.btn_more, 0, Qt.AlignVCenter)

        self.btn_add = self._kind_button("+ 新建短语", "primary", self.addRequested, 36)
        self.btn_add.setMinimumWidth(118)
        header.addWidget(self.btn_add, 0, Qt.AlignVCenter)
        outer.addLayout(header)

        # 搜索行
        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("搜索名称、缩写、拼音首字母或内容")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumHeight(40)
        self.search.textChanged.connect(self.schedule_refresh)
        search_row.addWidget(self.search, 1)
        self.btn_privacy = QPushButton("隐藏内容")
        self.btn_privacy.setProperty("kind", "ghost")
        self.btn_privacy.setCursor(Qt.PointingHandCursor)
        self.btn_privacy.setMinimumHeight(40)
        self.btn_privacy.clicked.connect(self.toggle_text_visibility)
        search_row.addWidget(self.btn_privacy)
        self._sync_privacy_button()
        outer.addLayout(search_row)

        # 内容区：表格 + 空状态叠加
        self.table = PhraseTable(0, 4)
        self.table.setObjectName("phrases")
        self.table.setHorizontalHeaderLabels(["名称", "分组", "快捷键", "内容"])
        for col in range(4):
            item = self.table.horizontalHeaderItem(col)
            if item is not None:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self.table.doubleClicked.connect(lambda _idx: self.editRequested.emit())
        self.table.orderChanged.connect(self.reorderRequested.emit)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.Interactive)
        header_view.setSectionResizeMode(1, QHeaderView.Interactive)
        header_view.setSectionResizeMode(2, QHeaderView.Interactive)
        header_view.setSectionResizeMode(3, QHeaderView.Stretch)
        header_view.setStretchLastSection(True)
        header_view.setFixedHeight(38)
        self.table.setColumnWidth(0, 170)
        self.table.setColumnWidth(1, 110)
        self.table.setColumnWidth(2, 118)
        header_view.sectionResized.connect(self._on_section_resized)
        self.table.verticalHeader().setDefaultSectionSize(40)

        self.empty_hint = QLabel("还没有短语\n点击右上角「新建短语」开始添加", self.table.viewport())
        self.empty_hint.setObjectName("emptyHint")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.empty_hint.hide()
        outer.addWidget(self.table, 1)

        # 底部操作栏
        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        self.btn_edit = self._kind_button("修改", "ghost", self.editRequested)
        self.btn_delete = self._kind_button("删除", "danger", self.deleteRequested)
        bottom.addWidget(self.btn_edit)
        bottom.addWidget(self.btn_delete)
        bottom.addStretch(1)
        self.tip_drag = QLabel("拖动行可调整顺序")
        self.tip_drag.setObjectName("pageSubtitle")
        bottom.addWidget(self.tip_drag)
        bottom.addSpacing(8)
        self.btn_import = self._kind_button("导入", "ghost", self.importRequested)
        self.btn_export = self._kind_button("导出", "ghost", self.exportRequested)
        bottom.addWidget(self.btn_import)
        bottom.addWidget(self.btn_export)
        outer.addLayout(bottom)

        self.setCentralWidget(central)
        self.status = self.statusBar()
        self.status.showMessage("就绪")
        self.lbl_stats = QLabel("共 0 条 · 启用 0 条")
        self.status.addPermanentWidget(self.lbl_stats)

        self._build_menus()

    # -------------------------------------------------------------- 侧边栏
    def _build_sidebar(self):
        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(216)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(16, 20, 16, 14)
        lay.setSpacing(6)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        mark = QLabel("速")
        mark.setObjectName("brandMark")
        mark.setFixedSize(38, 38)
        brand.addWidget(mark)
        names = QVBoxLayout()
        names.setSpacing(1)
        name = QLabel("速填文本")
        name.setObjectName("brandName")
        tag = QLabel("QUICKTEXT")
        tag.setObjectName("brandTag")
        names.addWidget(name)
        names.addWidget(tag)
        brand.addLayout(names, 1)
        lay.addLayout(brand)
        lay.addSpacing(20)

        lay.addWidget(self._nav_section("工作区"))
        lay.addSpacing(2)
        self.nav_library = self._nav_button("短语库")
        self.nav_library.setCheckable(True)
        self.nav_library.setChecked(True)
        self.nav_library.clicked.connect(self._on_nav_library)
        lay.addWidget(self.nav_library)

        self.nav_launcher = self._nav_button("应用速启")
        self.nav_launcher.setToolTip("打开应用速启搜索栏")
        self.nav_launcher.clicked.connect(lambda: self.launcherRequested.emit())
        lay.addWidget(self.nav_launcher)

        self.nav_panel = self._nav_button("悬浮面板")
        self.nav_panel.setCheckable(True)
        self.nav_panel.setChecked(bool(self.store.settings.get("showFloatingPanel", False)))
        self.nav_panel.clicked.connect(
            lambda checked=False: self.floatingPanelRequested.emit(bool(checked)))
        lay.addWidget(self.nav_panel)

        lay.addSpacing(16)
        group_head = QHBoxLayout()
        group_head.setContentsMargins(0, 0, 0, 0)
        group_head.setSpacing(4)
        group_head.addWidget(self._nav_section("分组"))
        group_head.addStretch(1)
        self.btn_group_add = QToolButton()
        self.btn_group_add.setObjectName("navSectionAction")
        self.btn_group_add.setText("+")
        self.btn_group_add.setFixedSize(24, 20)
        self.btn_group_add.setCursor(Qt.PointingHandCursor)
        self.btn_group_add.setToolTip("新建分组")
        self.btn_group_add.clicked.connect(lambda: self.groupAddRequested.emit())
        group_head.addWidget(self.btn_group_add, 0, Qt.AlignVCenter)
        lay.addLayout(group_head)
        lay.addSpacing(2)
        self.group_list = GroupList()
        self.group_list.setObjectName("groupList")
        self.group_list.setFrameShape(QFrame.NoFrame)
        self.group_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.group_list.setToolTip("点击按分组筛选；拖动分组名可调整顺序；右键可新建、重命名或删除分组")
        self.group_list.itemSelectionChanged.connect(self.schedule_refresh)
        self.group_list.orderChanged.connect(self.groupOrderRequested.emit)
        self.group_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.group_list.customContextMenuRequested.connect(self._show_group_menu)
        lay.addWidget(self.group_list, 1)

        lay.addSpacing(6)
        line = QFrame()
        line.setObjectName("hairline")
        line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(1)
        lay.addWidget(line)
        lay.addSpacing(4)

        self.nav_settings = self._nav_button("设置")
        self.nav_settings.clicked.connect(lambda: self.settingsRequested.emit())
        lay.addWidget(self.nav_settings)

        self.nav_pause = self._nav_button("暂停快捷键")
        self.nav_pause.setCheckable(True)
        self.nav_pause.clicked.connect(lambda: self.pauseRequested.emit())
        lay.addWidget(self.nav_pause)

        lay.addSpacing(6)
        version = QLabel("v%s · 自动输入" % __version__)
        version.setObjectName("versionLabel")
        lay.addWidget(version)
        return side

    def _nav_section(self, text):
        label = QLabel(text)
        label.setObjectName("navSection")
        return label

    def _nav_button(self, text, checkable=False, checked=False):
        btn = QPushButton(text)
        btn.setObjectName("navItem")
        btn.setCheckable(checkable)
        btn.setChecked(checked)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(34)
        return btn

    def _on_nav_library(self):
        # 可切换按钮二次点击会取消勾选，这里强制保持选中以保留高亮
        self.nav_library.setChecked(True)
        self.search.setFocus()

    def _kind_button(self, text, kind, signal, height=34):
        btn = QPushButton(text)
        btn.setProperty("kind", kind)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(height)
        btn.clicked.connect(signal.emit)
        return btn

    # --------------------------------------------------------------- 隐私
    def text_hidden(self):
        return bool(self.store.settings.get("hidePhraseText", True))

    def toggle_text_visibility(self):
        self.store.settings["hidePhraseText"] = not self.text_hidden()
        self._sync_privacy_button()
        self.refresh()
        self.privacyChanged.emit(self.text_hidden())
        try:
            self.store.save()
        except StoreError:
            pass

    def _sync_privacy_button(self):
        hidden = self.text_hidden()
        self.btn_privacy.setText("显示内容" if hidden else "隐藏内容")
        self.btn_privacy.setToolTip(
            "「内容」列已遮挡，点击恢复显示" if hidden
            else "遮挡「内容」列，避免旁人看到短语正文")

    def _build_menus(self):
        bar = self.menuBar()
        bar.setVisible(False)

        m_file = bar.addMenu("文件(&F)")
        m_file.addAction(_action(self, "添加(&A)…", self.addRequested.emit, "Ctrl+N"))
        self.act_edit = _action(self, "修改(&E)…", self.editRequested.emit, "Ctrl+E")
        # 焦点在搜索框时 Ctrl+E 不应弹出编辑对话框，快捷键只在表格区域内生效
        self.act_edit.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        m_file.addAction(self.act_edit)
        self.table.addAction(self.act_edit)
        self.act_delete = _action(self, "删除(&D)", self.deleteRequested.emit, "Del")
        m_file.addAction(self.act_delete)
        m_file.addSeparator()
        self.act_enable = _action(self, "启用所选", lambda: self.enableRequested.emit(True))
        self.act_disable = _action(self, "停用所选", lambda: self.enableRequested.emit(False))
        m_file.addAction(self.act_enable)
        m_file.addAction(self.act_disable)
        m_file.addSeparator()
        m_file.addAction(_action(self, "导入(&I)…", self.importRequested.emit, "Ctrl+I"))
        m_file.addAction(_action(self, "导出(&O)…", self.exportRequested.emit, "Ctrl+Shift+S"))
        m_file.addSeparator()
        m_file.addAction(_action(self, "退出(&X)", self.quitRequested.emit, "Alt+F4"))

        m_set = bar.addMenu("设置(&S)")
        m_set.addAction(_action(self, "选项(&O)…", self.optionsRequested.emit, "Ctrl+O"))
        m_set.addSeparator()
        self.act_pause = _action(self, "暂停快捷键", self.pauseRequested.emit, "Ctrl+Alt+P", checkable=True)
        m_set.addAction(self.act_pause)

        m_view = bar.addMenu("查看(&V)")
        # QAction.triggered 只带一个 bool，直接连接 Signal(bool).emit 会因缺少实参而报错
        self.act_panel = _action(
            self, "悬浮面板(&F)",
            lambda checked=False: self.floatingPanelRequested.emit(bool(checked)),
            checkable=True,
            checked=bool(self.store.settings.get("showFloatingPanel", False)))
        m_view.addAction(self.act_panel)
        m_view.addAction(_action(self, "聚焦搜索", lambda: self.search.setFocus(), "Ctrl+F"))

        # 顶部“更多”菜单复用同一组动作，菜单栏本身隐藏以保持界面干净
        self.more_menu = QMenu(self)
        self.more_menu.addActions(m_file.actions())
        self.more_menu.addSeparator()
        self.more_menu.addActions(m_set.actions())
        self.more_menu.addSeparator()
        self.more_menu.addActions(m_view.actions())
        self.btn_more.setMenu(self.more_menu)

    # --------------------------------------------------------------- theme
    def apply_theme(self, refresh=True):
        idx = int(self.store.settings.get("uiTheme", 1))
        self.setStyleSheet(theme.build_stylesheet(idx, "main"))
        p = theme.palette(idx)
        self.disabled_color = p["disabled"]
        self.muted_color = p["muted_text"]
        self.empty_hint.setStyleSheet("color: %s; background: transparent;" % p["muted_text"])
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.horizontalHeader().setFixedHeight(38)
        icon = W.app_icon_path()
        if icon:
            self.setWindowIcon(QIcon(icon))
        if refresh:
            self.refresh()
        self.update()

    def schedule_refresh(self, *_args):
        self._refresh_timer.start()

    # ----------------------------------------------------------------- data
    def refresh(self):
        keyword = self.search.text() if hasattr(self, "search") else ""
        self._sync_group_filter()
        group = self._current_group()
        items = self.store.search(keyword, group)
        selected_ids = {p["id"] for p in self.selected_phrases()}
        current = self.selected_phrase()
        current_id = current["id"] if current else None
        disabled_color = getattr(self, "disabled_color", theme.palette(0)["disabled"])
        hide_text = self.text_hidden()
        muted_color = getattr(self, "muted_color", theme.palette(0)["muted_text"])
        self.table.setUpdatesEnabled(False)
        self.table.clearContents()
        self.table.setRowCount(len(items))
        for row, phrase in enumerate(items):
            name_item = QTableWidgetItem(phrase["name"])
            name_item.setData(Qt.UserRole, phrase["id"])
            name_font = QFont(name_item.font())
            name_font.setBold(True)
            name_item.setFont(name_font)
            group_item = QTableWidgetItem(phrase.get("group") or "")
            hk_item = QTableWidgetItem(W.hotkey_text(phrase["hotkeyMods"], phrase["hotkeyVk"]))
            text = phrase["text"].replace("\r\n", " / ").replace("\n", " / ")
            if hide_text:
                text_item = QTableWidgetItem(mask_text(phrase["text"]))
                text_item.setToolTip("内容已隐藏")
                text_item.setForeground(QBrush(QColor(muted_color)))
            else:
                text_item = QTableWidgetItem(text)
                text_item.setToolTip(phrase["text"])
            if not phrase["enabled"]:
                for it in (name_item, group_item, hk_item, text_item):
                    it.setForeground(QBrush(QColor(disabled_color)))
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, group_item)
            self.table.setItem(row, 2, hk_item)
            self.table.setItem(row, 3, text_item)
        # 视图处于筛选状态（关键词或分组）时顺序只对子集有意义，关闭拖拽排序
        filtered = bool(keyword.strip()) or group is not None
        self.table.setDragEnabled(not filtered and len(items) > 1)
        self.tip_drag.setVisible(not filtered)
        self.table.setUpdatesEnabled(True)
        self._restore_selection(selected_ids, current_id)
        self._update_buttons()
        # 空状态与统计
        if not items and group is not None and not keyword.strip():
            if group:
                self.empty_hint.setText("分组「%s」还没有短语\n在列表中选中后用右键「移动到分组」放进来" % group)
            else:
                self.empty_hint.setText("所有短语都已分组")
        elif filtered:
            self.empty_hint.setText("没有匹配的短语\n换个关键词或分组试试")
        else:
            self.empty_hint.setText("还没有短语\n点击右上角「新建短语」开始添加")
        self._sync_empty_hint()
        total = len(self.store.phrases)
        enabled = sum(1 for ph in self.store.phrases if ph["enabled"])
        if group is not None:
            self.lbl_page_sub.setText("分组「%s」· 共 %d 条短语" % (group or "未分组", len(items)))
        else:
            self.lbl_page_sub.setText("共 %d 条短语 · %d 条已启用" % (total, enabled))
        self.lbl_stats.setText("共 %d 条 · 启用 %d 条" % (total, enabled))

    def _restore_selection(self, selected_ids, current_id):
        if not selected_ids:
            return
        model = self.table.model()
        self.table.blockSignals(True)
        try:
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item is None:
                    continue
                phrase_id = item.data(Qt.UserRole)
                if phrase_id in selected_ids:
                    self.table.selectionModel().select(
                        model.index(row, 0),
                        QItemSelectionModel.Select | QItemSelectionModel.Rows)
                if phrase_id == current_id:
                    self.table.setCurrentCell(row, 0)
        finally:
            self.table.blockSignals(False)

    def _sync_empty_hint(self):
        show = self.table.rowCount() == 0
        if show:
            vp = self.table.viewport()
            self.empty_hint.resize(vp.size())
            self.empty_hint.move(0, 0)
        self.empty_hint.setVisible(show)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "empty_hint"):
            self._sync_empty_hint()

    def _update_buttons(self):
        phrases = self.selected_phrases()
        has_selection = bool(phrases)
        single = len(phrases) == 1
        self.btn_edit.setEnabled(single)
        self.btn_delete.setEnabled(has_selection)
        self.act_edit.setEnabled(single)
        self.act_delete.setEnabled(has_selection)
        self.act_enable.setEnabled(has_selection)
        self.act_disable.setEnabled(has_selection)

    def _on_section_resized(self, index, old, new):
        if index in (0, 1, 2):
            widths = self._column_widths()
            widths[index] = int(new)
            self.store.settings["columnWidths"] = widths
            QTimer.singleShot(600, self._persist_widths)

    def _column_widths(self):
        """读取列宽；兼容旧版本只保存两列（名称、快捷键）的格式。"""
        widths = list(self.store.settings.get("columnWidths") or [150, 110, 110])
        if len(widths) == 2:
            widths = [widths[0], 110, widths[1]]
        while len(widths) < 3:
            widths.append(110)
        return widths

    def _persist_widths(self):
        try:
            self.store.save()
        except StoreError:
            pass

    def restore_column_widths(self):
        widths = self._column_widths()
        # 恢复列宽会触发 sectionResized，阻断信号避免启动即写盘
        blocker = QSignalBlocker(self.table.horizontalHeader())
        try:
            self.table.setColumnWidth(0, int(widths[0]))
            self.table.setColumnWidth(1, int(widths[1]))
            self.table.setColumnWidth(2, int(widths[2]))
        except (IndexError, TypeError, ValueError):
            pass
        finally:
            blocker.unblock()

    def _current_group(self):
        """None = 全部短语；"" = 只看未分组；其余为具体分组名。"""
        if not hasattr(self, "group_list"):
            return None
        item = self.group_list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return None if value is None else str(value)

    def _sync_group_filter(self):
        """侧栏分组列表随数据变化刷新，同时保留当前选择。"""
        if not hasattr(self, "group_list"):
            return
        current = self._current_group()
        groups = self.store.groups()
        counts = self.store.group_counts()
        selectable = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        self.group_list.blockSignals(True)
        try:
            self.group_list.clear()
            all_item = QListWidgetItem("全部短语 · %d" % len(self.store.phrases))
            all_item.setData(Qt.UserRole, None)
            all_item.setFlags(selectable)
            self.group_list.addItem(all_item)
            for group in groups:
                item = QListWidgetItem("%s · %d" % (group, counts.get(group, 0)))
                item.setData(Qt.UserRole, group)
                self.group_list.addItem(item)
            if counts.get(""):
                item = QListWidgetItem("未分组 · %d" % counts[""])
                item.setData(Qt.UserRole, "")
                item.setFlags(selectable)
                self.group_list.addItem(item)
            match = None
            for row in range(self.group_list.count()):
                candidate = self.group_list.item(row)
                value = candidate.data(Qt.UserRole)
                if (None if value is None else str(value)) == current:
                    match = candidate
                    break
            if match is not None:
                self.group_list.setCurrentItem(match)
            else:
                self.group_list.setCurrentRow(0)
        finally:
            self.group_list.blockSignals(False)

    def select_group(self, group):
        """把侧栏选中项切到指定分组，供新建/重命名后定位使用。"""
        for row in range(self.group_list.count()):
            value = self.group_list.item(row).data(Qt.UserRole)
            if value is not None and str(value) == group:
                self.group_list.setCurrentRow(row)
                return True
        return False

    def _show_group_menu(self, pos):
        item = self.group_list.itemAt(pos)
        value = item.data(Qt.UserRole) if item is not None else None
        group = str(value) if value else ""
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose, True)
        if group:
            menu.addAction("重命名分组…").triggered.connect(
                lambda: self.groupRenameRequested.emit(group))
            menu.addAction("删除分组").triggered.connect(
                lambda: self.groupDeleteRequested.emit(group))
            menu.addSeparator()
        menu.addAction("新建分组…").triggered.connect(lambda: self.groupAddRequested.emit())
        if not group:
            menu.addAction("显示全部短语").triggered.connect(lambda: self.group_list.setCurrentRow(0))
        menu.exec(self.group_list.viewport().mapToGlobal(pos))

    def selected_phrase(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        phrase_id = item.data(Qt.UserRole)
        for phrase in self.store.phrases:
            if phrase["id"] == phrase_id:
                return phrase
        return None

    def selected_phrases(self):
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()})
        result = []
        for row in rows:
            item = self.table.item(row, 0)
            if item is None:
                continue
            phrase_id = item.data(Qt.UserRole)
            phrase = next((p for p in self.store.phrases if p["id"] == phrase_id), None)
            if phrase is not None:
                result.append(phrase)
        return result

    def _show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        self.table.setCurrentCell(row, 0)
        phrases = self.selected_phrases()
        if not phrases:
            return
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose, True)
        act_edit = menu.addAction("修改…")
        act_edit.setEnabled(len(phrases) == 1)
        act_edit.triggered.connect(self.editRequested.emit)
        act_copy = menu.addAction("复制内容")
        act_copy.setEnabled(len(phrases) == 1)
        act_copy.triggered.connect(lambda: self.copyRequested.emit(phrases[0]["id"]))
        menu.addSeparator()
        menu.addAction("启用所选").triggered.connect(lambda: self.enableRequested.emit(True))
        menu.addAction("停用所选").triggered.connect(lambda: self.enableRequested.emit(False))
        menu.addSeparator()
        ids = [ph["id"] for ph in phrases]
        move_menu = menu.addMenu("移动到分组")
        act_none = move_menu.addAction("未分组")
        act_none.triggered.connect(lambda: self.phrasesMoveRequested.emit(ids, ""))
        groups = self.store.groups()
        if groups:
            move_menu.addSeparator()
            for group in groups:
                act = move_menu.addAction(group)
                act.triggered.connect(
                    lambda _checked=False, g=group: self.phrasesMoveRequested.emit(ids, g))
        menu.addSeparator()
        menu.addAction("删除所选").triggered.connect(self.deleteRequested.emit)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def toggle_paused(self, paused):
        self.paused = paused
        self.act_pause.setChecked(paused)
        if hasattr(self, "nav_pause"):
            self.nav_pause.blockSignals(True)
            self.nav_pause.setChecked(paused)
            self.nav_pause.blockSignals(False)
        self.status.showMessage("快捷键已暂停" if paused else "快捷键已恢复")

    def set_panel_checked(self, checked):
        self.act_panel.blockSignals(True)
        self.act_panel.setChecked(checked)
        self.act_panel.blockSignals(False)
        if hasattr(self, "nav_panel"):
            self.nav_panel.blockSignals(True)
            self.nav_panel.setChecked(checked)
            self.nav_panel.blockSignals(False)

    def closeEvent(self, event):
        # 与 3.2 行为一致：关闭主窗口只隐藏，程序继续在托盘运行
        event.ignore()
        self.hide()
