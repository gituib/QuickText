"""短语数据存储：JSON 文件（与 3.2 版结构兼容）。"""
import json
import os
import shutil
import uuid

from PySide6.QtCore import QTimer

from .winapi import data_file, MOD_ALT, MOD_CONTROL, hotkey_text

_pinyin = None


def _pinyin_module():
    """拼音首字母表体积较大，搜索真正用到时再加载。"""
    global _pinyin
    if _pinyin is None:
        from . import pinyin
        _pinyin = pinyin
    return _pinyin

SAVE_DELAY = 700          # 连续使用时的写盘合并窗口（毫秒）

DEFAULT_SETTINGS = {
    "inputMode": 2,            # 0 = 逐字输入，1 = 剪贴板粘贴，2 = 自动（长文本用粘贴）
    "floatingPanelHeight": 420,
    "floatingPanelOpacity": 97,
    "floatingPanelShowCopy": True,
    "floatingPanelShowType": True,
    "floatingPanelSnapToEdge": True,
    "floatingPanelTextLines": 2,
    "floatingPanelWidth": 320,
    "floatingPanelX": 0,
    "floatingPanelY": 0,
    "pickerMods": MOD_CONTROL,
    "pickerRecentFirst": True,
    "pickerVk": 0x52,          # Ctrl+R 打开选择器
    "launcherMods": MOD_CONTROL | MOD_ALT,
    "launcherVk": 0x20,        # Ctrl+Alt+Space 打开应用速启
    "launcherIncludeNoise": False,
    "showFloatingPanel": False,
    "showMods": 0,
    "showVk": 0,               # 未设置则使用托盘菜单
    "startMinimized": False,
    "startWithWindows": False,
    "uiTheme": 1,              # 1 = 青色主题，0 = 经典
    "columnWidths": [150, 110, 110],
    "groupOrder": [],          # 手动调整的分组顺序，未列出的分组按名称排在后面
    "extraGroups": [],         # 已创建但还没有短语的空分组
    "hidePhraseText": True,    # 短语正文在界面上遮挡显示（表格/选择器/悬浮面板）
}

MAX_GROUP_LEN = 24
RESERVED_GROUPS = ("未分组", "全部短语")

MASK_CAP = 40                  # 遮挡圆点的上限，避免超长正文生成同样超长的字符串


def mask_text(text):
    """按字符数生成等长圆点，用于在界面上遮挡短语正文。"""
    return "•" * min(len(text or ""), MASK_CAP)


def new_phrase(name="", hotkey_mods=0, hotkey_vk=0, text="", enabled=True,
               alias="", group=""):
    return {
        "id": uuid.uuid4().hex,
        "name": name,
        "alias": str(alias or ""),
        "group": str(group or ""),
        "hotkeyMods": int(hotkey_mods),
        "hotkeyVk": int(hotkey_vk),
        "text": text,
        "enabled": bool(enabled),
        "lastUsed": 0,
    }


class StoreError(Exception):
    pass


