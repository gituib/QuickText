"""端到端验证：全局热键 + 组合键 + 实际注入到目标文本框。"""
import os
import subprocess
import sys
import tempfile
import time
import ctypes

os.environ['APPDATA'] = os.path.join(tempfile.gettempdir(), 'qt_profile_e2e')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from quicktext import inputsim, winapi as W
from quicktext.app import AppController
from quicktext.store import new_phrase

PS_SCRIPT = r'''
param([string]$outPath)
Add-Type -AssemblyName System.Windows.Forms
$form = New-Object System.Windows.Forms.Form
$form.Text = 'QT_E2E_TARGET'
$form.Width = 700; $form.Height = 420; $form.StartPosition = 'CenterScreen'
$tb = New-Object System.Windows.Forms.TextBox
$tb.Multiline = $true; $tb.Dock = 'Fill'
$tb.Font = New-Object System.Drawing.Font('Microsoft YaHei', 12)
$form.Controls.Add($tb)
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 400
$timer.Add_Tick({ [IO.File]::WriteAllText($outPath, $tb.Text, [Text.Encoding]::UTF8) })
$timer.Start()
$form.Add_Shown({ $form.Activate(); $tb.Focus() })
[System.Windows.Forms.Application]::Run($form)
'''

out_file = os.path.join(tempfile.gettempdir(), 'qt_e2e_out.txt')
if os.path.exists(out_file):
    os.remove(out_file)
ps1 = os.path.join(tempfile.gettempdir(), 'qt_e2e_form.ps1')
with open(ps1, 'w', encoding='utf-8-sig') as fh:
    fh.write(PS_SCRIPT)
proc = subprocess.Popen(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                         '-File', ps1, out_file])

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
if os.path.exists(W.data_file()):
    os.remove(W.data_file())
ctl = AppController(app)
ctl.store.phrases = [
    new_phrase("账号", 0, 0x70, "HZ_NAP@1#2$3!"),
    new_phrase("多行", 0, 0x71, "第一行 Line2\n第二行 tab\ttabbed"),
    new_phrase("配合键", W.MOD_CONTROL, 0x4B, "Ctrl+K 输入的内容"),
]
ctl.store.save()
print("hotkeys:", ctl.reload_hotkeys())
ctl.window.hide()

user32 = ctypes.windll.user32
hwnd = 0
handler_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)


def find_target():
    global hwnd
    found = []

    def cb(h, l):
        t = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(h, t, 256)
        if 'QT_E2E_TARGET' in t.value:
            found.append(h)
        return True

    user32.EnumWindows(handler_type(cb), 0)
    if found:
        hwnd = found[0]
    return hwnd


for _ in range(40):
    if find_target():
        break
    time.sleep(0.2)
print("target:", hwnd)


def press(vk, mod=0, hold=0.05):
    if mod:
        inputsim._send_vk(mod, True)
        time.sleep(0.03)
    inputsim._send_vk(vk, True)
    time.sleep(hold)
    inputsim._send_vk(vk, False)
    if mod:
        time.sleep(0.03)
        inputsim._send_vk(mod, False)


def activate():
    ok = inputsim.restore_window(hwnd)
    time.sleep(0.8)
    fg = inputsim.foreground_window()
    title = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(ctypes.c_void_p(fg), title, 256)
    print("foreground:", fg, title.value, "restore ok:", ok)


def run_steps():
    steps = [
        (1500, lambda: (print(">> F1"), press(0x70))),
        (2600, lambda: (print(">> Enter"), press(0x0D))),
        (3400, lambda: (print(">> F2"), press(0x71))),
        (4800, lambda: (print(">> Ctrl+K"), press(0x4B, mod=0x11))),
        (6400, finish),
    ]
    total = 1500
    for delay, fn in steps:
        QTimer.singleShot(delay, fn)


def finish():
    time.sleep(1.0)
    try:
        user32.PostMessageW(hwnd, 0x0010, 0, 0)
    except Exception:
        pass
    proc.terminate()
    app.quit()


QTimer.singleShot(1200, activate)
QTimer.singleShot(2400, run_steps)
QTimer.singleShot(9000, app.quit)
app.exec()

time.sleep(0.5)
print("---- captured ----")
if os.path.exists(out_file):
    with open(out_file, 'r', encoding='utf-8-sig') as fh:
        print(repr(fh.read()))
else:
    print("(none)")
