"""
utils/win_titlebar.py
Windows 深色標題列（只呼叫 DWM 視窗屬性，不碰 Registry）
"""

import sys

from utils.logger import get_logger

logger = get_logger(__name__)

# Windows 10 1809~1903 使用 19，之後使用 20
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19


def _is_supported():
    """只有 Windows 且非 offscreen 平台才有真正的視窗可設定。"""
    if sys.platform != "win32":
        return False
    from PyQt6.QtGui import QGuiApplication
    return QGuiApplication.platformName() != "offscreen"


def enable_dark_titlebar(widget):
    """對 widget 所屬的頂層視窗啟用深色標題列。
    成功回傳 True；非 Windows、offscreen 或失敗回傳 False，不 raise。"""
    try:
        if not _is_supported():
            return False
        import ctypes
        from ctypes import wintypes

        hwnd = int(widget.window().winId())
        func = ctypes.windll.dwmapi.DwmSetWindowAttribute
        func.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        func.restype = ctypes.c_long  # HRESULT
        value = ctypes.c_int(1)
        result = 1
        for attribute in (DWMWA_USE_IMMERSIVE_DARK_MODE, DWMWA_USE_IMMERSIVE_DARK_MODE_OLD):
            result = func(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))
            if result == 0:
                return True
        logger.debug(f"DwmSetWindowAttribute 失敗 HRESULT={result}")
        return False
    except Exception as e:
        logger.warning(f"啟用深色標題列失敗: {e}")
        return False
