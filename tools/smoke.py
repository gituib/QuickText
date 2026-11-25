import os
import sys
import tempfile

os.environ['APPDATA'] = os.path.join(tempfile.gettempdir(), 'qt_profile')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from quicktext import winapi as W
from quicktext.app import AppController
from quicktext.store import new_phrase

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
ctl = AppController(app)
ctl.store.phrases = [
    new_phrase("账号", W.MOD_NONE if hasattr(W, 'MOD_NONE') else 0, 0x70, "HZ_NAP@1#2$3!"),
    new_phrase("邮箱", 0, 0x71, "fsd_enable@boce@2021"),
    new_phrase("密码", 0, 0x72, "Zpepc001@"),
]
ctl.store.save()
ctl.reload_hotkeys()
ctl.window.refresh()
ctl.show_main()

shots = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shots')
os.makedirs(shots, exist_ok=True)


def grab():
    ctl.window.grab().save(os.path.join(shots, 'main.png'))


def add_dialog():
    from quicktext.phrase_dialog import PhraseDialog
    dlg = PhraseDialog(ctl.store, ctl.store.phrases[0], ctl.window, ctl.theme_index)
    dlg.show()
    app.processEvents()
    dlg.grab().save(os.path.join(shots, 'phrase.png'))
    dlg.close()


def settings_dialog():
    from quicktext.settings_dialog import SettingsDialog
    dlg = SettingsDialog(ctl.store, ctl.theme_index, ctl.window, ctl.app_index)
    dlg.show()
    app.processEvents()
    dlg.grab().save(os.path.join(shots, 'settings.png'))
    dlg.close()


def picker_dialog():
    from quicktext.picker import PickerDialog
    dlg = PickerDialog(ctl.store, ctl.theme_index, (200, 200))
    dlg.show()
    app.processEvents()
    dlg.grab().save(os.path.join(shots, 'picker.png'))
    dlg.close()


def panel():
    ctl.toggle_panel(True)
    app.processEvents()
    ctl.floating.grab().save(os.path.join(shots, 'panel.png'))
    ctl.toggle_panel(False)


QTimer.singleShot(600, grab)
QTimer.singleShot(900, add_dialog)
QTimer.singleShot(1200, settings_dialog)
QTimer.singleShot(1500, picker_dialog)
QTimer.singleShot(1800, panel)
QTimer.singleShot(2300, lambda: (ctl.quit(), app.quit()))
print('exit', app.exec())
