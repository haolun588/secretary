"""
ui/calendar_dialog.py
行程新增與編輯對話框 (Add / Edit Event Modal Dialog) - 包含美化版暗黑風 ConfirmDeleteDialog
"""

import os
from PyQt6.QtCore import Qt, QDate, QTime, QDateTime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTextEdit, QCalendarWidget, QWidget
)
from PyQt6.QtGui import QIcon, QFont, QColor, QTextCharFormat

class ConfirmDeleteDialog(QDialog):
    """客製化暗黑紫紅風格行程刪除確認對話框"""
    def __init__(self, title_name, parent=None):
        super().__init__(parent)
        self.title_name = title_name
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("確認刪除行程")
        self.setFixedSize(420, 210)

        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(project_dir, "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QDialog {
                background-color: #1c1c24;
                border: 1px solid #8b5cf6;
                border-radius: 16px;
            }
            QLabel#ConfirmTitle {
                color: #f43f5e;
                font-size: 16px;
                font-weight: 800;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
            }
            QLabel#ConfirmMsg {
                color: #ffffff;
                font-size: 13.5px;
                font-weight: 600;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
            }
            QLabel#ConfirmSub {
                color: #a0a0ab;
                font-size: 12px;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
            }
            QPushButton#CancelBtn {
                background-color: #2a2a36;
                color: #a0a0ab;
                font-weight: bold;
                font-size: 13.5px;
                border: none;
                border-radius: 10px;
                padding: 10px 24px;
            }
            QPushButton#CancelBtn:hover {
                background-color: #3f3f46;
                color: #ffffff;
            }
            QPushButton#DeleteConfirmBtn {
                background-color: #f43f5e;
                color: #ffffff;
                font-weight: bold;
                font-size: 13.5px;
                border: none;
                border-radius: 10px;
                padding: 10px 24px;
            }
            QPushButton#DeleteConfirmBtn:hover {
                background-color: #e11d48;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)

        # 頂部列 (圖示 + 標題)
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        warn_icon = QLabel("⚠️", self)
        warn_icon.setStyleSheet("font-size: 22px; background: transparent; border: none;")
        top_row.addWidget(warn_icon)

        title_lbl = QLabel("確認刪除此行程？", self)
        title_lbl.setObjectName("ConfirmTitle")
        title_lbl.setStyleSheet("background: transparent; border: none;")
        top_row.addWidget(title_lbl)
        top_row.addStretch(1)

        layout.addLayout(top_row)

        # 訊息內容
        msg_lbl = QLabel(f"確定要刪除「{self.title_name}」嗎？", self)
        msg_lbl.setObjectName("ConfirmMsg")
        msg_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(msg_lbl)

        sub_lbl = QLabel("此動作將同步從 Google 雲端日曆中永久移除。", self)
        sub_lbl.setObjectName("ConfirmSub")
        sub_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(sub_lbl)

        layout.addStretch(1)

        # 底部按鈕列 [取消] [確定刪除]
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)

        cancel_btn = QPushButton("取消", self)
        cancel_btn.setObjectName("CancelBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        confirm_btn = QPushButton("確定刪除", self)
        confirm_btn.setObjectName("DeleteConfirmBtn")
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.clicked.connect(self.accept)
        btn_row.addWidget(confirm_btn)

        layout.addLayout(btn_row)


class DatePopupButton(QPushButton):
    def __init__(self, default_date=None, parent=None):
        super().__init__(parent)
        self.selected_date = default_date or QDate.currentDate()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_text()
        self.clicked.connect(self.show_calendar_popup)

    def update_text(self):
        self.setText(f"📅  {self.selected_date.toString('yyyy / MM / dd (ddd)')}")

    def date(self):
        return self.selected_date

    def setDate(self, date):
        self.selected_date = date
        self.update_text()

    def show_calendar_popup(self):
        popup = QDialog(self, Qt.WindowType.Popup)

        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        up_img = os.path.join(project_dir, "assets", "arrow_up.png").replace("\\", "/")
        down_img = os.path.join(project_dir, "assets", "arrow_down.png").replace("\\", "/")

        popup.setStyleSheet(f"""
            QDialog {{
                background-color: #1c1c24;
                border: 1px solid #8b5cf6;
                border-radius: 14px;
            }}
            QCalendarWidget {{
                background-color: #1c1c24;
                border: none;
                min-width: 340px;
                min-height: 280px;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: #1c1c24;
                border-bottom: 1px solid #2a2a36;
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
                min-height: 48px;
            }}
            QCalendarWidget QToolButton {{
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 12px;
                background-color: transparent;
                border: none;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: #2a2a36;
                color: #8b5cf6;
            }}
            QCalendarWidget QSpinBox {{
                background-color: #121217;
                color: #ffffff;
                border: 1px solid #2a2a36;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                padding: 4px 34px 4px 10px;
                min-height: 36px;
            }}
            QCalendarWidget QSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 28px;
                height: 17px;
                background-color: #2a2a36;
                border-top-right-radius: 7px;
                margin: 1px 1px 0px 0px;
            }}
            QCalendarWidget QSpinBox::up-button:hover {{
                background-color: #8b5cf6;
            }}
            QCalendarWidget QSpinBox::up-arrow {{
                image: url('{up_img}');
                width: 12px;
                height: 12px;
            }}
            QCalendarWidget QSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 28px;
                height: 17px;
                background-color: #2a2a36;
                border-bottom-right-radius: 7px;
                margin: 0px 1px 1px 0px;
            }}
            QCalendarWidget QSpinBox::down-button:hover {{
                background-color: #8b5cf6;
            }}
            QCalendarWidget QSpinBox::down-arrow {{
                image: url('{down_img}');
                width: 12px;
                height: 12px;
            }}
            QCalendarWidget QHeaderView::section {{
                background-color: #1c1c24;
                color: #ffffff;
                font-weight: bold;
                padding: 6px 0px;
                border: none;
            }}
            QCalendarWidget QTableView {{
                background-color: #1c1c24;
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
                selection-background-color: #8b5cf6;
                selection-color: #ffffff;
                outline: 0;
            }}
        """)

        layout = QVBoxLayout(popup)
        layout.setContentsMargins(10, 10, 10, 10)

        cal = QCalendarWidget(popup)
        cal.setSelectedDate(self.selected_date)
        cal.setGridVisible(False)
        cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)

        purple_fmt = QTextCharFormat()
        purple_fmt.setForeground(QColor("#8b5cf6"))
        purple_fmt.setFontWeight(QFont.Weight.Bold)
        cal.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, purple_fmt)
        cal.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, purple_fmt)

        def on_date_clicked(date):
            self.selected_date = date
            self.update_text()
            popup.accept()

        cal.clicked.connect(on_date_clicked)
        layout.addWidget(cal)

        global_pos = self.mapToGlobal(self.rect().bottomLeft())
        popup.move(global_pos.x(), global_pos.y() + 4)
        popup.exec()


