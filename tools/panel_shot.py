import os
import sys
import tempfile

os.environ['APPDATA'] = os.path.join(tempfile.gettempdir(), 'qt_profile_panel')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from quicktext import winapi as W
from quicktext.app import AppController
from quicktext.store import new_phrase

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
if os.path.exists(W.data_file()):
    os.remove(W.data_file())
ctl = AppController(app)
ctl.store.phrases = [new_phrase('长文本', 0, 0, '这是一段比较长的示例文字，用于检查悬浮面板里的多行预览效果，超出部分应被截断显示。'),
                     new_phrase('账号', 0, 0x70, 'HZ_NAP@1#2$3!')]
ctl.store.save()
ctl.toggle_panel(True)
ctl.store.settings['floatingPanelTextLines'] = 2
ctl.floating.reload_phrases()
ctl.floating.show()
shots = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shots')


def grab_panel():
    ctl.floating.grab().save(os.path.join(shots, 'panel2.png'))


def open_settings_popup():
    ctl.floating._toggle_settings()
    app.processEvents()
    ctl.floating.grab().save(os.path.join(shots, 'panel_settings.png'))
    ctl.floating._toggle_settings()


def done():
    ctl.quit()
    app.quit()


QTimer.singleShot(600, grab_panel)
QTimer.singleShot(900, open_settings_popup)
QTimer.singleShot(1400, done)
QTimer.singleShot(4000, app.quit)
app.exec()
print('ok')
