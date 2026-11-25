"""设置 / 选项对话框。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFormLayout, QFrame, QGroupBox, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QScrollArea, QVBoxLayout,
                               QWidget)

from . import theme, winapi as W
from .hotkeyedit import HotkeyEdit


class SettingsDialog(QDialog):
    def __init__(self, store, theme_index=1, parent=None, app_index=None):
        super().__init__(parent)
        self.store = store
        self.settings = dict(store.settings)
        self.app_index = app_index
        self._theme_index = theme_index
        self.setWindowTitle("选项")
        self.setStyleSheet(theme.build_stylesheet(theme_index, "dialog")
                           + theme.build_stylesheet(theme_index, "picker"))
        self.setMinimumWidth(560)
        self.resize(600, 700)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        head = QWidget()
        head_lay = QVBoxLayout(head)
        head_lay.setContentsMargins(24, 20, 24, 10)
        head_lay.setSpacing(3)
        title = QLabel("设置")
        title.setObjectName("dialogTitle")
        subtitle = QLabel("快捷键、输入方式与外观")
        subtitle.setObjectName("dialogSubtitle")
        head_lay.addWidget(title)
        head_lay.addWidget(subtitle)
        outer.addWidget(head)

        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("settingsBody")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 4, 24, 8)
        lay.setSpacing(12)

        # 通用
        box_general = QGroupBox("常规")
        gl = QVBoxLayout(box_general)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(8)
        self.chk_startup = QCheckBox("开机自动启动")
        self.chk_startup.setChecked(bool(self.settings.get("startWithWindows", False)))
        gl.addWidget(self.chk_startup)
        self.chk_tray = QCheckBox("启动时最小化到托盘")
        self.chk_tray.setChecked(bool(self.settings.get("startMinimized", False)))
        gl.addWidget(self.chk_tray)
        form = QFormLayout()
        form.setContentsMargins(0, 6, 0, 0)
        form.setSpacing(9)
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(["经典", "浅色 · 湖青", "深色"])
        ui_theme = int(self.settings.get("uiTheme", 1))
        self.cmb_theme.setCurrentIndex(min(2, max(0, ui_theme)))
        form.addRow("外观", self.cmb_theme)
        self.cmb_input = QComboBox()
        self.cmb_input.addItems(["逐字输入", "剪贴板粘贴", "自动（长文本用粘贴）"])
        self.cmb_input.setCurrentIndex(min(2, max(0, int(self.settings.get("inputMode", 2)))))
        form.addRow("输入方式", self.cmb_input)
        hint_input = QLabel("剪贴板粘贴更快，输入完成后会自动还原原来的剪贴板内容；"
                            "自动模式在文本较长时才使用粘贴。")
        hint_input.setObjectName("hint")
        hint_input.setWordWrap(True)
        form.addRow(hint_input)
        gl.addLayout(form)
        lay.addWidget(box_general)

        # 选择器
        box_picker = QGroupBox("选择器")
        pf = QFormLayout(box_picker)
        pf.setSpacing(9)
        self.ed_picker_key = HotkeyEdit(int(self.settings.get("pickerMods", 0)),
                                        int(self.settings.get("pickerVk", 0)),
                                        allow_empty=False)
        pf.addRow("打开选择器", self.ed_picker_key)
        hint1 = QLabel("按此快捷键，选择器会出现在文本光标旁。点击一行或按回车插入；按 Esc 或再次按快捷键关闭。")
        hint1.setObjectName("hint")
        hint1.setWordWrap(True)
        pf.addRow(hint1)
        self.ed_show_key = HotkeyEdit(int(self.settings.get("showMods", 0)),
                                      int(self.settings.get("showVk", 0)))
        pf.addRow("显示/隐藏主窗口", self.ed_show_key)
        self.chk_recent = QCheckBox("最近使用的排在前面")
        self.chk_recent.setChecked(bool(self.settings.get("pickerRecentFirst", True)))
        pf.addRow("选择器顺序", self.chk_recent)
        lay.addWidget(box_picker)

        # 应用速启
        box_apps = QGroupBox("应用启动")
        af = QFormLayout(box_apps)
        af.setSpacing(9)
        self.ed_launcher_key = HotkeyEdit(int(self.settings.get("launcherMods", 0)),
                                          int(self.settings.get("launcherVk", 0)))
        af.addRow("打开应用速启", self.ed_launcher_key)
        hint_apps = QLabel("按此快捷键弹出搜索栏，输入应用名、英文缩写、拼音首字母或别名后按回车打开；"
                           "单击也能直接打开，右键可置顶、设置别名或隐藏。")
        hint_apps.setObjectName("hint")
        hint_apps.setWordWrap(True)
        af.addRow(hint_apps)
        self.chk_noise = QCheckBox("索引时包含卸载、帮助等系统项")
        self.chk_noise.setChecked(bool(self.settings.get("launcherIncludeNoise", False)))
        af.addRow("索引范围", self.chk_noise)
        row_apps = QHBoxLayout()
        self.btn_rebuild = QPushButton("重建索引")
        self.btn_rebuild.setAutoDefault(False)
        self.btn_rebuild.clicked.connect(self._rebuild_index)
        row_apps.addWidget(self.btn_rebuild)
        self.btn_hidden = QPushButton("管理隐藏应用")
        self.btn_hidden.setAutoDefault(False)
        self.btn_hidden.clicked.connect(self._manage_hidden)
        row_apps.addWidget(self.btn_hidden)
        row_apps.addStretch(1)
        af.addRow("应用清单", row_apps)
        lay.addWidget(box_apps)
        lay.addStretch(1)

        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        footer = QWidget()
        footer.setObjectName("settingsFooter")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 10, 24, 16)
        buttons = QDialogButtonBox()
        self.btn_ok = QPushButton("确定")
        self.btn_ok.setObjectName("primary")
        self.btn_ok.setDefault(True)
        self.btn_cancel = QPushButton("取消")
        buttons.addButton(self.btn_ok, QDialogButtonBox.AcceptRole)
        buttons.addButton(self.btn_cancel, QDialogButtonBox.RejectRole)
        self.btn_ok.clicked.connect(self._accept)
        self.btn_cancel.clicked.connect(self.reject)
        fl.addWidget(buttons)
        outer.addWidget(footer)

    def _rebuild_index(self):
        if self.app_index is None:
            QMessageBox.information(self, "应用启动", "应用索引暂不可用。")
            return
        self.app_index.start_scan(self.chk_noise.isChecked())
        QMessageBox.information(self, "应用启动", "已在后台重建应用索引，完成后重新打开速启即可看到结果。")

    def _manage_hidden(self):
        if self.app_index is None:
            QMessageBox.information(self, "应用启动", "应用索引暂不可用。")
            return
        from .launcher import HiddenAppsDialog
        HiddenAppsDialog(self.app_index, self._theme_index, self).exec()

    def _accept(self):
        pm, pv = self.ed_picker_key.hotkey()
        sm, sv = self.ed_show_key.hotkey()
        lm, lv = self.ed_launcher_key.hotkey()
        if not pv:
            QMessageBox.warning(self, "选项", "请为“打开选择器”设置快捷键。")
            self.ed_picker_key.setFocus()
            return
        pairs = [(pm, pv, "打开选择器", self.ed_picker_key),
                 (sm, sv, "显示/隐藏主窗口", self.ed_show_key),
                 (lm, lv, "打开应用速启", self.ed_launcher_key)]
        for i in range(len(pairs)):
            for j in range(i + 1, len(pairs)):
                if pairs[i][1] and pairs[j][1] and pairs[i][0] == pairs[j][0] \
                        and pairs[i][1] == pairs[j][1]:
                    pairs[j][3].setFocus()
                    QMessageBox.warning(self, "选项", "各命令的快捷键不能相同。")
                    return
        self.settings["pickerMods"] = pm
        self.settings["pickerVk"] = pv
        self.settings["showMods"] = sm
        self.settings["showVk"] = sv
        self.settings["launcherMods"] = lm
        self.settings["launcherVk"] = lv
        self.settings["launcherIncludeNoise"] = self.chk_noise.isChecked()
        self.settings["pickerRecentFirst"] = self.chk_recent.isChecked()
        self.settings["startWithWindows"] = self.chk_startup.isChecked()
        self.settings["startMinimized"] = self.chk_tray.isChecked()
        self.settings["uiTheme"] = self.cmb_theme.currentIndex()
        self.settings["inputMode"] = self.cmb_input.currentIndex()
        self.accept()
