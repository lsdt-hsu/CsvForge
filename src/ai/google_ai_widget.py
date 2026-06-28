from PyQt6.QtWidgets import QWidget, QFormLayout, QLabel, QLineEdit, QComboBox
from PyQt6.QtCore import pyqtSignal
from plugin_sdk.theme import applyStandardLabelStyle, applyStandardLineEditStyle, applyStandardComboBoxStyle


class GoogleAiWidget(QWidget):
    """
    GoogleAiWidget — Google AI 控制區模組。
    
    管理 API KEY 與模型選擇，並於數值變更時發出 field_changed 信號。
    """
    field_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        google_layout = QFormLayout(self)
        google_layout.setContentsMargins(0, 0, 0, 0)
        google_layout.setSpacing(8)

        lbl_api_key = QLabel("API KEY：")
        applyStandardLabelStyle(lbl_api_key)
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_api_key.setPlaceholderText("請輸入 Gemini API KEY")
        applyStandardLineEditStyle(self.txt_api_key)
        
        google_layout.addRow(lbl_api_key, self.txt_api_key)

        lbl_google_model = QLabel("使用模型：")
        applyStandardLabelStyle(lbl_google_model)
        self.cb_google_model = QComboBox()
        self.cb_google_model.setEditable(True)
        self.cb_google_model.addItems(["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash"])
        applyStandardComboBoxStyle(self.cb_google_model)
        
        google_layout.addRow(lbl_google_model, self.cb_google_model)

        # 信號連接，向外轉發為 field_changed
        self.txt_api_key.textChanged.connect(self.field_changed)
        self.cb_google_model.currentIndexChanged.connect(self.field_changed)
        if self.cb_google_model.lineEdit():
            self.cb_google_model.lineEdit().textChanged.connect(self.field_changed)

    def set_enabled(self, enabled):
        self.setEnabled(enabled)

    def restore_from_config(self, cfg):
        self.txt_api_key.blockSignals(True)
        self.cb_google_model.blockSignals(True)
        if self.cb_google_model.lineEdit():
            self.cb_google_model.lineEdit().blockSignals(True)
        try:
            self.txt_api_key.setText(cfg.google_api_key)
            self.cb_google_model.setCurrentText(cfg.google_model)
        finally:
            self.txt_api_key.blockSignals(False)
            self.cb_google_model.blockSignals(False)
            if self.cb_google_model.lineEdit():
                self.cb_google_model.lineEdit().blockSignals(False)

    def save_to_config(self, cfg):
        cfg.google_api_key = self.txt_api_key.text()
        cfg.google_model = self.cb_google_model.currentText()
