"""
utils/config_manager.py
設定檔持久化管理模組 (JSON Config Storage)
負責存取 config.json 設定檔（包含提醒間隔分鐘數、開機自啟設定等）。
"""

import os
import json
from datetime import datetime

from utils.paths import CONFIG_PATH, DATA_DIR

DEFAULT_CONFIG = {
    "interval_minutes": 10,
    "autostart": True,
    "minimize_to_tray": True,
    "google_account": "",
    "last_updated": ""
}

class ConfigManager:
    @staticmethod
    def load_config():
        """讀取設定檔 config.json，若不存在或損壞則傳回預設設定"""
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 確保所有預設鍵值皆存在
                    config = DEFAULT_CONFIG.copy()
                    config.update(data)
                    return config
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [ConfigManager] 讀取設定檔失敗，使用預設值: {e}")
        
        return DEFAULT_CONFIG.copy()

    @staticmethod
    def save_config(config_data):
        """將設定資料寫入 config.json"""
        try:
            config = DEFAULT_CONFIG.copy()
            config.update(config_data)
            config["last_updated"] = datetime.now().isoformat()

            os.makedirs(DATA_DIR, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [ConfigManager] 寫入設定檔失敗: {e}")
            return False
