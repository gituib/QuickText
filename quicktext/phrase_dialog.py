"""添加 / 修改短语对话框。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QFrame,
                               QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
                               QPushButton, QVBoxLayout)

from . import theme
from .hotkeyedit import HotkeyEdit
from .store import new_phrase

MAX_TEXT = 100000

# 全局命令热键（存于 store.settings），与短语热键互斥
_GLOBAL_HOTKEYS = (("pickerMods", "pickerVk", "打开选择器"),
                   ("showMods", "showVk", "显示/隐藏主窗口"),
                   ("launcherMods", "launcherVk", "打开应用速启"))

# palette 不可用时的兜底配色（浅色·湖青）
_FALLBACK_PALETTE = {
    "text": "#0F172A", "muted_text": "#64748B", "danger": "#DC2626",
    "primary": "#0D9488",
}


def _palette(index: int) -> dict:
    try:
        fn = getattr(theme, "palette", None)
        if fn is not None:
            c = fn(index)
            if isinstance(c, dict) and "text" in c and "danger" in c:
                return c
    except Exception:
        pass
    return dict(_FALLBACK_PALETTE)


class PhraseDialog(QDialog):
    def __init__(self, store, phrase=None, parent=None, theme_index=1):
        super().__init__(parent)
        self.store = store
        self.editing = phrase
        self.setWindowTitle("修改短语" if phrase else "添加短语")
        self.setStyleSheet(theme.build_stylesheet(theme_index, "dialog"))
        self.setMinimumWidth(560)
        self.setMinimumHeight(560)
        self.resize(620, 760)
        c = _palette(theme_index)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(10)

        # 标题区：统一由 dialogTitle 提供大字号标题，theme 未覆盖时用控件级兜底
        self.lbl_title = QLabel("修改短语" if phrase else "添加短语")
        self.lbl_title.setObjectName("dialogTitle")
        if "dialogTitle" not in self.styleSheet():
            self.lbl_title.setStyleSheet(
                "QLabel#dialogTitle { color: %s; font-size: 16px; font-weight: 700;"
                " background: transparent; }" % c.get("text", "#0F172A"))
        layout.addWidget(self.lbl_title)

        subtitle = QLabel("设置名称与快捷键；不设快捷键时，可通过选择器弹出使用。缩写可让选择器里一次命中。")
        subtitle.setObjectName("hint")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("formCard")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(16, 14, 16, 12)
        card_lay.setSpacing(8)

        form = QFormLayout()
        form.setSpacing(10)
        form.setHorizontalSpacing(14)
        self.ed_name = QLineEdit(phrase["name"] if phrase else "")
        self.ed_name.setPlaceholderText("可留空")
        self.ed_name.setFixedHeight(34)
        form.addRow("名称", self.ed_name)

        self.ed_alias = QLineEdit(phrase.get("alias") or "" if phrase else "")
        self.ed_alias.setPlaceholderText("可选，例如 wx；在选择器里输入即可命中")
        self.ed_alias.setFixedHeight(34)
        form.addRow("缩写", self.ed_alias)

        self.ed_group = QComboBox()
        self.ed_group.setEditable(True)
        self.ed_group.setFixedHeight(34)
        self.ed_group.addItem("未分组", "")
        for group in self.store.groups():
            self.ed_group.addItem(group)
        group = (phrase.get("group") or "") if phrase else ""
        if group:
            self.ed_group.setCurrentText(group)
        else:
            self.ed_group.setCurrentIndex(0)
        if self.ed_group.lineEdit() is not None:
            self.ed_group.lineEdit().setPlaceholderText("可选，例如 工作 / 客服")
        form.addRow("分组", self.ed_group)

        self.ed_key = HotkeyEdit(phrase["hotkeyMods"] if phrase else 0,
                                 phrase["hotkeyVk"] if phrase else 0)
        form.addRow("快捷键", self.ed_key)
        card_lay.addLayout(form)

        hint = QLabel("按下一个字母、数字或任意按键即可快速输入该短语，可加 Ctrl、Alt 或 Shift。留空则使用选择器。")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        card_lay.addWidget(hint)
        layout.addWidget(card)

        lbl_text = QLabel("内容")
        lbl_text.setObjectName("sectionLabel")
        layout.addWidget(lbl_text)
        self.ed_text = QPlainTextEdit(phrase["text"] if phrase else "")
        self.ed_text.setObjectName("phraseTextEdit")
        self.ed_text.setPlaceholderText("输入要自动输入的文字。可以是一行，也可以是多行；按回车换行，空行会被保留。")
        self.ed_text.setTabChangesFocus(False)
        self.ed_text.setMinimumHeight(200)
        layout.addWidget(self.ed_text, 1)

        tip = QLabel("支持动态内容：{date}、{time}、{datetime}、{clipboard}、{uuid}；"
                     "宏：{wait:500}、{key:Tab}、{ctrl+enter}。需要原样花括号时写 {{ 或 }}。")
        tip.setObjectName("hint")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        self.chk_enabled = QCheckBox("启用此短语")
        self.chk_enabled.setChecked(phrase["enabled"] if phrase else True)
        layout.addWidget(self.chk_enabled)

        # 错误提示：空时隐藏，节省空间
        self.lbl_error = QLabel("")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setStyleSheet(
            "QLabel { color: %s; background: transparent; }" % c.get("danger", "#DC2626"))
        self.lbl_error.setVisible(False)
        layout.addWidget(self.lbl_error)

        rows = QHBoxLayout()
        rows.setSpacing(10)
        rows.addStretch(1)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setMinimumHeight(34)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok = QPushButton("确定")
        self.btn_ok.setObjectName("primary")
        self.btn_ok.setDefault(True)
        self.btn_ok.setMinimumSize(96, 34)
        self.btn_ok.clicked.connect(self._on_accept)
        rows.addWidget(self.btn_cancel)
        rows.addWidget(self.btn_ok)
        layout.addLayout(rows)

        self.ed_name.textChanged.connect(self._hide_error)
        self.ed_text.textChanged.connect(self._hide_error)
        self.ed_group.currentTextChanged.connect(self._hide_error)
        self.ed_key.hotkeyChanged.connect(self._hide_error)

        if phrase is None:
            self.ed_name.setFocus()

    def _hide_error(self, *_args):
        self.lbl_error.setVisible(False)

    def _group_value(self):
        """首项「未分组」对应的值是空串，其余取当前文本。"""
        if self.ed_group.currentIndex() == 0:
            return str(self.ed_group.itemData(0) or "")
        return self.ed_group.currentText().strip()

    def _conflicting_global_hotkey(self, mods, vk):
        settings = self.store.settings or {}
        for mods_key, vk_key, label in _GLOBAL_HOTKEYS:
            if int(settings.get(vk_key) or 0) != vk:
                continue
            if int(settings.get(mods_key) or 0) & 0x0F == mods & 0x0F:
                return label
        return None

    def _set_error(self, message):
        self.lbl_error.setText(message)
        self.lbl_error.setVisible(True)

    def _on_accept(self):
        self.lbl_error.setVisible(False)
        text = self.ed_text.toPlainText()
        if not text.strip():
            self._set_error("请输入要输入的文字。")
            self.ed_text.setFocus()
            return
        if len(text) > MAX_TEXT:
            self._set_error("文字太长，请保持在 100,000 个字符以内。")
            return
        mods, vk = self.ed_key.hotkey()
        exclude = self.editing["id"] if self.editing else None
        if vk:
            owner = self.store.hotkey_owner(mods, vk, exclude_id=exclude)
            if owner is not None:
                self._set_error("该快捷键已被其他短语使用。")
                return
            label = self._conflicting_global_hotkey(mods, vk)
            if label:
                self._set_error("该快捷键与全局「%s」热键冲突，请换一个。" % label)
                self.ed_key.setFocus()
                return
        existing = self.store.find_by_text(text)
        if existing is not None and (not self.editing or existing["id"] != self.editing["id"]):
            self._set_error("列表中已有相同内容的短语，不允许重复。")
            return
        self.accept()

    def result_phrase(self):
        mods, vk = self.ed_key.hotkey()
        base = self.editing or new_phrase()
        phrase = dict(base)
        phrase["name"] = self.ed_name.text().strip()
        phrase["alias"] = self.ed_alias.text().strip()
        phrase["group"] = self._group_value()
        phrase["hotkeyMods"] = mods
        phrase["hotkeyVk"] = vk
        phrase["text"] = self.ed_text.toPlainText()
        phrase["enabled"] = self.chk_enabled.isChecked()
        return phrase
