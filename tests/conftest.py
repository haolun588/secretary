import os
import shutil
import sys
import tempfile

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
