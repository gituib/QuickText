"""界面样式：三套主题的统一设计系统。

theme_index 语义：
    0 = 经典（中性灰，沉稳）
    1 = 浅色 · 湖青（默认）
    >=2 = 深色

设计令牌分三层：底色/表面/边框 → 文本层级 → 主色与状态色。
组件样式（侧栏、导航、卡片、表格、弹层）全部引用令牌，三套主题只换色不改结构。

对外函数：
    build_stylesheet(theme_index, scope)  主窗口 / 对话框 / 选择器 / 悬浮面板
    floating_stylesheet(theme_index)      悬浮面板（合并多段样式）
    palette(theme_index)                  供 Python 代码取色的字典
"""
import os
import tempfile

# ---------------------------------------------------------------- 图标
# 说明：Qt 的 QSS url() 不支持 data URI，图标需落地为 svg 文件后引用
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
_TEMP_ASSETS_DIR = os.path.join(tempfile.gettempdir(), "quicktext-assets")


def _svg_file(name: str, body: str) -> str:
    """写图标文件；包内目录不可写时退到临时目录，避免静默丢图。"""
    for directory in (_ASSETS_DIR, _TEMP_ASSETS_DIR):
        path = os.path.join(directory, name)
        try:
            if not os.path.exists(path):
                os.makedirs(directory, exist_ok=True)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(body)
        except OSError:
            continue
        return path.replace("\\", "/")
    return os.path.join(_ASSETS_DIR, name).replace("\\", "/")


def _svg_chevron(color="#ffffff") -> str:
    return ("<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'>"
            "<path d='M2 4l4 4 4-4' fill='none' stroke='%s' stroke-width='1.8' "
            "stroke-linecap='round' stroke-linejoin='round'/></svg>" % color)


def _svg_check(color="#ffffff") -> str:
    return ("<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'>"
            "<path d='M2.5 6.2l2.3 2.3 4.7-5' fill='none' stroke='%s' stroke-width='1.9' "
            "stroke-linecap='round' stroke-linejoin='round'/></svg>" % color)


def _svg_search(color="#6A8185", inset=0) -> str:
    # Qt 的 QSS 不支持 background-position 的三值语法，也无法用 px 定位，
    # 因此把左侧留白直接画进 svg，配合 `left center` 得到稳定的内缩距离。
    size = 16 + inset
    return ("<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='16' "
            "viewBox='0 0 %d 16'><g transform='translate(%d 0)'>"
            "<circle cx='7' cy='7' r='4.6' fill='none' stroke='%s' stroke-width='1.6'/>"
            "<path d='M10.6 10.6L14 14' fill='none' stroke='%s' stroke-width='1.6' "
            "stroke-linecap='round'/></g></svg>" % (size, size, inset, color, color))


# ---------------------------------------------------------------- 色板
# 浅色 · 湖青：冷调浅灰底 + 白卡片 + 青绿主色
LIGHT = {
    "primary": "#0E8C82",
    "primary_hover": "#12A197",
    "primary_pressed": "#0A736B",
    "on_primary": "#FFFFFF",
    "accent": "#E1673D",
    "accent_hover": "#F07A4F",
    "bg": "#F3F6F6",
    "surface": "#FFFFFF",
    "surface_alt": "#F6FAFA",
    "muted": "#EAF0F0",
    "muted_text": "#6A8185",
    "text": "#12292C",
    "text_soft": "#40585C",
    "border": "#E1EAEA",
    "border_strong": "#C9D8D8",
    "selected": "#DCF2EF",
    "selected_text": "#0B443F",
    "row_hover": "#F3FAF9",
    "header_bg": "#F7FBFB",
    "header_text": "#4A6266",
    "scroll": "#C9D8D8",
    "scroll_hover": "#9FB8B6",
    "disabled": "#9AADAD",
    "danger": "#C2410C",
    "danger_hover": "#EA580C",
    "danger_pressed": "#9A3412",
    "success": "#0E8C82",
    "warn": "#B45309",
    "check": "#FFFFFF",
    "chevron": "#6A8185",
    "pressed_bg": "#E3F1F0",
    "dialog_title_bg": "#FFFFFF",
    "dialog_title_text": "#12292C",
    "title_action_bg": "rgba(14,140,130,0.10)",
    "title_action_hover": "rgba(14,140,130,0.18)",
    "title_action_checked": "rgba(14,140,130,0.26)",
    "title_action_text": "#0A6E66",
    "hover_tint": "#F1F8F7",
    "sidebar": "#F8FBFB",
    "nav_text": "#536A6E",
    "nav_hover": "#EDF6F5",
    "nav_active": "#DFF3F1",
    "nav_active_text": "#0A4B45",
    "nav_section": "#8A9C9E",
    "brand_mark_bg": "#0E8C82",
    "brand_mark_text": "#FFFFFF",
    "chip_bg": "#EAF6F4",
    "chip_text": "#0B6B63",
    "chip_border": "#D3EBE8",
}

