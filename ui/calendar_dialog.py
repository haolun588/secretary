"""
ui/calendar_dialog.py
行程新增／編輯對話框（CalendarDialog）、刪除確認（ConfirmDeleteDialog）與日期選擇按鈕（DatePopupButton）。
樣式一律來自全域 QSS（ui/styles.py 的 _DIALOG 等區段）；此檔只處理版面與邏輯。
"""

from PyQt6.QtCore import QDate, QDateTime, QSize, QTime, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QGuiApplication, QIcon, QPainter, QPixmap, QTextCharFormat
from PyQt6.QtWidgets import (
    QCalendarWidget, QCheckBox, QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from ui import icons, theme
from ui.components import level_color
from ui.confirm_dialog import ConfirmDialog, DarkTitleDialog, apply_window_icon
from ui.styles import qcolor, repolish


_WEEKDAY_ZH = "一二三四五六日"  # QDate.dayOfWeek(): 1=週一 ... 7=週日；不依賴系統 locale


def _field_label(text, parent=None):
    lbl = QLabel(text, parent)
    lbl.setProperty("role", "field")
    return lbl


def _level_dot_icon(priority):
    """等級色點 icon（給 QComboBox 項目用）。"""
    screen = QGuiApplication.primaryScreen()
    dpr = float(screen.devicePixelRatio()) if screen is not None else 1.0
    size = theme.ICON_SM
    pm = QPixmap(int(round(size * dpr)), int(round(size * dpr)))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(qcolor(level_color(priority)))
    margin = theme.SPACE_1
    painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)
    painter.end()
    return QIcon(pm)


class ConfirmDeleteDialog(ConfirmDialog):
    """行程刪除確認對話框"""

    def __init__(self, title_name, parent=None):
        self.title_name = title_name
        super().__init__(
            window_title="確認刪除行程",
            heading="確認刪除此行程？",
            message=f"確定要刪除「{title_name}」嗎？",
            detail="此動作將同步從 Google 雲端日曆中永久移除。",
            confirm_text="刪除",
            parent=parent,
        )


class DatePopupButton(QPushButton):
    dateChanged = pyqtSignal(QDate)  # 只在使用者從彈出日曆選日期時發出；setDate() 不發出

    def __init__(self, default_date=None, parent=None):
        super().__init__(parent)
        self.setObjectName("DatePopupButton")
        self.selected_date = default_date or QDate.currentDate()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIcon(icons.icon("calendar", theme.TEXT_SECONDARY, theme.ICON_SM))
        self.setIconSize(QSize(theme.ICON_SM, theme.ICON_SM))
        self.update_text()
        self.clicked.connect(self.show_calendar_popup)

    def update_text(self):
        d = self.selected_date
        self.setText(f"{d.toString('yyyy/MM/dd')} 週{_WEEKDAY_ZH[d.dayOfWeek() - 1]}")

    def date(self):
        return self.selected_date

    def setDate(self, date):
        self.selected_date = date
        self.update_text()

    def _on_popup_date_clicked(self, date):
        """彈出日曆點選日期：更新顯示；與原日期不同時才發出 dateChanged"""
        changed = date != self.selected_date
        self.selected_date = date
        self.update_text()
        if changed:
            self.dateChanged.emit(date)

    def show_calendar_popup(self):
        popup = QDialog(self, Qt.WindowType.Popup)
        popup.setObjectName("DatePopup")

        layout = QVBoxLayout(popup)
        layout.setContentsMargins(theme.SPACE_2, theme.SPACE_2, theme.SPACE_2, theme.SPACE_2)

        cal = QCalendarWidget(popup)
        cal.setSelectedDate(self.selected_date)
        cal.setGridVisible(False)
        cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)

        weekend_fmt = QTextCharFormat()
        weekend_fmt.setForeground(qcolor(theme.ACCENT))
        weekend_fmt.setFontWeight(QFont.Weight.DemiBold)
        cal.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, weekend_fmt)
        cal.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, weekend_fmt)

        def on_date_clicked(date):
            popup.accept()
            self._on_popup_date_clicked(date)

        cal.clicked.connect(on_date_clicked)
        layout.addWidget(cal)

        global_pos = self.mapToGlobal(self.rect().bottomLeft())
        popup.move(global_pos.x(), global_pos.y() + theme.SPACE_1)
        popup.exec()


