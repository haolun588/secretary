"""
ui/tray_menu.py
系統匣右鍵選單（main.py 與預覽腳本共用）。樣式由全域 QSS 的 QMenu 區段負責。
"""

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu

from ui import icons, theme

# (handlers 的 key, 顯示文字, 圖示名稱)；None 代表分隔線
TRAY_MENU_ITEMS = (
    ("show", "顯示主視窗", "window"),
    ("test_water", "測試喝水提醒", "droplet"),
    ("settings", "設定", "settings"),
    None,
    ("quit", "結束", "power"),
)


def build_tray_menu(handlers, parent=None):
    """建立系統匣選單。handlers 為 {"show"/"test_water"/"settings"/"quit": callable}；
    缺少的 key 會建立停用的項目。回傳 QMenu（actions 以 menu.actions_by_key 取得）。"""
    menu = QMenu(parent)
    menu.actions_by_key = {}
    for item in TRAY_MENU_ITEMS:
        if item is None:
            menu.addSeparator()
            continue
        key, text, icon_name = item
        action = QAction(icons.icon(icon_name, theme.TEXT_SECONDARY, theme.ICON_SM), text, menu)
        callback = handlers.get(key)
        if callback is None:
            action.setEnabled(False)
        else:
            action.triggered.connect(lambda _checked=False, cb=callback: cb())
        menu.addAction(action)
        menu.actions_by_key[key] = action
    return menu