# 经典：中性灰蓝，收敛的强调色
CLASSIC = dict(LIGHT)
CLASSIC.update({
    "primary": "#3D4A55",
    "primary_hover": "#4C5B67",
    "primary_pressed": "#2E3942",
    "on_primary": "#FFFFFF",
    "accent": "#B45309",
    "accent_hover": "#C2610D",
    "bg": "#F4F5F6",
    "surface": "#FFFFFF",
    "surface_alt": "#F7F8F9",
    "muted": "#ECEFF1",
    "muted_text": "#66717B",
    "text": "#1B242B",
    "text_soft": "#3A464F",
    "border": "#E2E6E9",
    "border_strong": "#C8CED3",
    "selected": "#E6EBEE",
    "selected_text": "#111A20",
    "row_hover": "#F4F6F7",
    "header_bg": "#F8F9FA",
    "header_text": "#4A555E",
    "scroll": "#C8CED3",
    "scroll_hover": "#A4AEB6",
    "success": "#3D4A55",
    "danger": "#B91C1C",
    "danger_hover": "#DC2626",
    "danger_pressed": "#991B1B",
    "pressed_bg": "#E4E9EC",
    "dialog_title_bg": "#FFFFFF",
    "dialog_title_text": "#1B242B",
    "title_action_bg": "rgba(0,0,0,0.06)",
    "title_action_hover": "rgba(0,0,0,0.11)",
    "title_action_checked": "rgba(0,0,0,0.16)",
    "title_action_text": "#374151",
    "hover_tint": "#F3F5F6",
    "sidebar": "#F8F9FA",
    "nav_text": "#525E67",
    "nav_hover": "#EDF0F2",
    "nav_active": "#E4E9EC",
    "nav_active_text": "#111A20",
    "nav_section": "#8B959D",
    "brand_mark_bg": "#3D4A55",
    "brand_mark_text": "#FFFFFF",
    "chip_bg": "#F0F2F4",
    "chip_text": "#3A464F",
    "chip_border": "#E1E5E8",
    "chevron": "#66717B",
})

# 深色：墨蓝底 + 青绿荧光主色
DARK = {
    "primary": "#2DD4BF",
    "primary_hover": "#5EEAD4",
    "primary_pressed": "#14B8A6",
    "on_primary": "#04211F",
    "accent": "#FB923C",
    "accent_hover": "#FDBA74",
    "bg": "#0B1218",
    "surface": "#111B23",
    "surface_alt": "#16222C",
    "muted": "#1E2C37",
    "muted_text": "#8FA3AD",
    "text": "#E6EEF2",
    "text_soft": "#A5B7C0",
    "border": "#22323D",
    "border_strong": "#354856",
    "selected": "#123B38",
    "selected_text": "#CFFAFE",
    "row_hover": "#17242E",
    "header_bg": "#14202A",
    "header_text": "#9DB2BC",
    "scroll": "#2C3F4C",
    "scroll_hover": "#42606F",
    "disabled": "#64748B",
    "danger": "#F87171",
    "danger_hover": "#FCA5A5",
    "danger_pressed": "#EF4444",
    "success": "#2DD4BF",
    "warn": "#FBBF24",
    "check": "#04211F",
    "chevron": "#A5B7C0",
    "pressed_bg": "#22323D",
    "dialog_title_bg": "#111B23",
    "dialog_title_text": "#E6EEF2",
    "title_action_bg": "rgba(45,212,191,0.14)",
    "title_action_hover": "rgba(45,212,191,0.24)",
    "title_action_checked": "rgba(45,212,191,0.32)",
    "title_action_text": "#A7F3E8",
    "hover_tint": "#17242E",
    "sidebar": "#0E171E",
    "nav_text": "#9BB0BA",
    "nav_hover": "#16232C",
    "nav_active": "#14322F",
    "nav_active_text": "#CFFAFE",
    "nav_section": "#64808C",
    "brand_mark_bg": "#2DD4BF",
    "brand_mark_text": "#04211F",
    "chip_bg": "#15302E",
    "chip_text": "#7DE8DB",
    "chip_border": "#1E4440",
}

# 旧名字保留，避免外部按名称引用时出错
TEAL = LIGHT


def _resolve(theme_index) -> dict:
    try:
        idx = int(theme_index)
    except (TypeError, ValueError):
        idx = 1
    if idx <= 0:
        return CLASSIC
    if idx == 1:
        return LIGHT
    return DARK


def palette(theme_index: int) -> dict:
    """返回主题色板（dict），供 Python 代码直接取色。"""
    return dict(_resolve(theme_index))


def _check(c) -> str:
    color = c["check"]
    return _svg_file("check-%s.svg" % color.lstrip("#"), _svg_check(color))


def _chevron(c) -> str:
    color = c.get("chevron") or c["muted_text"]
    return _svg_file("chevron-%s.svg" % color.lstrip("#"), _svg_chevron(color))


def _search(c, inset=0) -> str:
    color = c["muted_text"].lstrip("#")
    return _svg_file("search-%s-%d.svg" % (color, inset), _svg_search("#" + color, inset))


