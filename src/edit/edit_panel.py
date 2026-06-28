from base.main_base_panel import BasePanel
from base.main_theme import ThemeStyle
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt

class EditPanel(BasePanel):
    def __init__(self, parent=None, context=None):
        super().__init__(parent, title_text="編輯", require_data_loading=False, context=context)
        self.init_ui()

    def init_ui(self):
        self.lbl_placeholder = QLabel("編輯功能\n(日後添加)")
        self.lbl_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_placeholder.setStyleSheet(f"color: {ThemeStyle.COLOR_TEXT_MUTED}; font-style: italic; font-size: 14px; margin-top: 20px;")
        
        self.controls_layout.addWidget(self.lbl_placeholder)
        self.controls_layout.addStretch()

    def get_package_name(self) -> str:
        return "edit_panel"

    def get_uuid(self) -> str:
        return "4e47a9e3-8287-48f8-b39f-26b669fcf72a"

    def serialize_config(self) -> dict:
        return {}

    def deserialize_config(self, data: dict) -> None:
        pass

    def set_enabled(self, enabled):
        pass
