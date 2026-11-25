"""
QuickText - 文本自动输入器

通过全局热键唤起短语面板，将预置短语输入到当前焦点窗口。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quicktext import main as run

if __name__ == "__main__":
    sys.exit(run())
