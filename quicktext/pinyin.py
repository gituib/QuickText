"""拼音首字母搜索：内置常用汉字首字母表，不依赖第三方库。"""
from functools import lru_cache

from .pinyin_data import INITIALS

_CHAR_TO_LETTER = {}
for _letter, _chars in INITIALS.items():
    for _ch in _chars:
        _CHAR_TO_LETTER.setdefault(_ch, _letter)


@lru_cache(maxsize=8192)
def initials(text: str) -> str:
    """把文本转成拼音首字母串；英文数字原样保留，其他字符忽略。"""
    if not text:
        return ""
    out = []
    for ch in text:
        letter = _CHAR_TO_LETTER.get(ch)
        if letter:
            out.append(letter)
        elif ch.isascii() and ch.isalnum():
            out.append(ch.lower())
    return "".join(out)
