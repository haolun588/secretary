"""
scripts/render_preview.py
離屏渲染各畫面成 PNG，供目視檢查樣式（不連網、不讀 data/、不碰 Registry）。

用法：
    python scripts/render_preview.py [--out 輸出資料夾]
"""

import argparse
import os
import sys
import tempfile
import traceback
from datetime import date, datetime, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# offscreen 平台預設找不到系統字型，指向 Windows 字型資料夾讓中文可正常渲染
if sys.platform == "win32":
    os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt6.QtCore import QObject, Qt, pyqtSignal  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout, QHBoxLayout,  # noqa: E402
                             QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget)

from ui import icons, theme  # noqa: E402
from ui.styles import apply_app_style, repolish  # noqa: E402
from utils.paths import PROJECT_DIR  # noqa: E402


# ---------------------------------------------------------------- 假資料

def _iso(d, hh=None, mm=0):
    if hh is None:
        return d.strftime("%Y-%m-%d")
    return datetime(d.year, d.month, d.day, hh, mm).strftime("%Y-%m-%dT%H:%M:%S")


def make_fake_events(today=None):
    """以今天為基準產生假行程：全天多日、定時、重疊、三種等級、同日多筆。"""
    today = today or date.today()
    d = lambda n: today + timedelta(days=n)  # noqa: E731
    events = []

    def add(title, start, end, all_day, priority, location="", notes=""):
        events.append({"id": f"fake{len(events)}", "title": title, "all_day": all_day,
                       "start": start, "end": end, "priority": priority,
                       "location": location, "notes": notes, "color_id": None})

    add("專題報告", _iso(d(-1)), _iso(d(1)), True, "major", "", "三天的全天行程")
    add("出差", _iso(d(3)), _iso(d(5)), True, "medium")
    add("生日", _iso(d(10)), _iso(d(10)), True, "minor")
    add("晨會", _iso(today, 9), _iso(today, 10), False, "medium", "會議室 A")
    add("設計討論", _iso(today, 9, 30), _iso(today, 11), False, "major", "線上")
    add("站立會議", _iso(today, 9, 45), _iso(today, 10, 15), False, "minor")
    add("午餐", _iso(today, 12), _iso(today, 13), False, "minor")
    add("健身", _iso(today, 18), _iso(today, 19, 30), False, "minor")
    add("跨日夜班", _iso(d(2), 22), _iso(d(3), 0), False, "medium")
    for i in range(5):
        add(f"同日事項 {i + 1}", _iso(d(7), 8 + i), _iso(d(7), 9 + i), False, ("major", "medium", "minor")[i % 3])
    add("季度檢討", _iso(d(20), 14), _iso(d(20), 16), False, "major", "大會議室")
    return events


class FakeStore(QObject):
    """EventStore 的替身：同名 signals 與方法，全部不連網。"""

    events_changed = pyqtSignal(list)
    sync_state_changed = pyqtSignal(str, str)
    operation_failed = pyqtSignal(str, str)
    operation_succeeded = pyqtSignal(str)
    auth_state_changed = pyqtSignal(bool)

    def __init__(self, parent=None, authenticated=True, with_events=True):
        super().__init__(parent)
        self._events = make_fake_events() if with_events else []
        self._authenticated = authenticated

    @property
    def is_authenticated(self):
        return self._authenticated

    @property
    def is_authorizing(self):
        return False

    def events(self):
        return list(self._events)

    def start(self):
        pass

    def authorize(self):
        pass

    def check_connection(self):
        pass

    def logout(self):
        pass

    def set_range(self, start, end_excl):
        pass

    def ensure_month(self, year, month):
        pass

    def refresh(self):
        pass

    def add_event(self, data):
        pass

    def update_event(self, event_id, data):
        pass

    def delete_event(self, event_id):
        pass

    def shutdown(self):
        pass


class FakeConfig:
    """ConfigManager 的替身：不讀寫磁碟。"""

    def load_config(self):
        return {"water_enabled": True, "autostart": False, "interval_minutes": 30,
                "minimize_to_tray": True}

    def save_config(self, data):
        return True


# ---------------------------------------------------------------- 畫面

def _section_label(text):
    lbl = QLabel(text)
    lbl.setProperty("role", "section")
    return lbl