class PhraseStore:
    def __init__(self, path=None):
        self.path = path or data_file()
        self.phrases = []
        self.settings = dict(DEFAULT_SETTINGS)
        self.recovered_from_backup = False
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(SAVE_DELAY)
        self._save_timer.timeout.connect(self._flush_scheduled)
        self.load()

    # ---------------------------------------------------------------- io
    @staticmethod
    def _read_file(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            raise StoreError("无法读取数据文件：%s" % exc) from exc
        if not isinstance(data, dict):
            raise StoreError("数据文件格式不正确。")
        return data

    def _apply(self, data):
        items = data.get("phrases") or []
        if not isinstance(items, list):
            items = []
        phrases = []
        for item in items:
            if not isinstance(item, dict):
                continue
            phrase = new_phrase(
                name=str(item.get("name") or ""),
                hotkey_mods=int(item.get("hotkeyMods") or 0),
                hotkey_vk=int(item.get("hotkeyVk") or 0),
                text=str(item.get("text") or ""),
                enabled=bool(item.get("enabled", True)),
                alias=str(item.get("alias") or ""),
                group=str(item.get("group") or ""),
            )
            phrase["id"] = str(item.get("id") or uuid.uuid4().hex)
            phrase["lastUsed"] = int(item.get("lastUsed") or 0)
            phrases.append(phrase)
        self.phrases = phrases
        settings = data.get("settings") or {}
        self.settings = dict(DEFAULT_SETTINGS)
        if isinstance(settings, dict):
            for key, value in settings.items():
                self.settings[key] = value

    def load(self):
        """优先读取主文件；主文件损坏时回退到最近一次自动备份。"""
        self.recovered_from_backup = False
        backup = self._backup_path()
        candidates = [self.path]
        if os.path.exists(backup):
            candidates.append(backup)
        first_error = None
        for path in candidates:
            if not os.path.exists(path):
                continue
            try:
                data = self._read_file(path)
            except StoreError as exc:
                if first_error is None:
                    first_error = exc
                continue
            self._apply(data)
            self.recovered_from_backup = path != self.path
            return
        if first_error is not None:
            raise first_error
        self.save()

    def save(self):
        payload = {
            "phrases": self.phrases,
            "settings": self.settings,
            "version": 1,
        }
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=4)
            os.replace(tmp, self.path)
        except OSError as exc:
            raise StoreError("无法写入数据文件：%s" % exc) from exc
        self._refresh_backup()

    def _backup_path(self):
        return self.path + ".bak"

    def _refresh_backup(self):
        """每次成功保存后同步一份备份，主文件损坏时可自动恢复。"""
        try:
            shutil.copy2(self.path, self._backup_path())
        except OSError:
            pass

    def schedule_save(self):
        """把连续的小改动合并为一次写盘。"""
        self._save_timer.start()

    def _flush_scheduled(self):
        try:
            self.save()
        except StoreError:
            pass

    def flush(self):
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._flush_scheduled()

    # ------------------------------------------------------------ query
    def find_by_text(self, text: str):
        for phrase in self.phrases:
            if phrase["text"] == text:
                return phrase
        return None

    def hotkey_owner(self, mods: int, vk: int, exclude_id=None):
        if not vk:
            return None
        for phrase in self.phrases:
            if phrase["id"] == exclude_id:
                continue
            if phrase["hotkeyVk"] == vk and (phrase["hotkeyMods"] & 0x0F) == (mods & 0x0F):
                return phrase
        return None

    def groups(self):
        """返回所有分组名：短语中出现的 + 手动新建的空分组，按用户排序。"""
        result = []
        for phrase in self.phrases:
            group = (phrase.get("group") or "").strip()
            if group and group not in result:
                result.append(group)
        for group in (self.settings.get("extraGroups") or []):
            group = str(group or "").strip()
            if group and group not in result:
                result.append(group)
        order = [str(g or "").strip() for g in (self.settings.get("groupOrder") or [])]
        ranked = {name: i for i, name in enumerate(order) if name}
        return sorted(result, key=lambda g: (ranked.get(g, len(order)), g))

    def group_counts(self):
        counts = {}
        for phrase in self.phrases:
            key = (phrase.get("group") or "").strip()
            counts[key] = counts.get(key, 0) + 1
        for group in self.groups():
            counts.setdefault(group, 0)
        return counts

    @staticmethod
    def check_group_name(name, existing=None):
        """校验分组名，返回 (是否合法, 规范化后的名称或错误说明)。"""
        clean = " ".join(str(name or "").split())
        if not clean:
            return False, "请输入分组名称。"
        if len(clean) > MAX_GROUP_LEN:
            return False, "分组名称请控制在 %d 个字以内。" % MAX_GROUP_LEN
        if any(ch in clean for ch in "/\\:*?\"<>|"):
            return False, "分组名称不能包含 / \\ : * ? \" < > | 这些字符。"
        if clean in RESERVED_GROUPS:
            return False, "「%s」是保留名称，换一个。" % clean
        if existing and clean in existing:
            return False, "已经存在同名分组「%s」。" % clean
        return True, clean

    def add_group(self, name):
        """新建分组（允许暂时没有短语），返回 (名称, 错误说明)。"""
        ok, value = self.check_group_name(name, set(self.groups()))
        if not ok:
            return None, value
        extras = list(self.settings.get("extraGroups") or [])
        if value not in extras:
            extras.append(value)
        self.settings["extraGroups"] = extras
        self.save()
        return value, ""

    def rename_group(self, old, new):
        """重命名分组，返回 (最终名称, 同步的短语数, 错误说明)。"""
        ok, value = self.check_group_name(new, set(self.groups()) - {old})
        if not ok:
            return old, 0, value
        if value == old:
            return old, 0, "新旧名称相同。"
        moved = 0
        for phrase in self.phrases:
            if (phrase.get("group") or "").strip() == old:
                phrase["group"] = value
                moved += 1
        self.settings["extraGroups"] = [value if g == old else g
                                        for g in (self.settings.get("extraGroups") or [])]
        self.settings["groupOrder"] = [value if g == old else g
                                       for g in (self.settings.get("groupOrder") or [])]
        self.save()
        return value, moved, ""

    def delete_group(self, name):
        """删除分组：组内短语转为未分组，返回受影响条数。"""
        if name not in self.groups():
            return 0, "分组不存在，可能已被删除。"
        dropped = 0
        for phrase in self.phrases:
            if (phrase.get("group") or "").strip() == name:
                phrase["group"] = ""
                dropped += 1
        self.settings["extraGroups"] = [g for g in (self.settings.get("extraGroups") or [])
                                        if g != name]
        self.settings["groupOrder"] = [g for g in (self.settings.get("groupOrder") or [])
                                       if g != name]
        self.save()
        return dropped, ""

    def set_group_order(self, names):
        order = [str(g or "").strip() for g in names if str(g or "").strip()]
        alive = set(self.groups())
        self.settings["groupOrder"] = [g for g in order if g in alive]
        self.save()

    def move_to_group(self, ids, group):
        """把选中的短语移动到指定分组；group 为空串表示未分组。返回移动条数。"""
        target = set(ids)
        if not target:
            return 0
        name = str(group or "").strip()
        if name and name not in self.groups():
            return 0
        moved = 0
        for phrase in self.phrases:
            if phrase["id"] in target and (phrase.get("group") or "").strip() != name:
                phrase["group"] = name
                moved += 1
        if moved:
            self.save()
        return moved

    def matches(self, phrase, keyword):
        """名称、缩写、分组、快捷键、内容或拼音首字母命中即算匹配。"""
        key = (keyword or "").strip().lower()
        if not key:
            return True
        fields = [phrase.get("name") or "", phrase.get("alias") or "",
                  phrase.get("group") or "",
                  hotkey_text(phrase["hotkeyMods"], phrase["hotkeyVk"]),
                  phrase.get("text") or ""]
        hay = " ".join(fields).lower()
        if key in hay:
            return True
        if not (key.isascii() and key.isalnum()):
            return False
        # 长文本只取前 500 字，避免每次搜索都计算整段拼音
        sample = " ".join([fields[0], fields[1], fields[2], fields[4][:500]])
        return key in _pinyin_module().initials(sample)

    def search(self, keyword: str, group=None):
        result = []
        for phrase in self.phrases:
            # group 为 None 表示不限分组，空串表示只看未分组短语
            if group is not None and (phrase.get("group") or "") != group:
                continue
            if self.matches(phrase, keyword):
                result.append(phrase)
        return result

    # ------------------------------------------------------------ mutate
    def add(self, phrase):
        self.phrases.append(phrase)
        self.save()

    def replace(self, phrase_id, phrase):
        for i, item in enumerate(self.phrases):
            if item["id"] == phrase_id:
                self.phrases[i] = phrase
                self.save()
                return True
        return False

    def remove(self, phrase_id):
        return self.remove_many([phrase_id]) > 0

    def remove_many(self, ids):
        target = set(ids)
        if not target:
            return 0
        before = len(self.phrases)
        self.phrases = [p for p in self.phrases if p["id"] not in target]
        removed = before - len(self.phrases)
        if removed:
            self.save()
        return removed

    def set_enabled(self, ids, enabled):
        target = set(ids)
        changed = False
        for phrase in self.phrases:
            if phrase["id"] in target and phrase["enabled"] != bool(enabled):
                phrase["enabled"] = bool(enabled)
                changed = True
        if changed:
            self.save()
        return changed

    def reorder(self, ids):
        """按给定 id 顺序重排全部短语；id 集合不一致时放弃。"""
        by_id = {p["id"]: p for p in self.phrases}
        if len(ids) != len(by_id) or set(ids) != set(by_id):
            return False
        self.phrases = [by_id[i] for i in ids]
        self.save()
        return True

    def touch(self, phrase_id):
        for phrase in self.phrases:
            if phrase["id"] == phrase_id:
                import time
                phrase["lastUsed"] = int(time.time())
                self.schedule_save()
                return

    def set_setting(self, key, value):
        self.settings[key] = value
        self.save()

    # ------------------------------------------------------------ import
    def import_payload(self, data):
        """返回 (new_phrases, skipped_duplicates, skipped_bad)。"""
        items = []
        if isinstance(data, dict):
            items = data.get("phrases") or []
        elif isinstance(data, list):
            items = data
        added, dup, bad = [], [], 0
        for item in items:
            if not isinstance(item, dict):
                bad += 1
                continue
            text = item.get("text")
            if text is None:
                text = item.get("content")
            if not isinstance(text, str) or not text:
                bad += 1
                continue
            if self.find_by_text(text) or any(p["text"] == text for p in added):
                dup.append(text)
                continue
            added.append(new_phrase(
                name=str(item.get("name") or ""),
                hotkey_mods=int(item.get("hotkeyMods") or 0),
                hotkey_vk=int(item.get("hotkeyVk") or 0),
                text=text,
                enabled=bool(item.get("enabled", True)),
                alias=str(item.get("alias") or ""),
                group=str(item.get("group") or ""),
            ))
            added[-1]["lastUsed"] = int(item.get("lastUsed") or 0)
        if added:
            self.phrases.extend(added)
            self.save()
        return added, dup, bad

    def export_payload(self):
        return {"phrases": self.phrases, "version": 1}