# ---------------------------------------------------------------- 主窗口
def _main_qss(c):
    chevron = _chevron(c)
    search = _search(c, 14)
    return f"""
/* ---- 基础容器 ---- */
QWidget {{ font-family: "Microsoft YaHei UI", "Segoe UI", "PingFang SC", sans-serif; }}
QWidget#menuHost {{ background: {c['bg']}; border: none; }}
QWidget#central {{ background: {c['bg']}; border: none; }}
QMainWindow {{ background: {c['bg']}; }}
QToolTip {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']};
    border-radius: 6px; padding: 5px 8px; font-size: 12px; }}

/* ---- 左侧导航 ---- */
QWidget#sidebar {{ background: {c['sidebar']}; border: none;
    border-right: 1px solid {c['border']}; }}
QLabel#brandMark {{ background: {c['brand_mark_bg']}; color: {c['brand_mark_text']};
    border-radius: 10px; font-size: 17px; font-weight: 800; qproperty-alignment: AlignCenter; }}
QLabel#brandName {{ color: {c['text']}; font-size: 15px; font-weight: 700; }}
QLabel#brandTag {{ color: {c['nav_section']}; font-size: 10px; font-weight: 600; }}
QLabel#navSection {{ color: {c['nav_section']}; font-size: 11px; font-weight: 700;
    padding: 0 4px; background: transparent; }}
QToolButton#navSectionAction {{ background: transparent; color: {c['nav_section']}; border: none;
    border-radius: 6px; font-size: 15px; font-weight: 700; }}
QToolButton#navSectionAction:hover {{ background: {c['nav_hover']}; color: {c['text']}; }}
QToolButton#navSectionAction:pressed {{ background: {c['pressed_bg']}; }}
QPushButton#navItem {{ background: transparent; color: {c['nav_text']}; border: none;
    border-radius: 8px; padding: 8px 12px; text-align: left; font-size: 13px;
    font-weight: 600; min-height: 20px; }}
QPushButton#navItem:hover {{ background: {c['nav_hover']}; color: {c['text']}; }}
QPushButton#navItem:pressed {{ background: {c['pressed_bg']}; }}
QPushButton#navItem:checked {{ background: {c['nav_active']}; color: {c['nav_active_text']}; }}
QPushButton#navItem::menu-indicator {{ image: none; width: 0; }}
QLabel#versionLabel {{ color: {c['nav_section']}; font-size: 11px; background: transparent; }}
QListWidget#groupList {{ background: transparent; border: none; outline: none; padding: 0; }}
QListWidget#groupList::item {{ color: {c['nav_text']}; padding: 7px 12px;
    border-radius: 7px; font-size: 13px; }}
QListWidget#groupList::item:hover {{ background: {c['nav_hover']}; color: {c['text']}; }}
QListWidget#groupList::item:selected {{ background: {c['nav_active']};
    color: {c['nav_active_text']}; font-weight: 600; }}

/* ---- 右侧内容区 ---- */
QWidget#content {{ background: {c['bg']}; border: none; }}
QLabel#pageTitle {{ color: {c['text']}; font-size: 24px; font-weight: 800; }}
QLabel#pageSubtitle {{ color: {c['muted_text']}; font-size: 12px; }}
QFrame#hairline {{ background: {c['border']}; border: none; max-height: 1px; min-height: 1px; }}
QLabel#emptyHint {{ color: {c['muted_text']}; font-size: 13px; background: transparent; }}

/* ---- 菜单 ---- */
QMenuBar {{ background: {c['surface']}; color: {c['text_soft']}; border: none;
    padding: 2px 6px; font-size: 13px; }}
QMenuBar::item {{ color: {c['text_soft']}; background: transparent; padding: 5px 10px;
    border-radius: 6px; margin: 0 1px; }}
QMenuBar::item:selected {{ background: {c['selected']}; color: {c['selected_text']}; }}

/* ---- 状态栏 ---- */
QStatusBar {{ background: {c['sidebar']}; color: {c['muted_text']}; border: none;
    border-top: 1px solid {c['border']}; padding: 4px 10px; font-size: 11px;
    min-height: 20px; }}
QStatusBar QLabel {{ color: {c['muted_text']}; background: transparent; padding-right: 8px; }}
QSizeGrip {{ width: 0; height: 0; }}

/* ---- 顶部 / 工具栏 ---- */
QLabel#appTitle {{ color: {c['text']}; font-size: 18px; font-weight: 700; }}
QLabel#appBadge {{ background: {c['primary']}; color: {c['on_primary']}; border-radius: 6px;
    padding: 3px 8px; font-size: 12px; font-weight: 700; }}
QLabel#appSubtitle {{ color: {c['muted_text']}; font-size: 12px; }}
QToolButton#moreButton {{ background: {c['surface']}; color: {c['text_soft']};
    border: 1px solid {c['border']}; border-radius: 9px; font-size: 17px;
    font-weight: 700; padding: 0 4px; }}
QToolButton#moreButton:hover {{ background: {c['hover_tint']}; border-color: {c['border_strong']};
    color: {c['text']}; }}
QToolButton#moreButton:pressed {{ background: {c['pressed_bg']}; }}
QToolButton#moreButton::menu-indicator {{ image: none; width: 0; }}

/* ---- 搜索框：左侧放大镜，focus 时主色描边 ---- */
QLineEdit#search {{ background: {c['surface']}; color: {c['text']};
    border: 1px solid {c['border_strong']}; border-radius: 10px;
    padding: 6px 14px 6px 38px; min-height: 24px; font-size: 13px;
    background-image: url("{search}"); background-repeat: no-repeat;
    background-position: left center;
    selection-background-color: {c['selected']}; selection-color: {c['selected_text']}; }}
QLineEdit#search:hover {{ border-color: {c['border_strong']}; }}
QLineEdit#search:focus {{ border: 2px solid {c['primary']}; padding: 5px 13px 5px 37px; }}
QLineEdit#search:disabled {{ color: {c['disabled']}; background: {c['muted']}; }}

/* ---- 分组筛选下拉 ---- */
QComboBox#groupFilter {{ background: {c['surface']}; color: {c['text']};
    border: 1px solid {c['border_strong']}; border-radius: 8px;
    padding: 4px 28px 4px 10px; min-height: 22px; font-size: 12px; }}
QComboBox#groupFilter:hover {{ border-color: {c['primary']}; }}
QComboBox#groupFilter:focus {{ border: 2px solid {c['primary']};
    padding: 3px 27px 3px 9px; }}
QComboBox#groupFilter::drop-down {{ subcontrol-origin: padding;
    subcontrol-position: center right; width: 24px; border: none; background: transparent; }}
QComboBox#groupFilter::down-arrow {{ image: url("{chevron}"); width: 10px; height: 10px; }}
QComboBox#groupFilter QAbstractItemView {{ background: {c['surface']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 8px; padding: 4px; outline: none;
    selection-background-color: {c['selected']}; selection-color: {c['selected_text']}; }}

/* ---- 按钮 ---- */
QPushButton[kind="ghost"] {{ background: {c['surface']};
    color: {c['text_soft']}; border: 1px solid {c['border']}; border-radius: 9px;
    padding: 6px 14px; min-height: 22px; font-weight: 600; font-size: 13px; }}
QPushButton[kind="ghost"]:hover {{
    background: {c['hover_tint']}; border-color: {c['border_strong']}; color: {c['text']}; }}
QPushButton[kind="ghost"]:pressed {{
    background: {c['pressed_bg']}; border-color: {c['border_strong']}; }}
QPushButton[kind="ghost"]:focus {{ border-color: {c['primary']}; }}
QPushButton[kind="ghost"]:disabled {{
    background: {c['muted']}; color: {c['disabled']}; border-color: {c['border']}; }}

QPushButton[kind="primary"] {{ background: {c['primary']}; color: {c['on_primary']};
    border: 1px solid {c['primary']}; border-radius: 9px; padding: 7px 18px;
    min-height: 22px; font-weight: 700; font-size: 13px; }}
QPushButton[kind="primary"]:hover {{ background: {c['primary_hover']};
    border-color: {c['primary_hover']}; }}
QPushButton[kind="primary"]:pressed {{ background: {c['primary_pressed']};
    border-color: {c['primary_pressed']}; }}
QPushButton[kind="primary"]:focus {{ border: 2px solid {c['text']}; padding: 6px 17px; }}
QPushButton[kind="primary"]:disabled {{ background: {c['muted']}; color: {c['disabled']};
    border-color: {c['border']}; }}

QPushButton[kind="danger"] {{ background: transparent; color: {c['danger']};
    border: 1px solid {c['border']}; border-radius: 9px; padding: 6px 14px;
    min-height: 22px; font-weight: 600; font-size: 13px; }}
QPushButton[kind="danger"]:hover {{ background: {c['danger_hover']};
    border-color: {c['danger_hover']}; color: {c['on_primary']}; }}
QPushButton[kind="danger"]:pressed {{ background: {c['danger_pressed']};
    border-color: {c['danger_pressed']}; color: {c['on_primary']}; }}
QPushButton[kind="danger"]:disabled {{ color: {c['disabled']}; border-color: {c['border']};
    background: transparent; }}

/* ---- 表格 ---- */
QTableWidget#phrases {{ background: {c['surface']}; alternate-background-color: {c['surface']};
    border: 1px solid {c['border']}; border-radius: 12px; outline: none;
    gridline-color: transparent; selection-background-color: {c['selected']};
    selection-color: {c['selected_text']}; color: {c['text']};
    font-size: 13px; }}
QTableWidget#phrases::item {{ padding: 4px 12px; border: none; background: transparent;
    color: {c['text']}; }}
QTableWidget#phrases::item:hover {{ background: {c['row_hover']}; }}
QTableWidget#phrases::item:selected {{ background: {c['selected']}; color: {c['selected_text']}; }}
QTableWidget#phrases::item:focus {{ outline: none; border: none; }}
QTableWidget#phrases QTableCornerButton::section {{ background: {c['header_bg']}; border: none; }}
QHeaderView {{ background: {c['header_bg']}; border: none; }}
QHeaderView::section {{ background: {c['header_bg']}; color: {c['header_text']};
    border: none; border-bottom: 1px solid {c['border']}; padding: 6px 12px;
    font-weight: 600; font-size: 11px; }}
QHeaderView::section:first {{ border-top-left-radius: 11px; }}
QHeaderView::section:last {{ border-top-right-radius: 11px; }}
QHeaderView::section:hover {{ background: {c['row_hover']}; color: {c['text']}; }}
QTableWidget QTableCornerButton::section {{ background: {c['header_bg']}; border: none; }}

/* ---- 滚动条 ---- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px 4px 0; border: none; }}
QScrollBar::handle:vertical {{ background: {c['scroll']}; min-height: 28px; border-radius: 5px; }}
QScrollBar::handle:vertical:hover {{ background: {c['scroll_hover']}; }}
QScrollBar::handle:vertical:pressed {{ background: {c['scroll_hover']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0; border: none; background: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{ background: transparent; height: 10px;
    margin: 0 4px 2px 4px; border: none; }}
QScrollBar::handle:horizontal {{ background: {c['scroll']}; min-width: 28px;
    border-radius: 5px; }}
QScrollBar::handle:horizontal:hover {{ background: {c['scroll_hover']}; }}
QScrollBar::handle:horizontal:pressed {{ background: {c['scroll_hover']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0; border: none; background: none; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
"""


