"""
utils/logger.py
集中日誌設定 (Logging)
所有模組以 `logger = get_logger(__name__)` 取得 logger，不使用 print。
日誌寫入 data/logs/secretary.log（RotatingFileHandler，約 1MB x 3 份備份）。
pythonw 下 sys.stdout 可能為 None，僅在有 stdout 時才加 StreamHandler。

循環匯入處理：本模組頂層不 import utils.paths，
改在首次設定日誌時才延遲匯入取得 LOGS_DIR，因此 utils.paths 也可以安全使用本模組。
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

ROOT_LOGGER_NAME = "secretary"
LOG_FILE_NAME = "secretary.log"
MAX_BYTES = 1024 * 1024
BACKUP_COUNT = 3
THIRD_PARTY_LOGGERS = ("googleapiclient", "google.auth")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

_configured = False


def _default_log_dir():
    """延遲匯入 utils.paths，避免循環匯入"""
    from utils.paths import LOGS_DIR
    return LOGS_DIR


def setup_logging(log_dir=None):
    """設定專案根 logger ("secretary")。冪等：已設定過則直接略過。
    log_dir 預設為 utils.paths.LOGS_DIR。
    建立目錄或開檔失敗時不丟例外，退回只有 stream handler（或 NullHandler）。"""
    global _configured
    if _configured:
        return logging.getLogger(ROOT_LOGGER_NAME)
    _configured = True

    root = logging.getLogger(ROOT_LOGGER_NAME)
    root.setLevel(logging.INFO)
    root.propagate = False
    formatter = logging.Formatter(LOG_FORMAT)
    added = False

    try:
        target_dir = log_dir if log_dir is not None else _default_log_dir()
        os.makedirs(target_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(target_dir, LOG_FILE_NAME),
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
            delay=True,
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
        # 第三方套件的警告以上也寫入同一個日誌檔
        for name in THIRD_PARTY_LOGGERS:
            third = logging.getLogger(name)
            third.setLevel(logging.WARNING)
            third.addHandler(file_handler)
        added = True
    except (OSError, ImportError):
        pass

    if sys.stdout is not None:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)
        added = True

    if not added:
        root.addHandler(logging.NullHandler())
    return root


def get_logger(name=None):
    """取得專案 logger。name 通常傳入 __name__，會掛在 "secretary" 之下。"""
    setup_logging()
    if not name or name == ROOT_LOGGER_NAME or name.startswith(ROOT_LOGGER_NAME + "."):
        return logging.getLogger(name or ROOT_LOGGER_NAME)
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")


def _reset_for_tests():
    """移除所有 handler 並重設設定旗標（僅供測試使用）"""
    global _configured
    for name in (ROOT_LOGGER_NAME,) + THIRD_PARTY_LOGGERS:
        target = logging.getLogger(name)
        for handler in list(target.handlers):
            target.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
    _configured = False