class CalendarDialog(DarkTitleDialog):
    def __init__(self, parent=None, event_data=None, default_date=None):
        super().__init__(parent)
        self.event_data = event_data or {}
        self.default_date = default_date if default_date is not None else QDate.currentDate()
        self.is_delete = False
        self._duration_minutes = 60  # 非全天模式的長度（分鐘）
        self._duration_days = 0  # 全天模式的長度（天數）
        self._linked_extra = None  # 連動時插入結束時間 combo 的非 30 分項目
        self._syncing = False  # 程式更新結束欄位時為 True，避免遞迴觸發連動
        self.init_ui()
        self.load_event_data()
        self._recompute_duration()
        self._connect_linkage()

    def _build_priority_combo(self):
        combo = QComboBox(self)
        combo.setIconSize(QSize(theme.ICON_SM, theme.ICON_SM))
        for key in ("major", "medium", "minor"):
            days = theme.PRIORITY_WINDOW_DAYS[key]
            combo.addItem(_level_dot_icon(key), f"{theme.PRIORITY_LABEL[key]} · 提前 {days} 天提醒", key)
        current_prio = self.event_data.get("priority", "medium")
        index = combo.findData(current_prio)
        combo.setCurrentIndex(index if index >= 0 else combo.findData("medium"))
        return combo

    @staticmethod
    def _time_combo(default_text, parent):
        combo = QComboBox(parent)
        for h in range(24):
            for m in (0, 30):
                combo.addItem(f"{h:02d}:{m:02d}")
        combo.setCurrentText(default_text)
        return combo

    def init_ui(self):
        self.setWindowTitle("編輯行程" if self.event_data else "新增行程")
        self.setFixedWidth(theme.DIALOG_WIDTH)
        apply_window_icon(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QWidget(self)
        grid = QGridLayout(body)
        grid.setContentsMargins(theme.SPACE_5, theme.SPACE_5, theme.SPACE_5, theme.SPACE_4)
        grid.setHorizontalSpacing(theme.SPACE_3)
        grid.setVerticalSpacing(theme.SPACE_1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        # 標題（全寬）
        self.title_input = QLineEdit(body)
        self.title_input.setPlaceholderText("行程標題")
        self.title_input.setText(self.event_data.get("title", ""))
        grid.addWidget(self.title_input, 0, 0, 1, 2)
        grid.setRowMinimumHeight(1, theme.SPACE_3)

        # 等級 + 全天
        grid.addWidget(_field_label("等級", body), 2, 0)
        self.priority_combo = self._build_priority_combo()
        grid.addWidget(self.priority_combo, 3, 0)

        self.all_day_chk = QCheckBox("全天", body)
        self.all_day_chk.setProperty("variant", "switch")
        self.all_day_chk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.all_day_chk.toggled.connect(self.on_all_day_toggled)
        grid.addWidget(self.all_day_chk, 3, 1)
        grid.setRowMinimumHeight(4, theme.SPACE_3)

        # 開始
        grid.addWidget(_field_label("開始", body), 5, 0, 1, 2)
        self.start_date_btn = DatePopupButton(self.default_date, body)
        self.start_time = self._time_combo("09:00", body)
        grid.addWidget(self.start_date_btn, 6, 0)
        grid.addWidget(self.start_time, 6, 1)
        grid.setRowMinimumHeight(7, theme.SPACE_3)

        # 結束
        grid.addWidget(_field_label("結束", body), 8, 0, 1, 2)
        self.end_date_btn = DatePopupButton(self.default_date, body)
        self.end_time = self._time_combo("10:00", body)
        grid.addWidget(self.end_date_btn, 9, 0)
        grid.addWidget(self.end_time, 9, 1)
        grid.setRowMinimumHeight(10, theme.SPACE_3)

        # 地點
        loc_label_row = QHBoxLayout()
        loc_label_row.setSpacing(theme.SPACE_1)
        loc_icon = QLabel(body)
        loc_icon.setPixmap(icons.pixmap("map-pin", theme.TEXT_MUTED, theme.ICON_SM))
        loc_label_row.addWidget(loc_icon)
        loc_label_row.addWidget(_field_label("地點", body))
        loc_label_row.addStretch(1)
        grid.addLayout(loc_label_row, 11, 0, 1, 2)
        self.location_input = QLineEdit(body)
        self.location_input.setPlaceholderText("地點（選填）")
        self.location_input.setText(self.event_data.get("location", ""))
        grid.addWidget(self.location_input, 12, 0, 1, 2)
        grid.setRowMinimumHeight(13, theme.SPACE_3)

        # 備註
        grid.addWidget(_field_label("備註", body), 14, 0, 1, 2)
        self.notes_input = QTextEdit(body)
        self.notes_input.setPlaceholderText("備註（選填）")
        self.notes_input.setPlainText(self.event_data.get("notes", ""))
        self.notes_input.setMinimumHeight(theme.CONTROL_H * 3)
        grid.addWidget(self.notes_input, 15, 0, 1, 2)

        root.addWidget(body, 1)

        # 按鈕列：左「刪除」（僅編輯），右「取消」「儲存」
        footer = QFrame(self)
        footer.setObjectName("DialogFooter")
        btn_layout = QHBoxLayout(footer)
        btn_layout.setContentsMargins(theme.SPACE_5, theme.SPACE_3, theme.SPACE_5, theme.SPACE_3)
        btn_layout.setSpacing(theme.SPACE_2)

        self.delete_btn = QPushButton("刪除", footer)
        self.delete_btn.setProperty("variant", "danger")
        self.delete_btn.setProperty("soft", "true")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        if not self.event_data:
            self.delete_btn.hide()
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch(1)

        self.cancel_btn = QPushButton("取消", footer)
        self.cancel_btn.setProperty("variant", "secondary")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("儲存", footer)
        self.save_btn.setProperty("variant", "primary")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.save_btn)

        root.addWidget(footer)

    def on_all_day_toggled(self, checked):
        self.start_time.setVisible(not checked)
        self.end_time.setVisible(not checked)
        self.start_time.setEnabled(not checked)
        self.end_time.setEnabled(not checked)
        # 長度依模式重新計算，並重跑狀態檢查（init 期間尚未有儲存鈕時略過）
        if hasattr(self, "save_btn"):
            self._recompute_duration()

    # ------------------------------------------------------------ 開始/結束連動

    def _connect_linkage(self):
        self.start_date_btn.dateChanged.connect(self._on_start_changed)
        self.start_time.currentIndexChanged.connect(self._on_start_changed)
        self.end_date_btn.dateChanged.connect(self._on_end_changed)
        self.end_time.currentIndexChanged.connect(self._on_end_changed)

    @staticmethod
    def _combo_time(combo):
        t = QTime.fromString(combo.currentText(), "HH:mm")
        return t if t.isValid() else QTime(0, 0)

    def _start_end_datetimes(self):
        """回傳 (開始, 結束) QDateTime；全天模式時間固定 00:00。"""
        if self.all_day_chk.isChecked():
            t_start = t_end = QTime(0, 0)
        else:
            t_start, t_end = self._combo_time(self.start_time), self._combo_time(self.end_time)
        spec = Qt.TimeSpec.UTC  # 牆上時間運算，避免夏令時間造成偏移
        return (QDateTime(self.start_date_btn.date(), t_start, spec),
                QDateTime(self.end_date_btn.date(), t_end, spec))

    def _recompute_duration(self):
        """依目前欄位重算長度（結束早於開始時維持原長度），並更新錯誤狀態。"""
        start, end = self._start_end_datetimes()
        if end >= start:
            if self.all_day_chk.isChecked():
                self._duration_days = start.date().daysTo(end.date())
            else:
                self._duration_minutes = start.secsTo(end) // 60
        self._update_validity()

    def _on_start_changed(self, *_):
        if self._syncing:
            return
        start, _end = self._start_end_datetimes()
        if self.all_day_chk.isChecked():
            new_end = start.addDays(self._duration_days)
        else:
            new_end = start.addSecs(self._duration_minutes * 60)
        self._syncing = True
        try:
            self.end_date_btn.setDate(new_end.date())
            if not self.all_day_chk.isChecked():  # 全天時結束時間欄位隱藏，保持原值
                self._link_end_time(new_end.time().toString("HH:mm"))
        finally:
            self._syncing = False
        self._update_validity()

    def _link_end_time(self, hhmm):
        """連動設定結束時間；清除先前連動插入、現已不用的非 30 分項目，避免累積"""
        extra = self._linked_extra
        if extra and extra != hhmm:
            i = self.end_time.findText(extra)
            if i >= 0:
                self.end_time.removeItem(i)
            self._linked_extra = None
        if self.end_time.findText(hhmm) < 0:
            self._linked_extra = hhmm
        self._select_time(self.end_time, hhmm)

    def _on_end_changed(self, *_):
        if self._syncing:
            return
        self._recompute_duration()

    def _update_validity(self):
        start, end = self._start_end_datetimes()
        invalid = end < start
        for w in (self.end_date_btn, self.end_time):
            w.setProperty("invalid", "true" if invalid else "false")
            repolish(w)
        self.save_btn.setEnabled(not invalid)

    @staticmethod
    def _select_time(combo, hhmm):
        """選取時間；不在 30 分清單中則插入該選項（依時間排序位置）"""
        index = combo.findText(hhmm)
        if index < 0:
            pos = combo.count()
            for i in range(combo.count()):
                if combo.itemText(i) > hhmm:
                    pos = i
                    break
            combo.insertItem(pos, hhmm)
            index = pos
        combo.setCurrentIndex(index)

    def load_event_data(self):
        """編輯模式：把既有行程帶入各欄位（新增模式維持預設）"""
        ev = self.event_data
        if not ev:
            return
        start = str(ev.get("start", ""))
        end = str(ev.get("end") or start)
        all_day = bool(ev["all_day"]) if "all_day" in ev else ("T" not in start)

        s_date = QDate.fromString(start[:10], "yyyy-MM-dd")
        e_date = QDate.fromString(end[:10], "yyyy-MM-dd")
        if s_date.isValid():
            self.start_date_btn.setDate(s_date)
        if e_date.isValid():
            self.end_date_btn.setDate(e_date)
        elif s_date.isValid():
            self.end_date_btn.setDate(s_date)

        if not all_day:
            if len(start) >= 16:
                self._select_time(self.start_time, start[11:16])
            if len(end) >= 16:
                self._select_time(self.end_time, end[11:16])
        self.all_day_chk.setChecked(all_day)

    def _validation_error(self):
        """回傳錯誤訊息；通過驗證回傳 None（end < start 視為錯誤）"""
        start_d = self.start_date_btn.date()
        end_d = self.end_date_btn.date()
        if self.all_day_chk.isChecked():
            if end_d < start_d:
                return "結束日期不能早於開始日期"
            return None
        start_key = (start_d.toString("yyyy-MM-dd"), self.start_time.currentText())
        end_key = (end_d.toString("yyyy-MM-dd"), self.end_time.currentText())
        if end_key < start_key:
            return "結束時間不能早於開始時間"
        return None

    def accept(self):
        error = self._validation_error()
        if error:
            QMessageBox.warning(self, "時間設定有誤", error)
            return
        super().accept()

    def on_delete_clicked(self):
        title_name = self.title_input.text().strip() or "此行程"
        confirm_dlg = ConfirmDeleteDialog(title_name, parent=self)
        if confirm_dlg.exec() == QDialog.DialogCode.Accepted:
            self.is_delete = True
            self.done(2)

    def get_data(self):
        s_date_str = self.start_date_btn.date().toString("yyyy-MM-dd")
        e_date_str = self.end_date_btn.date().toString("yyyy-MM-dd")
        all_day = self.all_day_chk.isChecked()
        if all_day:
            start, end = s_date_str, e_date_str
        else:
            start = f"{s_date_str}T{self.start_time.currentText()}:00"
            end = f"{e_date_str}T{self.end_time.currentText()}:00"

        title = self.title_input.text().strip()
        if not title:
            title = self.event_data.get("title") or "新行程"

        return {
            "title": title,
            "priority": self.priority_combo.currentData(),
            "all_day": all_day,
            "start": start,
            "end": end,
            "location": self.location_input.text().strip(),
            "notes": self.notes_input.toPlainText().strip()
        }