# ---------------------------------------------------------------- 菜单弹层
def _menu_qss(c):
    """QMenu 样式：主窗口、对话框（含托盘菜单）与速启弹窗共用。"""
    return f"""
QMenu {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']};
    border-radius: 10px; padding: 6px; }}
QMenu::item {{ background: transparent; color: {c['text']}; padding: 7px 28px 7px 12px;
    border-radius: 6px; }}
QMenu::item:selected {{ background: {c['selected']}; color: {c['selected_text']}; }}
QMenu::item:disabled {{ color: {c['disabled']}; }}
QMenu::separator {{ height: 1px; background: {c['border']}; margin: 5px 8px; }}
QMenu::indicator {{ width: 14px; height: 14px; }}
"""


# ---------------------------------------------------------------- 对话框
def _dialog_qss(c):
    chevron = _chevron(c)
    check = _check(c)
    return f"""
QDialog, QMessageBox {{ background: {c['bg']}; color: {c['text']}; font-size: 13px; }}
QDialog QLabel, QMessageBox QLabel {{ color: {c['text']}; background: transparent; }}
QLabel#dialogTitle {{ color: {c['text']}; font-size: 20px; font-weight: 800; }}
QLabel#dialogSubtitle {{ color: {c['muted_text']}; font-size: 12px; }}
QLabel#hint {{ color: {c['muted_text']}; font-size: 12px; }}
QLabel#sectionLabel {{ color: {c['text']}; font-size: 13px; font-weight: 700; }}
QFrame#formCard {{ background: {c['surface']}; border: 1px solid {c['border']};
    border-radius: 12px; }}
QWidget#settingsBody {{ background: transparent; }}
QWidget#settingsFooter {{ background: {c['bg']}; border-top: 1px solid {c['border']}; }}
QScrollArea#settingsScroll {{ background: transparent; border: none; }}
QScrollArea#settingsScroll > QWidget > QWidget {{ background: transparent; }}

QDialog QLineEdit, QDialog QPlainTextEdit, QDialog QTextEdit, QMessageBox QLineEdit {{
    background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border_strong']};
    border-radius: 9px; padding: 6px 10px; min-height: 22px; font-size: 13px;
    selection-background-color: {c['selected']}; selection-color: {c['selected_text']}; }}
QDialog QLineEdit:focus {{ border: 2px solid {c['primary']}; padding: 5px 9px; }}
QDialog QPlainTextEdit:focus, QDialog QTextEdit:focus {{ border: 2px solid {c['primary']};
    padding: 7px 9px; }}
QDialog QLineEdit:hover, QDialog QPlainTextEdit:hover, QDialog QTextEdit:hover {{
    border-color: {c['border_strong']}; }}
QDialog QLineEdit:disabled, QDialog QPlainTextEdit:disabled, QDialog QTextEdit:disabled {{
    color: {c['disabled']}; background: {c['muted']}; }}
QDialog QPlainTextEdit, QDialog QTextEdit {{ padding: 8px 10px; }}

QDialog QComboBox {{ background: {c['surface']}; color: {c['text']};
    border: 1px solid {c['border_strong']}; border-radius: 9px;
    padding: 4px 32px 4px 10px; min-height: 24px; font-size: 13px; }}
QDialog QComboBox:hover {{ border-color: {c['border_strong']}; }}
QDialog QComboBox:focus {{ border: 2px solid {c['primary']}; padding: 3px 31px 3px 9px; }}
QDialog QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right;
    width: 26px; border: none; background: transparent; }}
QDialog QComboBox::down-arrow {{ image: url("{chevron}"); width: 10px; height: 10px; }}
QDialog QComboBox::down-arrow:on {{ top: 1px; }}
QDialog QComboBox QAbstractItemView {{ background: {c['surface']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 8px; padding: 4px; outline: none;
    selection-background-color: {c['selected']}; selection-color: {c['selected_text']}; }}
QDialog QComboBox QAbstractItemView::item {{ padding: 6px 8px; min-height: 22px;
    border-radius: 6px; }}
QDialog QComboBox QAbstractItemView::item:hover {{ background: {c['row_hover']}; }}
QDialog QComboBox QAbstractItemView::item:selected {{ background: {c['selected']};
    color: {c['selected_text']}; }}

QDialog QCheckBox, QMessageBox QCheckBox {{ color: {c['text']}; background: transparent;
    spacing: 8px; font-size: 13px; }}
QDialog QCheckBox:disabled, QMessageBox QCheckBox:disabled {{ color: {c['disabled']}; }}
QDialog QCheckBox::indicator, QMessageBox QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid {c['border_strong']}; border-radius: 5px;
    background: {c['surface']}; }}
QDialog QCheckBox::indicator:hover, QMessageBox QCheckBox::indicator:hover {{
    border-color: {c['primary']}; }}
QDialog QCheckBox::indicator:checked, QMessageBox QCheckBox::indicator:checked {{
    background: {c['primary']}; border-color: {c['primary']}; image: url({check}); }}
QDialog QCheckBox::indicator:disabled, QMessageBox QCheckBox::indicator:disabled {{
    background: {c['muted']}; border-color: {c['border']}; }}

QDialog QGroupBox {{ background: {c['surface']}; border: 1px solid {c['border']};
    border-radius: 12px; margin-top: 18px; padding: 18px 16px 14px 16px;
    font-weight: 700; color: {c['text']}; font-size: 13px; }}
QDialog QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left;
    left: 0px; padding: 0 4px 0 0; color: {c['text_soft']}; font-weight: 700;
    font-size: 13px; background: {c['bg']}; }}

QDialog QPushButton, QMessageBox QPushButton {{ background: {c['surface']}; color: {c['text_soft']};
    border: 1px solid {c['border_strong']}; border-radius: 9px; padding: 7px 22px;
    font-weight: 600; min-height: 24px; min-width: 72px; font-size: 13px; }}
QDialog QPushButton:hover, QMessageBox QPushButton:hover {{ background: {c['hover_tint']};
    border-color: {c['primary']}; color: {c['text']}; }}
QDialog QPushButton:pressed, QMessageBox QPushButton:pressed {{ background: {c['pressed_bg']}; }}
QDialog QPushButton:focus, QMessageBox QPushButton:focus {{ border-color: {c['primary']}; }}
QDialog QPushButton:disabled, QMessageBox QPushButton:disabled {{ color: {c['disabled']};
    background: {c['muted']}; border-color: {c['border']}; }}
QDialog QPushButton#primary, QDialog QPushButton:default, QMessageBox QPushButton:default {{
    background: {c['primary']}; color: {c['on_primary']}; border: 1px solid {c['primary']}; }}
QDialog QPushButton#primary:hover, QDialog QPushButton:default:hover,
QMessageBox QPushButton:default:hover {{ background: {c['primary_hover']};
    border-color: {c['primary_hover']}; color: {c['on_primary']}; }}
QDialog QPushButton#primary:pressed, QDialog QPushButton:default:pressed,
QMessageBox QPushButton:default:pressed {{ background: {c['primary_pressed']};
    border-color: {c['primary_pressed']}; }}
QDialog QPushButton#primary:disabled, QDialog QPushButton:default:disabled {{
    background: {c['muted']}; color: {c['disabled']}; border-color: {c['border']}; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px 4px 0;
    border: none; }}
QScrollBar::handle:vertical {{ background: {c['scroll']}; min-height: 28px; border-radius: 5px; }}
QScrollBar::handle:vertical:hover {{ background: {c['scroll_hover']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: none;
    background: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{ background: transparent; height: 10px;
    margin: 0 4px 2px 4px; border: none; }}
QScrollBar::handle:horizontal {{ background: {c['scroll']}; min-width: 28px;
    border-radius: 5px; }}
QScrollBar::handle:horizontal:hover {{ background: {c['scroll_hover']}; }}
QScrollBar::handle:horizontal:pressed {{ background: {c['scroll_hover']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0; border: none; background: none; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
QToolTip {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']};
    border-radius: 6px; padding: 5px 8px; font-size: 12px; }}
"""


