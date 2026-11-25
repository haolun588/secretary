"""
ui/mlb_view.py
MLB 頁：以 QWebEngineView 內嵌顯示 MLB 每日頁面。
第一次顯示此頁才載入網址（延遲載入），之後切回不重載；載入失敗時以提示文字取代網頁。
樣式由全域 QSS 負責（QWidget#MlbPage、QLabel[role="title"]、QPushButton[variant="secondary"]）。
"""

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QStackedLayout, QVBoxLayout, QWidget

from ui import theme

MLB_DAILY_URL = "https://haolun588.github.io/MLB-daily/index.html"

_LOAD_FAILED_TEXT = "無法載入 MLB 頁面，請檢查網路後按重新整理"


class MlbView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._loaded = False
        self.init_ui()

    def init_ui(self):
        self.setObjectName("MlbPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.SPACE_6, theme.SPACE_5, theme.SPACE_6, theme.SPACE_5)
        layout.setSpacing(theme.SPACE_3)

        header = QHBoxLayout()
        title = QLabel("MLB 每日", self)
        title.setProperty("role", "title")
        header.addWidget(title)
        header.addStretch(1)
        self.refresh_btn = QPushButton("重新整理", self)
        self.refresh_btn.setProperty("variant", "secondary")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.reload)
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)

        body = QWidget(self)
        self._body = QStackedLayout(body)
        self.web_view = None  # 延遲到第一次顯示才建立，避免啟動時就初始化 WebEngine
        self.error_label = QLabel(_LOAD_FAILED_TEXT, body)
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self._body.addWidget(self.error_label)
        layout.addWidget(body, 1)

    def ensure_loaded(self):
        """第一次呼叫時才建立 QWebEngineView 並載入網址；之後不重載。"""
        if self._loaded:
            return
        self._loaded = True
        self.web_view = QWebEngineView(self)
        self.web_view.loadFinished.connect(self.on_load_finished)
        # 網頁要開新視窗（target=_blank 等）時，交給系統瀏覽器處理
        self.web_view.page().newWindowRequested.connect(
            lambda request: QDesktopServices.openUrl(request.requestedUrl())
        )
        self._body.addWidget(self.web_view)
        self._body.setCurrentWidget(self.web_view)
        self.web_view.setUrl(QUrl(MLB_DAILY_URL))

    def showEvent(self, event):
        super().showEvent(event)
        self.ensure_loaded()

    def reload(self):
        if not self._loaded:
            self.ensure_loaded()
            return
        if self.web_view.url().isEmpty():
            self.web_view.setUrl(QUrl(MLB_DAILY_URL))
        else:
            self.web_view.reload()

    def on_load_finished(self, ok):
        self._body.setCurrentWidget(self.web_view if ok else self.error_label)
