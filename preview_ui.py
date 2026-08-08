"""
preview_ui.py
Phase 2 UI 靜態模擬視覺展示腳本 (Static Mockup Preview Launcher)
可用於預覽與驗證主介面、左側選單、右側提醒側欄、設定頁面與右下角 3 秒淡出彈窗。
"""

import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # 全域 Qt 屬性與字型優化
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
