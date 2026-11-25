import os
import sys
import tempfile

os.environ['APPDATA'] = os.path.join(tempfile.gettempdir(), 'qt_profile_flow')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from quicktext import winapi as W
from quicktext.app import AppController
from quicktext.phrase_dialog import PhraseDialog
from quicktext.store import new_phrase

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
path = W.data_file()
if os.path.exists(path):
    os.remove(path)
ctl = AppController(app)
calls = []


def close_dialogs():
    dlg = app.activeModalWidget()
    if dlg is not None:
        dlg.accept()


def add_two():
    # 1) 添加：账号 F1
    def fill1():
        dlg = app.activeModalWidget()
        if not isinstance(dlg, PhraseDialog):
            calls.append('no phrase dialog')
            return
        dlg.ed_name.setText('账号')
        dlg.ed_key.set_hotkey(0, 0x70)
        dlg.ed_text.setPlainText('HZ_NAP@1#2$3!')
        dlg._on_accept()

    QTimer.singleShot(150, fill1)
    ctl.add_phrase()
    calls.append('added1=%d' % len(ctl.store.phrases))

    # 2) 添加：重复内容应被拒绝
    def fill2():
        dlg = app.activeModalWidget()
        dlg.ed_name.setText('重复')
        dlg.ed_text.setPlainText('HZ_NAP@1#2$3!')
        dlg._on_accept()
        calls.append('dup_error=%r' % dlg.lbl_error.text())
        dlg.reject()

    calls.append('fill2 scheduled')
    QTimer.singleShot(150, fill2)
    def run2():
        calls.append('run2 start')
        ctl.add_phrase()
        calls.append('run2 end')
    QTimer.singleShot(400, run2)
    calls.append('after dup=%d' % len(ctl.store.phrases))

    # 3) 添加：快捷键冲突应被拒绝
    def fill3():
        dlg = app.activeModalWidget()
        dlg.ed_name.setText('冲突')
        dlg.ed_key.set_hotkey(0, 0x70)
        dlg.ed_text.setPlainText('别的文字')
        dlg._on_accept()
        calls.append('hk_error=%r' % dlg.lbl_error.text())
        dlg.reject()

    QTimer.singleShot(150, fill3)
    ctl.add_phrase()

    # 4) 添加：Ctrl+K
    def fill4():
        dlg = app.activeModalWidget()
        dlg.ed_name.setText('配合键')
        dlg.ed_key.set_hotkey(W.MOD_CONTROL, 0x4B)
        dlg.ed_text.setPlainText('多行\n第二行')
        dlg._on_accept()

    QTimer.singleShot(150, fill4)
    ctl.add_phrase()
    calls.append('total=%d' % len(ctl.store.phrases))

    # 5) 修改第一条
    ctl.window.refresh()
    ctl.window.select_phrase(ctl.store.phrases[0]['id'])

    def fill5():
        dlg = app.activeModalWidget()
        dlg.ed_name.setText('账号2')
        dlg._on_accept()

    QTimer.singleShot(150, fill5)
    ctl.edit_phrase()
    calls.append('edited_name=%r' % ctl.store.phrases[0]['name'])

    # 6) 导出
    out = os.path.join(tempfile.gettempdir(), 'qt_export.json')
    if os.path.exists(out):
        os.remove(out)
    import json
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(ctl.store.export_payload(), fh, ensure_ascii=False)

    # 7) 导入（含重复项与一条新项）
    with open(out, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
    data['phrases'].append(new_phrase('新条目', 0, 0x72, '全新内容'))
    data['phrases'].append({'name': '坏数据'})
    added, dup, bad = ctl.store.import_payload(data)
    calls.append('import added=%d dup=%d bad=%d' % (len(added), len(dup), bad))

    # 8) 删除
    ctl.window.refresh()
    ctl.window.select_phrase(ctl.store.phrases[-1]['id'])
    QTimer.singleShot(150, lambda: app.activeModalWidget().done(QMessageBox.Yes))
    ctl.delete_phrase()
    calls.append('after delete=%d' % len(ctl.store.phrases))

    # 9) 暂停
    ctl.set_paused(True)
    calls.append('paused=%s panel=%s' % (ctl.paused, ctl.floating.paused))
    ctl.set_paused(False)
    calls.append('resumed=%s' % ctl.paused)

    # 10) 数据持久化检查
    from quicktext.store import PhraseStore
    reloaded = PhraseStore()
    calls.append('persisted=%d' % len(reloaded.phrases))

    # 11) 热键重载
    calls.append('hotkeys=%r' % (ctl.reload_hotkeys(),))

    ctl.quit()


QTimer.singleShot(800, add_two)
QTimer.singleShot(6000, lambda: (ctl.quit(), app.quit()))
app.exec()
for line in calls:
    print(line)
