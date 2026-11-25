"""应用控制器：托盘、全局热键、选择器、悬浮面板与各对话框的协作。"""
import ctypes
import json
import os
import sys
import time

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, QTimer, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtNetwork import QLocalServer
from PySide6.QtWidgets import (QApplication, QFileDialog, QInputDialog, QMenu, QMessageBox,
                               QSystemTrayIcon)

from . import inputsim, theme, tokens, winapi as W
from .appindex import AppIndex
from .floating import FloatingPanel
from .launcher import LauncherDialog
from .mainwindow import MainWindow
from .phrase_dialog import PhraseDialog
from .picker import PickerDialog
from .settings_dialog import SettingsDialog
from .store import PhraseStore, StoreError

WM_HOTKEY = 0x0312
HK_PHRASE_BASE = 1000
HK_PICKER = 1
HK_SHOW = 2
HK_LAUNCHER = 3
IPC_NAME = "QuickText.IPC"


class HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    def nativeEventFilter(self, event_type, message):
        if event_type in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            msg = W._MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                self.controller.on_hotkey(int(msg.wParam))
                return True, 0
        return False, 0


class AppController(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.store = PhraseStore()
        self.theme_index = int(self.store.settings.get("uiTheme", 1))
        self._applied_theme = self.theme_index
        self.paused = False
        self.hwnd = None
        self._registered = {}
        self._picker = None
        self._launcher = None
        self._typing = False
        self._last_foreign_hwnd = 0
        self._self_pids = {os.getpid(), os.getppid()}
        self._floating = None

        icon = QIcon(W.app_icon_path()) if W.app_icon_path() else QIcon()
        self.window = MainWindow(self.store)
        self.window.restore_column_widths()
        if not icon.isNull():
            self.window.setWindowIcon(icon)
        self.app_index = AppIndex()

        self._build_tray(icon)
        self._build_ipc()
        self._wire()

        # 持续记录“最近一个属于其它程序的前台窗口”：面板被点击后会自己抢到前台，
        # 那时再取前台窗口已经来不及，所以必须提前留档。
        self._tracker = QTimer(self)
        self._tracker.setInterval(300)
        self._tracker.timeout.connect(self._track_foreground)
        self._tracker.start()

        self.hotkey_filter = HotkeyFilter(self)
        app.installNativeEventFilter(self.hotkey_filter)
        QTimer.singleShot(0, self._after_start)

    # ------------------------------------------------------------- startup
    def _after_start(self):
        self.hwnd = int(self.window.winId())
        self.apply_start_with_windows()
        self.reload_hotkeys()
        self.refresh_theme()
        self.app_index.set_include_noise(
            bool(self.store.settings.get("launcherIncludeNoise", False)))
        if self.app_index.needs_scan():
            self.app_index.start_scan(bool(self.store.settings.get("launcherIncludeNoise", False)))
        if self.store.recovered_from_backup:
            QTimer.singleShot(300, lambda: self.notify("数据文件损坏，已从自动备份恢复。"))
        if self.store.migrated_to_encrypted:
            QTimer.singleShot(300, lambda: self.notify(
                "本机数据文件已按当前 Windows 账户加密；「导出」生成的备份仍是明文，可在其它电脑导入。"))
        if self.store.data_quarantined:
            kept = "、".join(os.path.basename(p) for p in self.store.data_quarantined)
            QTimer.singleShot(300, lambda: self.notify(
                "数据无法解密（可能更换了 Windows 账户），已原样保留为 " + kept + "，本次以空列表启动。", 8000))
        if bool(self.store.settings.get("showFloatingPanel", False)):
            self.floating.show()
            self.window.set_panel_checked(True)
        if not bool(self.store.settings.get("startMinimized", False)):
            self.show_main()

    def _build_tray(self, icon):
        self.tray = QSystemTrayIcon(icon if not icon.isNull() else QIcon(), self.app)
        menu = QMenu()
        act_show = QAction("显示主窗口", menu)
        act_show.triggered.connect(self.show_main)
        menu.addAction(act_show)
        menu.addSeparator()
        act_panel = QAction("悬浮面板", menu, checkable=True)
        act_panel.setChecked(bool(self.store.settings.get("showFloatingPanel", False)))
        act_panel.triggered.connect(self.toggle_panel)
        menu.addAction(act_panel)
        act_launcher = QAction("应用速启", menu)
        act_launcher.triggered.connect(self.toggle_launcher)
        menu.addAction(act_launcher)
        act_pause = QAction("暂停快捷键", menu, checkable=True)
        act_pause.triggered.connect(self.set_paused)
        menu.addAction(act_pause)
        menu.addSeparator()
        act_quit = QAction("退出", menu)
        act_quit.triggered.connect(self.quit)
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray_menu = menu
        self.tray.setToolTip(W.APP_TITLE)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()
        self.tray_actions = (act_panel, act_pause)

    def _build_ipc(self):
        """监听第二实例的唤醒请求，避免双开抢热键、互相覆盖数据。"""
        self._ipc = QLocalServer(self)
        QLocalServer.removeServer(IPC_NAME)
        self._ipc.newConnection.connect(self._on_ipc_connection)
        self._ipc.listen(IPC_NAME)

    def _on_ipc_connection(self):
        while self._ipc.hasPendingConnections():
            conn = self._ipc.nextPendingConnection()
            conn.readAll()
            conn.disconnectFromServer()
            conn.deleteLater()
        self.show_main()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_main()

    def _wire(self):
        w = self.window
        w.addRequested.connect(self.add_phrase)
        w.editRequested.connect(self.edit_phrase)
        w.deleteRequested.connect(self.delete_phrase)
        w.importRequested.connect(self.import_phrases)
        w.exportRequested.connect(self.export_phrases)
        w.settingsRequested.connect(self.open_settings)
        w.optionsRequested.connect(self.open_settings)
        w.pauseRequested.connect(lambda: self.set_paused(not self.paused))
        w.floatingPanelRequested.connect(self.toggle_panel)
        w.launcherRequested.connect(self.toggle_launcher)
        w.quitRequested.connect(self.quit)
        w.enableRequested.connect(self.set_selected_enabled)
        w.copyRequested.connect(self.copy_phrase_by_id)
        w.reorderRequested.connect(self.reorder_phrases)
        w.groupAddRequested.connect(self.add_group)
        w.groupRenameRequested.connect(self.rename_group)
        w.groupDeleteRequested.connect(self.delete_group)
        w.groupOrderRequested.connect(self.save_group_order)
        w.phrasesMoveRequested.connect(self.move_phrases_to_group)
        w.privacyChanged.connect(self._on_privacy_changed)
        self.app_index.scan_finished.connect(self._on_scan_finished)

    def _on_privacy_changed(self, _hidden):
        """主窗口切换遮挡时，已创建的悬浮面板需要重绘正文。"""
        if self._floating is not None:
            self._floating.reload_phrases()

    @property
    def floating(self):
        """悬浮面板按需创建：默认不显示时不必在启动阶段构建整套控件。"""
        if self._floating is None:
            self._floating = FloatingPanel(self.store, self.theme_index)
            f = self._floating
            f.typeRequested.connect(self.type_phrase_from_panel)
            f.copyRequested.connect(self.copy_phrase_by_id)
            f.editRequested.connect(self.edit_phrase_by_id)
            f.toggleRequested.connect(self.toggle_phrase_by_id)
            f.deleteRequested.connect(self.delete_phrase_by_id)
            f.pausedChanged.connect(self._on_panel_pause)
            f.settingsChanged.connect(self.window.refresh)
        return self._floating

    # -------------------------------------------------------------- window
    def show_main(self):
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()
        self.window.refresh()

    def quit(self):
        self.unregister_all()
        self.store.flush()
        self.app_index.stop()
        if getattr(self, "_ipc", None) is not None:
            self._ipc.close()
        self.tray.hide()
        self.app.quit()

    # ------------------------------------------------------------- hotkeys
    def unregister_all(self):
        for hk_id in list(self._registered):
            try:
                inputsim.user32.UnregisterHotKey(ctypes.c_void_p(self.hwnd), hk_id)
            except Exception:
                pass
        self._registered.clear()

    def _register(self, hk_id, mods, vk):
        if not vk or not self.hwnd:
            return True
        ok = bool(inputsim.user32.RegisterHotKey(ctypes.c_void_p(self.hwnd),
                                                 hk_id, W.modifiers_of(mods) | 0x4000, vk))
        if ok:
            self._registered[hk_id] = (mods, vk)
        return ok

    def reload_hotkeys(self):
        self.unregister_all()
        failed = []
        s = self.store.settings
        if not self._register(HK_PICKER, int(s.get("pickerMods", 0)), int(s.get("pickerVk", 0))):
            failed.append(("打开选择器", int(s.get("pickerMods", 0)), int(s.get("pickerVk", 0))))
        if not self._register(HK_SHOW, int(s.get("showMods", 0)), int(s.get("showVk", 0))):
            failed.append(("显示/隐藏主窗口", int(s.get("showMods", 0)), int(s.get("showVk", 0))))
        if not self._register(HK_LAUNCHER, int(s.get("launcherMods", 0)),
                              int(s.get("launcherVk", 0))):
            failed.append(("应用速启", int(s.get("launcherMods", 0)),
                           int(s.get("launcherVk", 0))))
        self._phrase_ids = {}
        for i, phrase in enumerate(self.store.phrases):
            if not phrase["enabled"] or not phrase["hotkeyVk"]:
                continue
            hk_id = HK_PHRASE_BASE + i
            if self._register(hk_id, phrase["hotkeyMods"], phrase["hotkeyVk"]):
                self._phrase_ids[hk_id] = phrase["id"]
            else:
                failed.append((phrase["name"] or phrase["text"][:12], phrase["hotkeyMods"],
                               phrase["hotkeyVk"]))
        self.window.status.showMessage("就绪" if not failed else "部分快捷键注册失败")
        return failed

    def on_hotkey(self, hk_id):
        if hk_id == HK_PICKER:
            self.show_picker()
            return
        if hk_id == HK_SHOW:
            if self.window.isVisible() and self.window.isActiveWindow():
                self.window.hide()
            else:
                self.show_main()
            return
        if hk_id == HK_LAUNCHER:
            self.toggle_launcher()
            return
        phrase_id = getattr(self, "_phrase_ids", {}).get(hk_id)
        if phrase_id:
            self.type_phrase_by_id(phrase_id)

    # ------------------------------------------------------------- typing
    def type_phrase_by_id(self, phrase_id):
        if self.paused or self._typing:
            return
        phrase = next((p for p in self.store.phrases if p["id"] == phrase_id), None)
        if phrase is None or not phrase["enabled"]:
            return
        self._do_type(phrase["text"], phrase["hotkeyMods"])
        self.store.touch(phrase_id)
        self.window.refresh()

    def _do_type(self, text, mods=0, hwnd=0):
        segments = tokens.parse_actions(text)
        plain = "".join(seg[1] for seg in segments if seg[0] == "text")
        if len(plain) > 100000:
            self.notify("文字太长，请保持在 100,000 个字符以内。")
            return
        self._typing = True
        try:
            QApplication.processEvents()
            if hwnd:
                inputsim.restore_window(hwnd)
                time.sleep(0.12)
            typer = inputsim.Typer(int(mods))
            if len(segments) == 1 and segments[0][0] == "text":
                typer.type_text(segments[0][1], paste=self._wants_paste(plain))
            else:
                self._run_segments(typer, segments)
        finally:
            self._typing = False

    def _run_segments(self, typer, segments):
        """按顺序执行文本、等待与按键，支持 {wait:500}、{key:Tab} 这类宏。"""
        for seg in segments:
            if seg[0] == "text":
                if seg[1]:
                    typer.type_text(seg[1], paste=self._wants_paste(seg[1]))
            elif seg[0] == "wait":
                time.sleep(seg[1] / 1000.0)
            elif seg[0] == "key":
                typer.run_commands([(seg[1], seg[2])])

    def _wants_paste(self, text):
        mode = int(self.store.settings.get("inputMode", 2))
        if mode == 1:
            return True
        if mode == 0:
            return False
        if len(text) <= inputsim.PASTE_THRESHOLD:
            return False
        # 自动模式：剪贴板里有图片/文件时不覆盖，退回逐字输入
        return not inputsim.clipboard_has_rich_content()

    def copy_phrase_by_id(self, phrase_id):
        phrase = next((p for p in self.store.phrases if p["id"] == phrase_id), None)
        if phrase is None:
            return
        if inputsim.clipboard_set_text(tokens.plain_text(phrase["text"])):
            self.notify("已复制到剪贴板。")
            self.store.touch(phrase_id)

    def show_picker(self):
        if self.paused:
            return
        if self._picker is not None and self._picker.isVisible():
            self._picker.close()
            self._picker = None
            return
        self._target_hwnd = self._foreign_foreground()
        anchor = inputsim.caret_screen_rect()
        picker = PickerDialog(self.store, self.theme_index, anchor)
        picker.picked.connect(lambda text: self._on_pick(text))
        picker.finished.connect(self._on_picker_closed)
        self._picker = picker
        picker.show_at()

    def _on_scan_finished(self, added, removed, total):
        self.window.status.showMessage(
            "应用索引已更新：新增 %d、移除 %d，共 %d 个" % (added, removed, total), 6000)

    def toggle_launcher(self):
        """唤起/关闭应用速启；首次打开时把焦点还给唤起前的窗口。"""
        if self.paused:
            return
        if self._launcher is not None:
            self._launcher.close()
            return
        self._target_hwnd = self._foreign_foreground()
        include_noise = bool(self.store.settings.get("launcherIncludeNoise", False))
        self.app_index.set_include_noise(include_noise)
        if self.app_index.needs_scan():
            # 后台重扫，本次仍用已有缓存，避免开窗卡顿
            self.app_index.start_scan(include_noise)
        dialog = LauncherDialog(self.app_index, self.theme_index)
        dialog.finished.connect(self._on_launcher_closed)
        self._launcher = dialog
        dialog.show_launcher()

    def _on_launcher_closed(self, _result):
        dialog = self._launcher
        self._launcher = None
        launched = bool(dialog is not None and dialog.launched_app)
        restore = bool(dialog is not None and dialog.restore_focus)
        if dialog is not None:
            dialog.deleteLater()
        hwnd = getattr(self, "_target_hwnd", 0)
        if not launched and restore and hwnd:
            QTimer.singleShot(40, lambda: inputsim.restore_window(hwnd))

    def _foreign_foreground(self):
        try:
            return inputsim.last_tracked_foreign_window(self._self_pids)
        except Exception:
            return 0

    def _track_foreground(self):
        hwnd = self._foreign_foreground()
        if hwnd:
            self._last_foreign_hwnd = hwnd

    def _on_picker_closed(self, _result):
        self._picker = None
        hwnd = getattr(self, "_target_hwnd", 0)
        if hwnd:
            QTimer.singleShot(60, lambda: inputsim.restore_window(hwnd))

    def _on_pick(self, text):
        mods = int(self.store.settings.get("pickerMods", 0))
        hwnd = getattr(self, "_target_hwnd", 0)
        QTimer.singleShot(160, lambda: self._do_type(text, mods, hwnd))

    def type_phrase_from_panel(self, phrase_id):
        """面板点击“输入”：先把焦点还给进入面板之前的那个窗口再输入。"""
        hwnd = self._last_foreign_hwnd or self._foreign_foreground()
        if hwnd and inputsim.restore_window(hwnd):
            QTimer.singleShot(140, lambda: self.type_phrase_by_id(phrase_id))
        else:
            self.type_phrase_by_id(phrase_id)

    # --------------------------------------------------------------- menus
    def _refresh_all(self):
        self.window.refresh()
        if self._floating is not None:
            self._floating.reload_phrases()

    def _phrase_by_id(self, phrase_id):
        return next((p for p in self.store.phrases if p["id"] == phrase_id), None)

    def _exec_modal(self, dialog):
        """以主窗口为父的模态对话框会被置顶面板盖住，弹出期间临时取消置顶。"""
        panel = self._floating
        if panel is not None:
            panel.set_always_on_top(False)
        try:
            return dialog.exec()
        finally:
            if panel is not None:
                panel.set_always_on_top(True)

    def add_phrase(self):
        dialog = PhraseDialog(self.store, None, self.window, self.theme_index)
        if self._exec_modal(dialog) == PhraseDialog.Accepted:
            phrase = dialog.result_phrase()
            try:
                self.store.add(phrase)
            except StoreError as exc:
                QMessageBox.warning(self.window, "添加短语", str(exc))
            self._refresh_all()
            self._report_hotkey_failures()

    def edit_phrase(self):
        current = self.window.selected_phrase()
        if current is None:
            self.notify("请先选择一个短语。")
            return
        self._edit_phrase(current)

    def edit_phrase_by_id(self, phrase_id):
        phrase = self._phrase_by_id(phrase_id)
        if phrase is not None:
            self._edit_phrase(phrase)

    def _edit_phrase(self, current):
        dialog = PhraseDialog(self.store, current, self.window, self.theme_index)
        if self._exec_modal(dialog) == PhraseDialog.Accepted:
            phrase = dialog.result_phrase()
            self.store.replace(current["id"], phrase)
            self._refresh_all()
            self._report_hotkey_failures()

    def delete_phrase(self):
        phrases = self.window.selected_phrases()
        if not phrases:
            self.notify("请先选择一个短语。")
            return
        self._delete_phrases(phrases)

    def delete_phrase_by_id(self, phrase_id):
        phrase = self._phrase_by_id(phrase_id)
        if phrase is not None:
            self._delete_phrases([phrase])

    def _delete_phrases(self, phrases):
        if len(phrases) == 1:
            name = phrases[0]["name"] or phrases[0]["text"][:16]
            question = '确定要删除“%s”吗？' % name
        else:
            question = "确定要删除所选的 %d 条短语吗？" % len(phrases)
        if QMessageBox.question(self.window, "删除", question) != QMessageBox.Yes:
            return
        self.store.remove_many([p["id"] for p in phrases])
        self._refresh_all()
        self.reload_hotkeys()

    def set_selected_enabled(self, enabled):
        ids = [p["id"] for p in self.window.selected_phrases()]
        if not ids:
            self.notify("请先选择短语。")
            return
        if self.store.set_enabled(ids, enabled):
            self._refresh_all()
            self.reload_hotkeys()

    def toggle_phrase_by_id(self, phrase_id):
        phrase = self._phrase_by_id(phrase_id)
        if phrase is None:
            return
        if self.store.set_enabled([phrase_id], not phrase["enabled"]):
            self._refresh_all()
            self.reload_hotkeys()

    def reorder_phrases(self, ids):
        if self.store.reorder(ids):
            self._refresh_all()
            self.reload_hotkeys()

    # --------------------------------------------------------------- groups
    def add_group(self):
        name, ok = QInputDialog.getText(self.window, "新建分组", "分组名称：")
        if not ok:
            return
        value, error = self.store.add_group(name)
        if error:
            QMessageBox.warning(self.window, "新建分组", error)
            return
        self._refresh_all()
        self.window.select_group(value)
        self.window.status.showMessage("已新建分组「%s」，现在还是空的" % value, 5000)

    def rename_group(self, old):
        name, ok = QInputDialog.getText(self.window, "重命名分组", "新的分组名称：", text=old)
        if not ok:
            return
        value, moved, error = self.store.rename_group(old, name)
        if error:
            QMessageBox.warning(self.window, "重命名分组", error)
            return
        self._refresh_all()
        self.window.select_group(value)
        self.window.status.showMessage("分组已重命名为「%s」，%d 条短语同步更新" % (value, moved), 5000)

    def delete_group(self, name):
        count = self.store.group_counts().get(name, 0)
        if count:
            question = "分组「%s」下有 %d 条短语，删除后这些短语会变成未分组。\n确定删除该分组吗？" % (name, count)
        else:
            question = "确定删除空分组「%s」吗？" % name
        if QMessageBox.question(self.window, "删除分组", question) != QMessageBox.Yes:
            return
        dropped, error = self.store.delete_group(name)
        if error:
            self.notify(error)
            return
        self._refresh_all()
        self.window.status.showMessage("已删除分组「%s」" % name, 5000)

    def save_group_order(self, names):
        self.store.set_group_order(names)
        self._refresh_all()

    def move_phrases_to_group(self, ids, group):
        changed = self.store.move_to_group(ids, group)
        if not changed:
            return
        self._refresh_all()
        self.window.status.showMessage(
            "已把 %d 条短语移动到「%s」" % (changed, group or "未分组"), 5000)

    def _report_hotkey_failures(self):
        failed = self.reload_hotkeys()
        if failed:
            lines = ["%s（%s）" % (name, W.hotkey_text(mods, vk)) for name, mods, vk in failed]
            QMessageBox.warning(self.window, "快捷键",
                                "以下快捷键被其他程序占用或无效：\n" + "\n".join(lines))

    # ------------------------------------------------------- import/export
    def import_phrases(self):
        path, _ = QFileDialog.getOpenFileName(self.window, "导入短语", "",
                                               "短语备份 (*.json);;所有文件 (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            QMessageBox.warning(self.window, "导入", "无法读取该文件。")
            return
        added, dup, bad = self.store.import_payload(data)
        self._refresh_all()
        self._report_hotkey_failures()
        messages = []
        if added:
            messages.append("已导入 %d 条短语。" % len(added))
        else:
            messages.append("没有新的短语被导入。")
        if dup:
            # 只报数量，不把用户正文回显到屏幕上
            messages.append("已跳过 %d 条重复内容（正文与已有短语相同）。" % len(dup))
        if bad:
            messages.append("有 %d 条记录格式不正确，已忽略。" % bad)
        QMessageBox.information(self.window, "导入", "\n\n".join(messages))

    def export_phrases(self):
        question = ("导出的备份文件会以明文保存全部短语正文，其中可能包含个人信息。\n"
                    "请把文件存放在只有你能访问的位置。\n\n是否继续导出？")
        if QMessageBox.question(self.window, "导出短语", question) != QMessageBox.Yes:
            return
        path, _ = QFileDialog.getSaveFileName(self.window, "导出短语", "backup.json",
                                               "短语备份 (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.store.export_payload(), fh, ensure_ascii=False, indent=4)
        except OSError:
            QMessageBox.warning(self.window, "导出", "无法写入该文件。")
            return
        self.notify("短语已导出。")

    # ------------------------------------------------------------ settings
    def open_settings(self):
        old_noise = bool(self.store.settings.get("launcherIncludeNoise", False))
        dialog = SettingsDialog(self.store, self.theme_index, self.window, self.app_index)
        if self._exec_modal(dialog) != SettingsDialog.Accepted:
            return
        self.store.settings.update(dialog.settings)
        try:
            self.store.save()
        except StoreError:
            pass
        include_noise = bool(self.store.settings.get("launcherIncludeNoise", False))
        self.app_index.set_include_noise(include_noise)
        if include_noise != old_noise:
            self.app_index.rebuild()
        self.apply_start_with_windows()
        self._report_hotkey_failures()
        self.refresh_theme()

    def apply_start_with_windows(self):
        import winreg
        enabled = bool(self.store.settings.get("startWithWindows", False))
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                                 winreg.KEY_SET_VALUE)
        except OSError:
            return
        try:
            if enabled:
                exe = sys.executable if getattr(sys, "frozen", False) else self._script_path()
                winreg.SetValueEx(key, W.APP_NAME, 0, winreg.REG_SZ, '"%s"' % exe)
            else:
                try:
                    winreg.DeleteValue(key, W.APP_NAME)
                except FileNotFoundError:
                    pass
        finally:
            key.Close()

    def _script_path(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, "main.py")

    def refresh_theme(self):
        self.theme_index = int(self.store.settings.get("uiTheme", 1))
        changed = self.theme_index != self._applied_theme
        self._applied_theme = self.theme_index
        if changed:
            # 主题未变时不重建主窗口列表，避免启动和保存设置时重复全表刷新
            self.window.apply_theme()
            self._restyle_open_dialogs()
        self.tray_menu.setStyleSheet(theme.build_stylesheet(self.theme_index, "dialog"))
        if self._floating is not None:
            self._floating.set_theme(self.theme_index)
            self._floating.apply_settings()
            self._floating.reload_phrases()

    def _restyle_open_dialogs(self):
        """对话框在构造时一次性套用样式，切主题需给已打开的实例重新下发。"""
        idx = self.theme_index
        dialog_qss = theme.build_stylesheet(idx, "dialog")
        picker_qss = theme.build_stylesheet(idx, "picker")
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, PhraseDialog):
                widget.setStyleSheet(dialog_qss)
            elif isinstance(widget, SettingsDialog):
                widget.setStyleSheet(dialog_qss + picker_qss)
            elif isinstance(widget, PickerDialog):
                widget.setStyleSheet(dialog_qss + picker_qss + theme.card_stylesheet(idx))

    # --------------------------------------------------------------- panel
    def toggle_panel(self, checked=None):
        visible = self.floating.isVisible()
        if checked is None:
            checked = not visible
        # 先落设置，面板 hideEvent 的兜底写入就不会重复保存一次
        self.store.settings["showFloatingPanel"] = bool(checked)
        if checked:
            self.floating.apply_settings()
            self.floating.reload_phrases()
            self.floating.show()
            self.floating.raise_()
        else:
            self.floating.hide()
        try:
            self.store.save()
        except StoreError:
            pass
        self.window.set_panel_checked(bool(checked))
        self.tray_actions[0].setChecked(bool(checked))

    def _on_panel_pause(self, paused):
        self.set_paused(paused, from_panel=True)

    def set_paused(self, paused, from_panel=False):
        self.paused = bool(paused)
        self.window.toggle_paused(self.paused)
        self.tray_actions[1].setChecked(self.paused)
        if not from_panel and self._floating is not None:
            self._floating.set_paused(self.paused)

    # --------------------------------------------------------------- misc
    def notify(self, message):
        self.window.status.showMessage(message, 4000)
        if self.tray.isVisible():
            self.tray.showMessage(W.APP_TITLE, message, QSystemTrayIcon.Information, 2500)
