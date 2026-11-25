"""应用索引：扫描开始菜单与桌面的快捷方式与可执行文件，提供搜索、置顶、别名与隐藏。"""
import json
import os
import re
import time

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from . import pinyin, winapi as W

INDEX_FILE = "apps.json"
SAVE_DELAY = 700
RESCAN_AFTER = 600          # 秒：超过该时间再打开速启时后台重扫，本次仍用缓存
MAX_RESULTS = 60
APP_EXTS = (".lnk", ".exe")
NOISE_PREFIX = ("卸载", "uninstall")
# .exe 额外过滤安装/卸载程序，避免桌面上的安装包混进结果
EXE_NOISE_WORDS = ("setup", "install", "unins")
NOISE_WORDS = ("readme", "帮助", "help", "更新", "update", "网站", "文档", "repair")
_SOURCE_ORDER = {"user": 0, "common": 1, "desktop": 2}
_SPLIT = re.compile(r"[\s\-_·（）()\[\]/\\,，.。:：]+")


def index_file() -> str:
    return os.path.join(W.config_dir(), INDEX_FILE)


def scan_dirs():
    """返回 [(目录, 来源)]：用户/公共开始菜单 + 用户/公共桌面。"""
    appdata = os.environ.get("APPDATA") or ""
    programdata = os.environ.get("PROGRAMDATA") or ""
    home = os.path.expanduser("~")
    public = os.environ.get("PUBLIC") or ""
    dirs = [
        (os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs"), "user"),
        (os.path.join(programdata, r"Microsoft\Windows\Start Menu\Programs"), "common"),
        (os.path.join(home, "Desktop"), "desktop"),
    ]
    if public:
        dirs.append((os.path.join(public, "Desktop"), "desktop"))
    return [(d, s) for d, s in dirs if d and os.path.isdir(d)]


def is_noise(name: str, ext: str = ".lnk") -> bool:
    low = name.lower()
    if low.startswith(NOISE_PREFIX):
        return True
    if ext == ".exe" and (low.startswith(EXE_NOISE_WORDS) or low.endswith(EXE_NOISE_WORDS)):
        return True
    return any(word in low for word in NOISE_WORDS)


def acronym(name: str) -> str:
    """英文取每词首字母、中文段取拼音首字母：Visual Studio Code→vsc。"""
    out = []
    for token in _SPLIT.split(name):
        if not token:
            continue
        letters = pinyin.initials(token)
        if not letters:
            continue
        out.append(letters[0] if token[0].isascii() else letters)
    return "".join(out).lower()


def new_app(path: str, name: str, source: str) -> dict:
    return {
        "key": "lnk:" + path.lower(),
        "name": name,
        "path": path,
        "source": source,
        "alias": "",
        "pinned": False,
        "hidden": False,
        "useCount": 0,
        "lastUsed": 0,
    }


def collect_apps(include_noise=False):
    """在后台线程执行：逐目录收集 .lnk 与 .exe，同名按 用户>公共>桌面、快捷方式优先 去重。"""
    found = {}
    for base, source in scan_dirs():
        for root, _dirs, files in os.walk(base):
            for fname in files:
                name, ext = os.path.splitext(fname)
                ext = ext.lower()
                if ext not in APP_EXTS:
                    continue
                name = name.strip()
                if not name or (not include_noise and is_noise(name, ext)):
                    continue
                rank = (_SOURCE_ORDER.get(source, 9), 0 if ext == ".lnk" else 1)
                old = found.get(name.lower())
                if old is None or rank < old[3]:
                    found[name.lower()] = (os.path.join(root, fname), name, source, rank)
    return [(path, name, source) for path, name, source, _rank in found.values()]


class _ScanThread(QThread):
    def __init__(self, include_noise, parent=None):
        super().__init__(parent)
        self.include_noise = include_noise
        self.result = []
        self.ok = False

    def run(self):
        try:
            self.result = collect_apps(self.include_noise)
            self.ok = True
        except Exception:
            self.ok = False


class AppIndex(QObject):
    """应用清单的加载、扫描合并、评分搜索与元数据写盘。"""

    scan_finished = Signal(int, int, int)   # 新增、移除、总数

    def __init__(self, path=None):
        super().__init__()
        self.path = path or index_file()
        self.apps = []
        self.scannedAt = 0
        self._include_noise = False
        self._scanning = False
        self._thread = None
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(SAVE_DELAY)
        self._save_timer.timeout.connect(self._flush)
        self.load()

    # ---------------------------------------------------------------- io
    def load(self):
        data = {}
        try:
            with open(self.path, "r", encoding="utf-8-sig") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        self.scannedAt = int(data.get("scannedAt") or 0)
        apps = []
        for item in data.get("apps") or []:
            if not isinstance(item, dict) or not item.get("path"):
                continue
            app = new_app(str(item["path"]), str(item.get("name") or ""),
                          str(item.get("source") or "user"))
            app["key"] = str(item.get("key") or app["key"])
            app["alias"] = str(item.get("alias") or "")
            app["pinned"] = bool(item.get("pinned", False))
            app["hidden"] = bool(item.get("hidden", False))
            app["useCount"] = int(item.get("useCount") or 0)
            app["lastUsed"] = int(item.get("lastUsed") or 0)
            self._prepare(app)
            apps.append(app)
        self.apps = apps

    def _prepare(self, app):
        """预计算匹配字段，避免每次按键重复计算拼音。"""
        app["_name_l"] = app["name"].lower()
        app["_alias_l"] = app["alias"].lower()
        app["_pinyin"] = pinyin.initials(app["name"])
        app["_acronym"] = acronym(app["name"])

    def save(self):
        payload = {
            "version": 1,
            "scannedAt": int(self.scannedAt),
            "apps": [{k: v for k, v in app.items() if not k.startswith("_")}
                     for app in self.apps],
        }
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=4)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def schedule_save(self):
        self._save_timer.start()

    def _flush(self):
        try:
            self.save()
        except Exception:
            pass

    def flush(self):
        if self._save_timer.isActive():
            self._save_timer.stop()
            self.save()

    def stop(self):
        """退出前落盘并等后台扫描收尾，避免 QThread 被提前销毁。"""
        self.flush()
        thread = self._thread
        if thread is not None and thread.isRunning():
            thread.wait(2000)

    # -------------------------------------------------------------- scan
    def needs_scan(self) -> bool:
        return not self.apps or (time.time() - self.scannedAt) > RESCAN_AFTER

    def start_scan(self, include_noise=False):
        if self._scanning:
            return False
        self._scanning = True
        self._thread = _ScanThread(bool(include_noise), self)
        self._thread.finished.connect(self._on_scan_done)
        self._thread.start()
        return True

    def _on_scan_done(self):
        thread = self._thread
        self._scanning = False
        self._thread = None
        if thread is None:
            return
        if not thread.ok:
            thread.deleteLater()
            return
        found = thread.result
        thread.deleteLater()
        by_key = {app["key"]: app for app in self.apps}
        merged, seen, added = [], set(), 0
        for path, name, source in found:
            key = "lnk:" + path.lower()
            if key in seen:
                continue
            seen.add(key)
            app = by_key.get(key)
            if app is None:
                app = new_app(path, name, source)
                self._prepare(app)
                added += 1
            else:
                if app["name"] != name:
                    app["name"] = name
                    self._prepare(app)
                app["path"], app["source"] = path, source
            merged.append(app)
        removed = len(self.apps) - (len(merged) - added)
        merged.sort(key=lambda a: (not a["pinned"], a["name"].lower()))
        self.apps = merged
        self.scannedAt = int(time.time())
        self.save()
        self.scan_finished.emit(added, max(0, removed), len(self.apps))

    def rebuild(self):
        return self.start_scan(self._include_noise)

    def set_include_noise(self, include_noise):
        self._include_noise = bool(include_noise)

    # ------------------------------------------------------------ query
    def get(self, key):
        return next((app for app in self.apps if app["key"] == key), None)

    @staticmethod
    def _score(app, q):
        name, alias = app["_name_l"], app["_alias_l"]
        if q == name or (alias and q == alias):
            score = 1000
        elif name.startswith(q) or (alias and alias.startswith(q)):
            score = 900
        elif app["_acronym"].startswith(q):
            score = 850
        elif app["_pinyin"].startswith(q):
            score = 800
        elif q in name or (alias and q in alias):
            score = 700
        elif q in app["_pinyin"]:
            score = 600
        elif q in app["_acronym"]:
            score = 550
        else:
            return 0
        if app["pinned"]:
            score += 300
        score += min(int(app["useCount"] or 0), 20) * 5
        if app["lastUsed"]:
            days = (time.time() - app["lastUsed"]) / 86400.0
            if days <= 1:
                score += 40
            elif days <= 7:
                score += 20
            elif days <= 30:
                score += 10
        return score

    def visible_apps(self):
        return [app for app in self.apps if not app["hidden"]]

    def search(self, keyword, limit=MAX_RESULTS):
        q = (keyword or "").strip().lower()
        apps = self.visible_apps()
        if not q:
            apps.sort(key=lambda a: (not a["pinned"], -int(a["lastUsed"] or 0),
                                     -int(a["useCount"] or 0), a["name"].lower()))
            return apps[:limit]
        scored = []
        for app in apps:
            score = self._score(app, q)
            if score:
                scored.append((score, app))
        scored.sort(key=lambda pair: (-pair[0], len(pair[1]["name"]),
                                      pair[1]["name"].lower()))
        return [app for _score, app in scored[:limit]]

    def hidden_apps(self):
        return [app for app in self.apps if app["hidden"]]

    # ----------------------------------------------------------- mutate
    def record_use(self, key):
        app = self.get(key)
        if app is None:
            return
        app["useCount"] = int(app["useCount"] or 0) + 1
        app["lastUsed"] = int(time.time())
        self.schedule_save()

    def set_alias(self, key, alias):
        app = self.get(key)
        if app is None:
            return False
        app["alias"] = str(alias or "").strip()
        self._prepare(app)
        self.save()
        return True

    def set_pinned(self, key, pinned):
        app = self.get(key)
        if app is None:
            return False
        app["pinned"] = bool(pinned)
        self.save()
        return True

    def set_hidden(self, key, hidden):
        app = self.get(key)
        if app is None:
            return False
        app["hidden"] = bool(hidden)
        self.save()
        return True