# ---------------------------------------------------------------- 标题栏
def _titlebar_qss(c):
    return f"""
QWidget#dialogTitleBar {{ background: {c['dialog_title_bg']};
    border-bottom: 1px solid {c['border']}; }}
QLabel#dialogTitleLabel {{ color: {c['dialog_title_text']}; font-weight: 700; font-size: 13px;
    background: transparent; }}
QPushButton#dialogCaptionClose {{ background: transparent; border: none; border-radius: 6px;
    padding: 0px; color: {c['text_soft']}; }}
QPushButton#dialogCaptionClose:hover {{ background: {c['danger']}; color: {c['on_primary']}; }}
QPushButton#dialogCaptionClose:pressed {{ background: {c['danger_pressed']}; }}
QWidget#mainTitleBar {{ background: {c['surface']}; border-bottom: 1px solid {c['border']}; }}
QLabel#mainTitleLabel {{ color: {c['text']}; font-weight: 700; font-size: 13px;
    background: transparent; }}
QPushButton#captionMin, QPushButton#captionMax {{ background: transparent; border: none;
    border-radius: 6px; color: {c['text_soft']}; }}
QPushButton#captionMin:hover, QPushButton#captionMax:hover {{ background: {c['muted']};
    color: {c['text']}; }}
QPushButton#captionMin:pressed, QPushButton#captionMax:pressed {{ background: {c['pressed_bg']}; }}
QPushButton#captionClose {{ background: transparent; border: none; border-radius: 6px;
    padding: 0px; color: {c['text_soft']}; }}
QPushButton#captionClose:hover {{ background: {c['danger']}; color: {c['on_primary']}; }}
QPushButton#captionClose:pressed {{ background: {c['danger_pressed']}; }}
"""