class CalendarDialog(QDialog):
    def __init__(self, parent=None, event_data=None):
        super().__init__(parent)
        self.event_data = event_data or {}
        self.is_delete = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("新增 / 編輯行程")
        self.setFixedSize(500, 640)

        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(project_dir, "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QDialog {
                background-color: #1c1c24;
                color: #ffffff;
            }
            QLabel {
                color: #a0a0ab;
                font-size: 13px;
                font-weight: 600;
                font-family: 'Segoe UI', 'Microsoft JhengHei UI', sans-serif;
                margin-top: 4px;
            }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #121217;
                border: 1px solid #2a2a36;
                border-radius: 8px;
                padding: 6px 12px;
                color: #ffffff;
                font-size: 13px;
                min-height: 38px;
                max-height: 38px;
            }
            QTextEdit {
                max-height: 75px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 26px;
                border-left: 1px solid #2a2a36;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 1px solid #8b5cf6;
            }
            QPushButton#DateBtn {
                background-color: #121217;
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                border: 1px solid #2a2a36;
                border-radius: 8px;
                padding: 6px 12px;
                text-align: left;
                min-height: 38px;
                max-height: 38px;
            }
            QPushButton#DateBtn:hover {
                border-color: #8b5cf6;
                background-color: #23232e;
            }
            QPushButton#SaveBtn {
                background-color: #8b5cf6;
                color: #ffffff;
                font-weight: bold;
                font-size: 13.5px;
                border: none;
                border-radius: 10px;
                padding: 10px 24px;
            }
            QPushButton#SaveBtn:hover {
                background-color: #7c3aed;
            }
            QPushButton#DeleteBtn {
                background-color: #f43f5e;
                color: #ffffff;
                font-weight: bold;
                font-size: 13.5px;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
            }
            QPushButton#DeleteBtn:hover {
                background-color: #e11d48;
            }
            QPushButton#CancelBtn {
                background-color: #2a2a36;
                color: #a0a0ab;
                font-weight: bold;
                font-size: 13.5px;
                border: none;
                border-radius: 10px;
                padding: 10px 24px;
            }
            QPushButton#CancelBtn:hover {
                background-color: #3f3f46;
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(10)

        title_lbl = QLabel("📌 行程詳細資訊", self)
        title_lbl.setStyleSheet("font-size: 17px; font-weight: 800; color: #8b5cf6; margin-bottom: 4px;")
        layout.addWidget(title_lbl)

        layout.addWidget(QLabel("行程標題"))
        self.title_input = QLineEdit(self)
        self.title_input.setPlaceholderText("請輸入行程名稱 (例如：季度專案報告)")
        self.title_input.setText(self.event_data.get("title", ""))
        layout.addWidget(self.title_input)

        layout.addWidget(QLabel("事件等級 (影響右側倒數提醒天數與色彩標籤)"))
        self.priority_combo = QComboBox(self)
        self.priority_combo.addItem("🔴 大事件 (提前 30 天/1個月提醒 - 紅色)", "major")
        self.priority_combo.addItem("🟡 中事件 (提前 7 天/1週提醒 - 黃色)", "medium")
        self.priority_combo.addItem("🟢 小事件 (提前 3 天提醒 - 綠色)", "minor")
        
        current_prio = self.event_data.get("priority", "medium")
        prio_map = {"major": 0, "medium": 1, "minor": 2}
        self.priority_combo.setCurrentIndex(prio_map.get(current_prio, 1))
        layout.addWidget(self.priority_combo)

        layout.addWidget(QLabel("開始時間"))
        start_row = QHBoxLayout()
        start_row.setSpacing(10)

        self.start_date_btn = DatePopupButton(QDate.currentDate(), self)
        self.start_date_btn.setObjectName("DateBtn")

        self.start_time = QComboBox(self)
        for h in range(24):
            for m in (0, 30):
                self.start_time.addItem(f"{h:02d}:{m:02d}")
        self.start_time.setCurrentText("09:00")

        start_row.addWidget(self.start_date_btn, stretch=3)
        start_row.addWidget(self.start_time, stretch=2)
        layout.addLayout(start_row)

        layout.addWidget(QLabel("結束時間"))
        end_row = QHBoxLayout()
        end_row.setSpacing(10)

        self.end_date_btn = DatePopupButton(QDate.currentDate(), self)
        self.end_date_btn.setObjectName("DateBtn")

        self.end_time = QComboBox(self)
        for h in range(24):
            for m in (0, 30):
                self.end_time.addItem(f"{h:02d}:{m:02d}")
        self.end_time.setCurrentText("10:00")

        end_row.addWidget(self.end_date_btn, stretch=3)
        end_row.addWidget(self.end_time, stretch=2)
        layout.addLayout(end_row)

        layout.addWidget(QLabel("地點"))
        self.location_input = QLineEdit(self)
        self.location_input.setPlaceholderText("請輸入地點 (例如：總部 A101 會議室)")
        self.location_input.setText(self.event_data.get("location", ""))
        layout.addWidget(self.location_input)

        layout.addWidget(QLabel("備註資訊"))
        self.notes_input = QTextEdit(self)
        self.notes_input.setPlaceholderText("請輸入行程詳細說明...")
        self.notes_input.setText(self.event_data.get("notes", ""))
        layout.addWidget(self.notes_input)

        layout.addStretch(1)

        # 底部右下角按鈕區 [取消] [🗑️ 刪除行程] [儲存行程]
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch(1)

        cancel_btn = QPushButton("取消", self)
        cancel_btn.setObjectName("CancelBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self.delete_btn = QPushButton("🗑️ 刪除行程", self)
        self.delete_btn.setObjectName("DeleteBtn")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        
        if not self.event_data:
            self.delete_btn.hide()

        btn_layout.addWidget(self.delete_btn)

        save_btn = QPushButton("儲存行程", self)
        save_btn.setObjectName("SaveBtn")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def on_delete_clicked(self):
        title_name = self.title_input.text().strip() or "此行程"
        confirm_dlg = ConfirmDeleteDialog(title_name, parent=self)
        if confirm_dlg.exec() == QDialog.DialogCode.Accepted:
            self.is_delete = True
            self.done(2)

    def get_data(self):
        s_date_str = self.start_date_btn.date().toString("yyyy-MM-dd")
        s_time_str = self.start_time.currentText()
        e_date_str = self.end_date_btn.date().toString("yyyy-MM-dd")
        e_time_str = self.end_time.currentText()

        return {
            "title": self.title_input.text().strip(),
            "priority": self.priority_combo.currentData(),
            "start": f"{s_date_str}T{s_time_str}:00",
            "end": f"{e_date_str}T{e_time_str}:00",
            "location": self.location_input.text().strip(),
            "notes": self.notes_input.toPlainText().strip()
        }
