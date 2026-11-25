"""动态占位符与宏。

占位符：{date} {date:%Y年%m月%d日} {time} {datetime} {year} {month} {day}
        {hour} {minute} {second} {clipboard} {uuid}
宏：    {wait:500}（毫秒，写小数按秒） {key:Enter} {key:Ctrl+V} {ctrl+enter}
转义：  {{ 表示一个左花括号，}} 表示一个右花括号。
"""
import datetime
import re
import uuid

from . import inputsim
from . import winapi as W

_KEY_NAMES = {
    "enter": 0x0D, "return": 0x0D, "tab": 0x09, "esc": 0x1B, "escape": 0x1B,
    "space": 0x20, "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
    "insert": 0x2D, "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
}
for _i in range(1, 13):
    _KEY_NAMES["f%d" % _i] = 0x6F + _i

_MOD_NAMES = {
    "ctrl": W.MOD_CONTROL, "control": W.MOD_CONTROL,
    "alt": W.MOD_ALT, "shift": W.MOD_SHIFT, "win": W.MOD_WIN,
}

_FMT = {
    "date": "%Y-%m-%d",
    "time": "%H:%M:%S",
    "datetime": "%Y-%m-%d %H:%M:%S",
}


def _vk_of(name: str):
    name = (name or "").strip().lower()
    if name in _KEY_NAMES:
        return _KEY_NAMES[name]
    if len(name) == 1 and name.isascii() and name.isalnum():
        return ord(name.upper())
    return None


def _parse_key(spec: str):
    """解析 Enter / Ctrl+V / Ctrl+Shift+Left 这类按键组合。"""
    parts = [p for p in re.split(r"\s*\+\s*", (spec or "").strip()) if p]
    if not parts:
        return None
    mods = 0
    for part in parts[:-1]:
        mask = _MOD_NAMES.get(part.lower())
        if not mask:
            return None
        mods |= mask
    vk = _vk_of(parts[-1])
    if not vk:
        return None
    return mods, vk


def _resolve(token: str):
    """把一个 {...} 内的内容解析成动作元组；无法识别时返回 None。"""
    head, _, tail = token.partition(":")
    head_l = head.strip().lower()
    tail = tail.strip()

    now = datetime.datetime.now()
    if head_l == "year":
        return ("text", str(now.year))
    if head_l == "month":
        return ("text", "%02d" % now.month)
    if head_l == "day":
        return ("text", "%02d" % now.day)
    if head_l == "hour":
        return ("text", "%02d" % now.hour)
    if head_l == "minute":
        return ("text", "%02d" % now.minute)
    if head_l == "second":
        return ("text", "%02d" % now.second)
    if head_l in _FMT:
        fmt = tail or _FMT[head_l]
        try:
            return ("text", now.strftime(fmt))
        except ValueError:
            return ("text", now.strftime(_FMT[head_l]))
    if head_l == "clipboard":
        text = inputsim.clipboard_text()
        return ("text", text or "")
    if head_l == "uuid":
        return ("text", uuid.uuid4().hex)
    if head_l in ("wait", "sleep"):
        try:
            value = float(tail or "0")
        except ValueError:
            return None
        ms = int(value * 1000) if "." in tail else int(value)
        return ("wait", max(0, min(ms, 60000)))
    if head_l == "key":
        parsed = _parse_key(tail)
        return ("key",) + parsed if parsed else None
    if "+" in token or head_l in _KEY_NAMES:
        parsed = _parse_key(token)
        if parsed:
            return ("key",) + parsed
    return None


def parse_actions(text: str):
    """把文本拆成 [('text', str) | ('wait', ms) | ('key', mods, vk)]。"""
    segments = []
    buf = []
    i = 0
    length = len(text)
    while i < length:
        ch = text[i]
        if ch == "{":
            if text.startswith("{{", i):
                buf.append("{")
                i += 2
                continue
            end = text.find("}", i + 1)
            if end == -1:
                buf.append(ch)
                i += 1
                continue
            action = _resolve(text[i + 1:end])
            if action is None:
                buf.append(text[i:end + 1])
            else:
                if buf:
                    segments.append(("text", "".join(buf)))
                    buf = []
                segments.append(action)
            i = end + 1
        elif ch == "}" and text.startswith("}}", i):
            buf.append("}")
            i += 2
        else:
            buf.append(ch)
            i += 1
    if buf:
        segments.append(("text", "".join(buf)))
    return segments


def plain_text(text: str) -> str:
    """只保留文本部分（用于复制、预览），丢弃按键与等待。"""
    return "".join(seg[1] for seg in parse_actions(text) if seg[0] == "text")
