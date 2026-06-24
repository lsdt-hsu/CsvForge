from base_panel import BasePanel
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt

class EditPanel(BasePanel):
    def __init__(self, parent=None, context=None):
        super().__init__(parent, title_text="編輯", require_data_loading=False, context=context)
        self.init_ui()

    def init_ui(self):
        self.lbl_placeholder = QLabel("編輯功能\n(日後添加)")
        self.lbl_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_placeholder.setStyleSheet("color: #565f89; font-style: italic; font-size: 14px; margin-top: 20px;")
        
        self.controls_layout.addWidget(self.lbl_placeholder)
        self.controls_layout.addStretch()

    def set_enabled(self, enabled):
        pass
