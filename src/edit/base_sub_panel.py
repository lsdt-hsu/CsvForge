from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt
from plugin_sdk import theme

class BaseSubPanel(QWidget):
    # 定義對外通訊的 Signals
    expanded = pyqtSignal(object)  # 傳遞 self，通知主面板自己展開了
    # 通知主面板啟動 Worker (worker_instance, task_name, total, initial_log)
    request_run_worker = pyqtSignal(object, str, int, str) 

    def __init__(self, title_text: str, api, context, parent=None):
        super().__init__(parent)
        self.api = api
        self.context = context
        self._is_expanded = False
        self._is_working = False  # 追蹤此面板是否為當前任務發起者
        self._title_text = title_text
        
        self._setup_base_ui()

    def _setup_base_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 1. 標題折疊按鈕
        self.btn_toggle = QPushButton(f"▶ {self._title_text}")
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                text-align: left;
                font-weight: bold;
                font-size: {theme.getTitleFontSize()}px;
                color: {theme.getTitleTextColor()};
                padding: 5px 0px;
            }}
            QPushButton:hover {{
                color: #89ddff;
            }}
        """)
        self.btn_toggle.clicked.connect(self._on_toggle_clicked)
        self.main_layout.addWidget(self.btn_toggle)

        # 2. 內容容器 (子類別的 UI 都要加進這個 widget 的 layout 裡)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_widget.setVisible(False)  # 預設收合
        self.main_layout.addWidget(self.content_widget)

    def _on_toggle_clicked(self):
        self._is_expanded = not self._is_expanded
        self.content_widget.setVisible(self._is_expanded)
        icon = "▼" if self._is_expanded else "▶"
        self.btn_toggle.setText(f"{icon} {self._title_text}")
        
        if self._is_expanded:
            self.expanded.emit(self)

    def force_collapse(self):
        """提供給主面板的 API：強制收合此面板"""
        if self._is_expanded:
            self._is_expanded = False
            self.content_widget.setVisible(False)
            self.btn_toggle.setText(f"▶ {self._title_text}")

    def set_panel_enabled(self, global_enabled: bool) -> None:
        """
        統一的 UI 鎖定邏輯：
        子類別應覆寫此方法來鎖定輸入框，但必須呼叫 super().set_panel_enabled(global_enabled)。
        此處預留了狀態機邏輯：global_enabled || self._is_working
        """
        pass

    # --- 以下為子類別必須覆寫的虛擬方法 ---
    def get_config(self) -> dict:
        raise NotImplementedError

    def restore_config(self, data: dict) -> None:
        raise NotImplementedError

    def on_data_refreshed(self) -> None:
        raise NotImplementedError
