from PyQt6.QtWidgets import QVBoxLayout, QLabel
from base_panel import BasePanel

class EditPanel(BasePanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        lbl_sec = QLabel("編輯設定")
        lbl_sec.setObjectName("sectionHeader")
        layout.addWidget(lbl_sec)
        
        layout.addStretch()

    def set_enabled(self, enabled):
        # 暫無控制項，僅保留此 Method 供 ui.py 呼叫以避免 AttributeError
        pass

    def get_start_button_text(self, state: str) -> str:
        if state == "critical":
            return "停止載入"
        elif state == "disabled":
            return "正在停止..."
        return "載入"

    def handle_start_button_click(self, main_window, state: str):
        if state == "critical":
            main_window.cancel_task()
        else:
            main_window.start_task()