# ---------------------------------------------------------------- 选择器
def _picker_qss(c):
    search = _search(c, 13)
    return f"""
QDialog#picker {{ background: transparent; border: none; }}
QFrame#pickerCard {{ background: {c['surface']}; border: 1px solid {c['border_strong']};
    border-radius: 16px; }}
QWidget#pickerHeader {{ background: transparent; }}
QLabel#pickerTitle {{ color: {c['text']}; font-size: 15px; font-weight: 700;
    background: transparent; }}
QLabel#pickerHint {{ color: {c['muted_text']}; font-size: 11px; background: transparent; }}
QLineEdit#pickerSearch {{ background: {c['surface_alt']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 9px;
    padding: 5px 10px 5px 36px; min-height: 22px; font-size: 13px;
    background-image: url("{search}"); background-repeat: no-repeat;
    background-position: left center;
    selection-background-color: {c['selected']}; selection-color: {c['selected_text']}; }}
QLineEdit#pickerSearch:focus {{ border: 2px solid {c['primary']};
    padding: 4px 9px 4px 35px; }}
QListWidget#pickerList {{ background: transparent; color: {c['text']};
    border: none; outline: none; padding: 2px; }}
QListWidget#pickerList::item {{ padding: 7px 10px; border-radius: 8px; }}
QListWidget#pickerList::item:hover:!selected {{ background: {c['row_hover']}; }}
QListWidget#pickerList::item:selected {{ background: {c['selected']};
    color: {c['selected_text']}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px 4px 0;
    border: none; }}
QScrollBar::handle:vertical {{ background: {c['scroll']}; min-height: 28px; border-radius: 5px; }}
QScrollBar::handle:vertical:hover {{ background: {c['scroll_hover']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: none;
    background: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{ background: transparent; height: 10px;
    margin: 0 4px 2px 4px; border: none; }}
QScrollBar::handle:horizontal {{ background: {c['scroll']}; min-width: 28px;
    border-radius: 5px; }}
QScrollBar::handle:horizontal:hover {{ background: {c['scroll_hover']}; }}
QScrollBar::handle:horizontal:pressed {{ background: {c['scroll_hover']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0; border: none; background: none; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
"""


