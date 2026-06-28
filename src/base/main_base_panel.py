# src/base/main_base_panel.py
from PyQt6.QtWidgets import QFrame, QVBoxLayout
from common_data.app_context import AppContext

class BasePanel(QFrame):

    def __init__(self, parent=None, title_text="", require_data_loading=True, context: AppContext = None):
        super().__init__(parent)
        self.context = context
        self.setObjectName("grpFrame")
        
        # 建立主要垂直佈局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(8)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.controls_layout = self.main_layout