def build_components():
    from ui.components import IconButton, SegmentedControl, SyncStatusBadge

    root = QWidget()
    layout = QVBoxLayout(root)
    layout.setContentsMargins(theme.SPACE_5, theme.SPACE_5, theme.SPACE_5, theme.SPACE_5)
    layout.setSpacing(theme.SPACE_3)

    layout.addWidget(_section_label("按鈕 variant（一般 / 停用）"))
    row = QHBoxLayout()
    for variant in ("primary", "secondary", "ghost", "danger"):
        for disabled in (False, True):
            btn = QPushButton(variant + (" 停用" if disabled else ""))
            btn.setProperty("variant", variant)
            btn.setEnabled(not disabled)
            row.addWidget(btn)
    soft = QPushButton("danger soft")
    soft.setProperty("variant", "danger")
    soft.setProperty("soft", "true")
    row.addWidget(soft)
    row.addStretch(1)
    layout.addLayout(row)

    layout.addWidget(_section_label("輸入元件"))
    row = QHBoxLayout()
    line = QLineEdit()
    line.setPlaceholderText("行程標題")
    row.addWidget(line)
    filled = QLineEdit("已輸入的文字")
    row.addWidget(filled)
    combo = QComboBox()
    combo.addItems(["中", "大", "小"])
    row.addWidget(combo)
    spin = QSpinBox()
    spin.setRange(1, 180)
    spin.setValue(30)
    spin.setSuffix(" 分鐘")
    row.addWidget(spin)
    layout.addLayout(row)

    row = QHBoxLayout()
    for text, checked in (("核取方塊", True), ("核取方塊", False)):
        chk = QCheckBox(text)
        chk.setChecked(checked)
        row.addWidget(chk)
    for checked in (True, False):
        sw = QCheckBox("開關")
        sw.setProperty("variant", "switch")
        sw.setChecked(checked)
        row.addWidget(sw)
    seg = SegmentedControl([("month", "月"), ("week", "週"), ("day", "日")])
    seg.set_current("week")
    row.addWidget(seg)
    row.addStretch(1)
    layout.addLayout(row)

    layout.addWidget(_section_label("SyncStatusBadge 各狀態與 IconButton"))
    row = QHBoxLayout()
    for state in ("idle", "authorizing", "syncing", "ok", "offline", "error"):
        badge = SyncStatusBadge()
        badge.set_state(state, state)
        row.addWidget(badge)
    row.addWidget(IconButton("chevron-left", "上一個"))
    row.addWidget(IconButton("chevron-right", "下一個"))
    row.addWidget(IconButton("settings", "設定"))
    row.addStretch(1)
    layout.addLayout(row)

    layout.addWidget(_section_label("全部圖示"))
    names = sorted(f[:-4] for f in os.listdir(os.path.join(PROJECT_DIR, "assets", "icons"))
                   if f.endswith(".svg"))
    grid = QGridLayout()
    grid.setSpacing(theme.SPACE_3)
    for i, name in enumerate(names):
        cell = QVBoxLayout()
        pic = QLabel()
        pic.setPixmap(icons.pixmap(name, theme.TEXT_PRIMARY, theme.ICON_MD * 2))
        pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cap = QLabel(name)
        cap.setProperty("role", "muted")
        cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cell.addWidget(pic)
        cell.addWidget(cap)
        holder = QWidget()
        holder.setLayout(cell)
        grid.addWidget(holder, i // 8, i % 8)
    layout.addLayout(grid)
    layout.addStretch(1)
    root.resize(900, 560)
    return root


def _build_main_window():
    from ui.main_window import MainWindow
    win = MainWindow(FakeConfig(), FakeStore())
    win.sidebar.set_countdown(8 * 60 + 42)
    win.water_view.set_countdown(8 * 60 + 42)
    return win


def _build_calendar_main(mode="month", with_events=True):
    """主視窗（日曆頁）：以假 store 推送行程與同步狀態。"""
    from ui.main_window import MainWindow
    store = FakeStore(with_events=with_events)
    win = MainWindow(FakeConfig(), store)
    win.sidebar.set_countdown(8 * 60 + 42)
    store.events_changed.emit(store.events())
    store.sync_state_changed.emit("ok", "已同步")
    win.calendar_view.set_view_mode(mode)
    return win


def build_main_month():
    return _build_calendar_main("month")


def build_main_week():
    return _build_calendar_main("week")


def build_main_day():
    return _build_calendar_main("day")


def build_main_month_empty():
    return _build_calendar_main("month", with_events=False)


def build_main_shell():
    return _build_main_window()


def build_main_water():
    win = _build_main_window()
    cfg = FakeConfig().load_config()
    win.water_view.chk_water_enabled.setChecked(cfg["water_enabled"])
    win.water_view.spin_interval.setValue(cfg["interval_minutes"])
    win.sidebar.btn_water.click()
    return win


def _build_settings(authenticated):
    from ui.nav_sidebar import PAGE_SETTINGS
    from ui.main_window import MainWindow
    store = FakeStore(authenticated=authenticated)
    win = MainWindow(FakeConfig(), store)
    win.sidebar.set_countdown(8 * 60 + 42)
    win.sidebar.set_active_page(PAGE_SETTINGS)
    cfg = FakeConfig().load_config()
    view = win.settings_view
    view.chk_autostart.setChecked(cfg["autostart"])
    view.chk_minimize_to_tray.setChecked(cfg["minimize_to_tray"])
    store.auth_state_changed.emit(authenticated)
    return win


def build_settings():
    return _build_settings(False)


def build_settings_connected():
    return _build_settings(True)


def _sample_event(all_day=False):
    for evt in make_fake_events():
        if bool(evt["all_day"]) == all_day and evt["priority"] in ("major", "medium"):
            return evt
    raise RuntimeError("找不到範例行程")


def build_dialog_new():
    from PyQt6.QtCore import QDate
    from ui.calendar_dialog import CalendarDialog
    return CalendarDialog(default_date=QDate.currentDate())


def build_dialog_edit():
    from ui.calendar_dialog import CalendarDialog
    return CalendarDialog(event_data=_sample_event(all_day=False))


def build_dialog_allday():
    from ui.calendar_dialog import CalendarDialog
    return CalendarDialog(event_data=_sample_event(all_day=True))


def build_confirm_delete():
    from ui.calendar_dialog import ConfirmDeleteDialog
    return ConfirmDeleteDialog("專題報告")


def build_toast_water():
    from ui.toast_window import ToastWindow
    return ToastWindow(
        title="該喝水了", message="久坐一段時間了，起來喝杯水、活動一下吧。", kind="water",
        actions=[("延後 10 分鐘", lambda: None), ("已喝", lambda: None)])


def build_toast_danger():
    from ui.toast_window import ToastWindow
    return ToastWindow(title="同步失敗", message="無法連線到 Google 日曆，請檢查網路後再試一次。",
                       kind="danger")


def build_tray_menu_preview():
    from ui.tray_menu import build_tray_menu
    noop = lambda: None  # noqa: E731
    return build_tray_menu({"show": noop, "test_water": noop, "settings": noop, "quit": noop})


# 名稱 -> (建構函式, 寬, 高)；寬或高為 None 時依內容 adjustSize
SCREENS = {
    "components": (build_components, 900, 560),
    "main_shell_1180x740": (build_main_shell, theme.WINDOW_W, theme.WINDOW_H),
    "main_shell_960x620": (build_main_shell, theme.WINDOW_MIN_W, theme.WINDOW_MIN_H),
    "main_water": (build_main_water, theme.WINDOW_W, theme.WINDOW_H),
    "main_month_1180x740": (build_main_month, theme.WINDOW_W, theme.WINDOW_H),
    "main_month_960x620": (build_main_month, theme.WINDOW_MIN_W, theme.WINDOW_MIN_H),
    "main_week": (build_main_week, theme.WINDOW_W, theme.WINDOW_H),
    "main_day": (build_main_day, theme.WINDOW_W, theme.WINDOW_H),
    "main_month_empty": (build_main_month_empty, theme.WINDOW_W, theme.WINDOW_H),
    "settings": (build_settings, theme.WINDOW_W, theme.WINDOW_H),
    "settings_connected": (build_settings_connected, theme.WINDOW_MIN_W, theme.WINDOW_MIN_H),
    "dialog_new": (build_dialog_new, None, None),
    "dialog_edit": (build_dialog_edit, None, None),
    "dialog_allday": (build_dialog_allday, None, None),
    "confirm_delete": (build_confirm_delete, None, None),
    "toast_water": (build_toast_water, None, None),
    "toast_danger": (build_toast_danger, None, None),
    "tray_menu": (build_tray_menu_preview, None, None),
}

# 頂層透明 / 彈出視窗：貼到 BG 底色畫布上再存檔
COMPOSITE_ON_BG = {"toast_water", "toast_danger", "tray_menu"}


def _load_preview_fonts():
    """offscreen 平台的字型後備是明體；預覽專用：手動載入微軟正黑體讓中文呈現與實機一致。"""
    from PyQt6.QtGui import QFontDatabase
    fonts_dir = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    for name in ("msjh.ttc", "segoeui.ttf"):
        path = os.path.join(fonts_dir, name)
        if os.path.isfile(path):
            QFontDatabase.addApplicationFont(path)


def _save_grab(widget, path, on_bg):
    pixmap = widget.grab()
    if not on_bg:
        return pixmap.save(path)
    from PyQt6.QtGui import QImage, QPainter
    from ui.styles import qcolor
    margin = theme.SPACE_5
    image = QImage(pixmap.width() + 2 * margin, pixmap.height() + 2 * margin,
                   QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(qcolor(theme.BG))
    painter = QPainter(image)
    painter.drawPixmap(margin, margin, pixmap)
    painter.end()
    return image.save(path)


def render_all(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    _load_preview_fonts()
    apply_app_style(app)
    # 預覽不要發出系統提示音
    from ui.toast_window import ToastWindow
    ToastWindow.play_notification_sound = lambda self: None
    written = []
    for name, (builder, w, h) in SCREENS.items():
        try:
            widget = builder()
            if w is not None and h is not None:
                widget.resize(w, h)
            widget.show()
            if w is None or h is None:
                widget.adjustSize()
            app.processEvents()
            path = os.path.join(out_dir, f"{name}.png")
            if _save_grab(widget, path, name in COMPOSITE_ON_BG):
                written.append(path)
            else:
                print(f"[略過] {name}: 存檔失敗")
            widget.close()
            widget.deleteLater()
        except Exception as e:  # noqa: BLE001  預覽腳本：單張失敗不影響其他
            print(f"[略過] {name}: {e}")
            traceback.print_exc()
    return written


def main():
    parser = argparse.ArgumentParser(description="離屏渲染 UI 預覽圖")
    parser.add_argument("--out", default=os.path.join(tempfile.gettempdir(), "secretary_preview"))
    args = parser.parse_args()
    for path in render_all(args.out):
        print(path)


if __name__ == "__main__":
    main()
