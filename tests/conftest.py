import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # 必須在任何 Qt 匯入之前
import shutil
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# 測試期間日誌一律寫到暫存目錄，避免碰到真實的 data/logs/
# （被測模組在匯入時就會 get_logger，所以必須在 conftest 載入階段就導向）
from utils import logger as _logger_mod  # noqa: E402

_TEST_LOG_DIR = tempfile.mkdtemp(prefix="secretary_test_logs_")
_logger_mod._default_log_dir = lambda: _TEST_LOG_DIR


def pytest_sessionfinish(session, exitstatus):
    _logger_mod._reset_for_tests()
    shutil.rmtree(_TEST_LOG_DIR, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def _session_qapplication():
    """整個測試 session 持有同一個 QApplication（offscreen），避免模組間因 QCoreApplication / 被回收造成不一致。"""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception:
        yield None
        return
    app = QApplication.instance() or QApplication([])
    yield app
