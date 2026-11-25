import os
import sys
import tempfile

os.environ['APPDATA'] = os.path.join(tempfile.gettempdir(), 'qt_profile_flow2')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from quicktext import winapi as W
from quicktext.app import AppController
from quicktext.phrase_dialog import PhraseDialog
from quicktext.store import PhraseStore, new_phrase

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
path = W.data_file()
if os.path.exists(path):
    os.remove(path)
log = []


def check_validation():
    store = PhraseStore()
    store.phrases = [new_phrase('账号', 0, 0x70, 'AAA')]
    # 重复内容
    dlg = PhraseDialog(store, None, None, 1)
    dlg.ed_text.setPlainText('AAA')
    dlg._on_accept()
    log.append('dup_rejected=%s msg=%r visible=%s' % (dlg.result() != PhraseDialog.Accepted,
                                                      dlg.lbl_error.text(), dlg.isVisible()))
    # 快捷键冲突
    dlg2 = PhraseDialog(store, None, None, 1)
    dlg2.ed_text.setPlainText('BBB')
    dlg2.ed_key.set_hotkey(0, 0x70)
    dlg2._on_accept()
    log.append('hk_rejected=%s msg=%r' % (dlg2.result() != PhraseDialog.Accepted, dlg2.lbl_error.text()))
    # 空内容
    dlg3 = PhraseDialog(store, None, None, 1)
    dlg3._on_accept()
    log.append('empty_rejected=%s msg=%r' % (dlg3.result() != PhraseDialog.Accepted, dlg3.lbl_error.text()))
    # 正常
    dlg4 = PhraseDialog(store, None, None, 1)
    dlg4.ed_name.setText('邮件')
    dlg4.ed_key.set_hotkey(0, 0x71)
    dlg4.ed_text.setPlainText('line1\nline2')
    dlg4._on_accept()
    p = dlg4.result_phrase()
    log.append('accepted=%s name=%r vk=%s' % (dlg4.result() == PhraseDialog.Accepted, p['name'], p['hotkeyVk']))
    for d in (dlg, dlg2, dlg3, dlg4):
        d.deleteLater()

    # 热键集合（避免与真实应用占用冲突）
    ctl = AppController(app)
    ctl.store.phrases = []
    ctl.store.save()
    failed = ctl.reload_hotkeys()
    log.append('baseline_failures=%r' % (failed,))
    # 删除流程
    ctl.store.add(new_phrase('临时', 0, 0x7A, '临时内容'))
    ctl.window.refresh()
    ctl.window.select_phrase(ctl.store.phrases[0]['id'])
    from PySide6.QtWidgets import QMessageBox as MB
    calls = []
    orig = MB.question
    MB.question = staticmethod(lambda *a, **k: (calls.append('question'), MB.Yes)[1])
    ctl.delete_phrase()
    MB.question = orig
    log.append('question_called=%r count_after_delete=%d' % (calls, len(ctl.store.phrases)))
    ctl.quit()
    app.quit()


QTimer.singleShot(500, check_validation)
QTimer.singleShot(8000, app.quit)
app.exec()
for line in log:
    print(line)
