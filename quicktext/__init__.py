"""应用入口。"""
import ctypes
import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtNetwork import QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

from . import winapi as W
from .app import AppController, IPC_NAME

_INSTANCE_HANDLE = None


def _acquire_single_instance():
    """用命名互斥量保证只运行一个实例（进程退出后自动释放）。"""
    global _INSTANCE_HANDLE
    if sys.platform != "win32":
        return True
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        _INSTANCE_HANDLE = kernel32.CreateMutexW(None, False,
                                                 r"Local\QuickText.SingleInstance")
        if not _INSTANCE_HANDLE:
            return True
        return ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return True


def _signal_existing_instance():
    """唤醒已在运行的实例，把主窗口带到前台。"""
    sock = QLocalSocket()
    sock.connectToServer(IPC_NAME)
    if sock.waitForConnected(600):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(600)
        sock.disconnectFromServer()


def main():
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    app = QApplication(sys.argv)
    app.setApplicationName(W.APP_NAME)
    app.setApplicationDisplayName(W.APP_TITLE)
    app.setOrganizationName(W.ORG_NAME)
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    icon = W.app_icon_path()
    if icon:
        app.setWindowIcon(QIcon(icon))

    if not _acquire_single_instance():
        _signal_existing_instance()
        return 0

    try:
        controller = AppController(app)
    except Exception as exc:  # 数据文件损坏等致命错误
        QMessageBox.critical(None, W.APP_TITLE, "启动失败：%s" % exc)
        return 1

    app._controller = controller
    return app.exec()
