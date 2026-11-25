"""
QuickText - 文本自动输入器（复刻自 Cok Auto Typer / 楼月文本自动输入器 3.2）

Author: clone build
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quicktext import main as run

if __name__ == "__main__":
    sys.exit(run())
