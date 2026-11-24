"""
utils/paths.py
集中管理專案路徑 (Project Paths)
所有路徑皆為絕對路徑，以本檔位置往上推導專案根目錄。
"""

import os
import shutil

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")
DATA_DIR = os.path.join(PROJECT_DIR, "data")
LOGS_DIR = os.path.join(DATA_DIR, "logs")

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
CREDENTIALS_PATH = os.path.join(DATA_DIR, "credentials.json")
TOKEN_PATH = os.path.join(DATA_DIR, "token.json")

_LEGACY_FILES = ("config.json", "credentials.json", "token.json")


def _logger():
    """延遲取得 logger（logger 會延遲匯入本模組，避免循環匯入）"""
    from utils.logger import get_logger
    return get_logger(__name__)


def asset_path(name):
    """回傳 assets 資料夾下檔案的絕對路徑"""
    return os.path.join(ASSETS_DIR, name)


def qss_url(path):
    """回傳可放入 QSS url(...) 的路徑 (反斜線轉正斜線)"""
    return str(path).replace("\\", "/")


def ensure_data_dirs():
    """建立 data/ 與 data/logs/"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)


def migrate_legacy_files():
    """將舊版放在專案根目錄的機密／設定檔搬進 data/。
    僅在根目錄有檔、data/ 內沒有時才搬；兩邊都存在時不動（不覆蓋、不刪除）。
    每個檔案各自處理，單一失敗不影響其他檔。
    回傳 {"moved": [...], "skipped_both_exist": [...], "failed": [(name, 錯誤訊息), ...]}"""
    result = {"moved": [], "skipped_both_exist": [], "failed": []}
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception as e:
        _logger().exception("建立 data/ 失敗")
        for name in _LEGACY_FILES:
            result["failed"].append((name, str(e)))
        return result

    for name in _LEGACY_FILES:
        old_path = os.path.join(PROJECT_DIR, name)
        new_path = os.path.join(DATA_DIR, name)
        try:
            if not os.path.exists(old_path):
                continue
            if os.path.exists(new_path):
                result["skipped_both_exist"].append(name)
                _logger().warning(f"{name} 根目錄與 data/ 皆存在，未搬移（請手動確認）")
                continue
            shutil.move(old_path, new_path)
            result["moved"].append(name)
            _logger().info(f"已將舊檔 {name} 搬移至 data/")
        except Exception as e:
            result["failed"].append((name, str(e)))
            _logger().exception(f"搬移 {name} 失敗")
    return result