# ---------------------------------------------------------------- 悬浮面板
def _floating_qss(c):
    check = _check(c)
    search = _search(c, 12)
    return f"""
QWidget#floatingPanel {{ background: transparent; border: none; }}
QFrame#panelCard {{ background: {c['surface']}; border: 1px solid {c['border_strong']};
    border-radius: 16px; }}
QWidget#floatingHeader {{ background: {c['surface_alt']}; border: none;
    border-top-left-radius: 15px; border-top-right-radius: 15px;
    border-bottom: 1px solid {c['border']}; }}
QLabel#floatingTitle {{ color: {c['text']}; font-weight: 700; font-size: 14px;
    background: transparent; }}
QLabel#statusText {{ color: {c['chip_text']}; background: {c['chip_bg']};
    border: 1px solid {c['chip_border']}; border-radius: 8px; padding: 1px 7px;
    font-size: 10px; font-weight: 600; }}
QWidget#floatingBody {{ background: {c['surface']}; border: none;
    border-bottom-left-radius: 15px; border-bottom-right-radius: 15px; }}
QScrollArea#phraseScroll, QWidget#phraseViewport, QWidget#listHost {{
    background: {c['surface']}; border: none; }}
QFrame#phraseRow {{ background: {c['surface']}; border: 1px solid {c['border']};
    border-radius: 10px; }}
QFrame#phraseRow:hover {{ background: {c['row_hover']}; border-color: {c['border_strong']}; }}
QFrame#phraseRow[current="true"] {{ background: {c['selected']};
    border-color: {c['primary']}; }}
QFrame#phraseRow[current="true"] QLabel#phraseText {{ color: {c['selected_text']}; }}
QFrame#rowAccent {{ background: {c['primary']}; border: none;
    border-top-left-radius: 9px; border-bottom-left-radius: 9px; }}
QLabel#phraseText {{ color: {c['text']}; background: transparent; border: none; }}
QLabel#rowTag {{ color: {c['chip_text']}; background: {c['chip_bg']};
    border: 1px solid {c['chip_border']}; border-radius: 5px; padding: 0px 5px;
    font-size: 10px; font-weight: 600; }}
QPushButton#rowAction {{ color: {c['text_soft']}; background: transparent;
    border: 1px solid {c['border']}; border-radius: 7px; padding: 2px 4px;
    min-height: 20px; max-height: 24px; font-size: 11px; font-weight: 600; }}
QPushButton#rowAction:hover {{ background: {c['selected']}; border-color: {c['primary']};
    color: {c['selected_text']}; }}
QPushButton#rowAction:pressed {{ background: {c['pressed_bg']}; }}
QPushButton#rowType {{ color: {c['on_primary']}; background: {c['primary']};
    border: 1px solid {c['primary']}; border-radius: 7px; padding: 2px 4px;
    min-height: 20px; max-height: 24px; font-size: 11px; font-weight: 700; }}
QPushButton#rowType:hover {{ background: {c['primary_hover']}; border-color: {c['primary_hover']}; }}
QPushButton#rowType:pressed {{ background: {c['primary_pressed']}; }}
QLineEdit#search {{ background: {c['surface']}; color: {c['text']};
    border: 1px solid {c['border_strong']}; border-radius: 9px;
    padding: 5px 12px 5px 34px; min-height: 20px; font-size: 12px;
    background-image: url("{search}"); background-repeat: no-repeat;
    background-position: left center;
    selection-background-color: {c['selected']}; selection-color: {c['selected_text']}; }}
QLineEdit#search:focus {{ border: 2px solid {c['primary']}; padding: 4px 11px 4px 33px; }}
QPushButton#primaryPause {{ background: {c['surface']}; color: {c['text_soft']};
    border: 1px solid {c['border_strong']}; border-radius: 8px; padding: 4px 10px;
    text-align: center; font-weight: 600; font-size: 12px; }}
QPushButton#primaryPause:hover {{ background: {c['hover_tint']}; border-color: {c['primary']};
    color: {c['text']}; }}
QPushButton#primaryPause:pressed {{ background: {c['pressed_bg']}; }}
QPushButton#primaryPause[paused="true"] {{ background: {c['warn']}; color: {c['on_primary']};
    border-color: {c['warn']}; }}
QPushButton#primaryPause[paused="true"]:hover {{ background: {c['warn']};
    color: {c['on_primary']}; }}
QPushButton#titleAction {{ color: {c['title_action_text']}; border: none; border-radius: 7px;
    font-size: 13px; font-weight: 600; background: {c['title_action_bg']}; }}
QToolButton#titleAction {{ color: {c['title_action_text']}; border: none; border-radius: 7px;
    font-size: 14px; font-weight: 600; background: {c['title_action_bg']}; padding: 0px; }}
QToolButton#titleAction:hover {{ background: {c['title_action_hover']}; }}
QToolButton#titleAction:pressed {{ background: {c['title_action_checked']}; }}
QToolButton#titleAction:checked {{ background: {c['title_action_checked']}; }}
QPushButton#titleAction:hover {{ background: {c['title_action_hover']}; }}
QPushButton#titleAction:pressed {{ background: {c['title_action_checked']}; }}
QPushButton#titleAction:checked {{ background: {c['title_action_checked']}; }}

QFrame#settingsPopup {{ background: {c['surface']}; border: 1px solid {c['border_strong']};
    border-radius: 12px; }}
QFrame#settingsPopup QLabel {{ color: {c['text']}; background: transparent; }}
QFrame#settingsPopup QCheckBox {{ color: {c['text']}; background: transparent; spacing: 8px; }}
QFrame#settingsPopup QCheckBox::indicator {{ width: 16px; height: 16px;
    border: 1px solid {c['border_strong']}; border-radius: 5px; background: {c['surface']}; }}
QFrame#settingsPopup QCheckBox::indicator:hover {{ border-color: {c['primary']}; }}
QFrame#settingsPopup QCheckBox::indicator:checked {{ background: {c['primary']};
    border-color: {c['primary']}; image: url({check}); }}
QFrame#settingsPopup QSpinBox {{ background: {c['surface_alt']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 7px; padding: 2px 6px; min-width: 52px; }}
QFrame#settingsPopup QSpinBox:focus {{ border-color: {c['primary']}; }}
QFrame#settingsPopup QSpinBox::up-button, QFrame#settingsPopup QSpinBox::down-button {{
    width: 0px; border: none; background: transparent; }}
QFrame#settingsPopup QSpinBox::up-arrow, QFrame#settingsPopup QSpinBox::down-arrow {{
    width: 0px; height: 0px; }}
QFrame#settingsPopup QSlider::groove:horizontal {{ height: 4px; background: {c['muted']};
    border-radius: 2px; }}
QFrame#settingsPopup QSlider::sub-page:horizontal {{ background: {c['primary']};
    border-radius: 2px; }}
QFrame#settingsPopup QSlider::handle:horizontal {{ background: {c['primary']}; width: 14px;
    margin: -5px 0; border-radius: 7px; }}
QFrame#settingsPopup QSlider::handle:horizontal:hover {{ background: {c['primary_hover']}; }}
QLabel#settingsLabel {{ color: {c['text_soft']}; font-weight: 700; font-size: 12px; }}
"""


# ---------------------------------------------------------------- 应用速启
def _launcher_qss(c):
    check = _check(c)
    search = _search(c, 16)
    return f"""
QDialog#launcher {{ background: transparent; border: none; }}
QFrame#launcherCard {{ background: {c['surface']}; border: 1px solid {c['border_strong']};
    border-radius: 18px; }}
QLineEdit#launcherSearch {{ background: {c['surface_alt']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 11px;
    padding: 6px 14px 6px 44px; font-size: 15px;
    background-image: url("{search}"); background-repeat: no-repeat;
    background-position: left center;
    selection-background-color: {c['selected']}; selection-color: {c['selected_text']}; }}
QLineEdit#launcherSearch:focus {{ border: 2px solid {c['primary']};
    padding: 5px 13px 5px 43px; }}
QListWidget#launcherList {{ background: transparent; color: {c['text']};
    border: none; outline: none; padding: 2px; }}
QListWidget#launcherList::item {{ padding: 4px 10px; border-radius: 9px; }}
QListWidget#launcherList::item:hover:!selected {{ background: {c['row_hover']}; }}
QListWidget#launcherList::item:selected {{ background: {c['selected']};
    color: {c['selected_text']}; }}
QLabel#launcherError {{ color: {c['danger']}; font-size: 12px; background: transparent; }}
QLabel#hint {{ color: {c['muted_text']}; font-size: 12px; background: transparent; }}
QPushButton#launcherHidden {{ color: {c['primary']}; background: transparent; border: none;
    padding: 2px 6px; font-size: 12px; font-weight: 600; }}
QPushButton#launcherHidden:hover {{ color: {c['primary_hover']}; }}

QDialog {{ background: {c['bg']}; color: {c['text']}; font-size: 13px; }}
QDialog QLabel {{ color: {c['text']}; background: transparent; }}
QLabel#hiddenTitle {{ color: {c['text_soft']}; font-weight: 700; }}
QListWidget#hiddenList {{ background: {c['surface']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 9px; outline: none; padding: 4px; }}
QListWidget#hiddenList::item {{ padding: 6px 8px; border-radius: 6px; }}
QListWidget#hiddenList::item:selected {{ background: {c['selected']};
    color: {c['selected_text']}; }}
QListWidget#hiddenList::indicator {{ width: 15px; height: 15px;
    border: 1px solid {c['border_strong']}; border-radius: 4px; background: {c['surface']}; }}
QListWidget#hiddenList::indicator:checked {{ background: {c['primary']};
    border-color: {c['primary']}; image: url({check}); }}
QDialog QPushButton {{ background: {c['surface']}; color: {c['text_soft']};
    border: 1px solid {c['border_strong']}; border-radius: 9px; padding: 6px 18px;
    font-weight: 600; font-size: 13px; }}
QDialog QPushButton:hover {{ background: {c['hover_tint']}; border-color: {c['primary']};
    color: {c['text']}; }}
QDialog QPushButton:default {{ background: {c['primary']}; color: {c['on_primary']};
    border-color: {c['primary']}; }}
QDialog QPushButton:default:hover {{ background: {c['primary_hover']};
    border-color: {c['primary_hover']}; color: {c['on_primary']}; }}
QDialog QPushButton:disabled {{ color: {c['disabled']}; background: {c['muted']};
    border-color: {c['border']}; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px 4px 0;
    border: none; }}
QScrollBar::handle:vertical {{ background: {c['scroll']}; min-height: 28px; border-radius: 5px; }}
QScrollBar::handle:vertical:hover {{ background: {c['scroll_hover']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: none;
    background: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{ background: transparent; height: 10px;
    margin: 0 4px 2px 4px; border: none; }}
QScrollBar::handle:horizontal {{ background: {c['scroll']}; min-width: 28px;
    border-radius: 5px; }}
QScrollBar::handle:horizontal:hover {{ background: {c['scroll_hover']}; }}
QScrollBar::handle:horizontal:pressed {{ background: {c['scroll_hover']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0; border: none; background: none; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
"""


def build_stylesheet(theme_index: int, scope: str = "main") -> str:
    c = _resolve(theme_index)
    parts = []
    if scope in ("main", "all"):
        parts.append(_main_qss(c))
    if scope in ("dialog", "all"):
        parts.append(_dialog_qss(c))
    if scope in ("dialog", "main", "all"):
        parts.append(_titlebar_qss(c))
    if scope in ("picker", "all"):
        parts.append(_picker_qss(c))
    if scope in ("launcher", "all"):
        parts.append(_launcher_qss(c))
    if scope in ("floating", "all"):
        parts.append(_floating_qss(c))
    # 托盘菜单、右键菜单与速启弹窗分属不同作用域，QMenu 规则需各自带上
    if scope in ("main", "dialog", "launcher", "all"):
        parts.append(_menu_qss(c))
    return "\n".join(parts)


# 浮动面板复用主窗口的基础与滚动条样式，面板专属规则必须排在最后才不被覆盖
def floating_stylesheet(theme_index: int) -> str:
    c = _resolve(theme_index)
    return "\n".join([_main_qss(c), _titlebar_qss(c), _floating_qss(c)])


def _card_qss(c):
    """无边框圆角卡片（选择器弹窗等）。"""
    return f"""
QDialog#picker {{ background: transparent; border: none; }}
QFrame#pickerCard {{ background: {c['surface']}; border: 1px solid {c['border_strong']};
    border-radius: 16px; }}
"""


def card_stylesheet(theme_index: int) -> str:
    """供无边框圆角窗口使用的补充样式（可在既有样式之后追加）。"""
    return _card_qss(_resolve(theme_index))
