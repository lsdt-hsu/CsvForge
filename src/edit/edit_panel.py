from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QStackedWidget,
    QWidget, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from base_panel import BasePanel

class EditPanel(BasePanel):
    request_filter = pyqtSignal(str, str, int, int) # method, text, col1, col2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        lbl_sec = QLabel("編輯過濾")
        lbl_sec.setObjectName("sectionHeader")
        layout.addWidget(lbl_sec)
        
        # 過濾方式下拉選單
        self.cmb_filter_method = QComboBox()
        self.cmb_filter_method.addItems([
            "全部",
            "範圍欄位─完全符合",
            "範圍欄位─包含",
            "範圍欄位─正規表達式",
            "欄位比對"
        ])
        self.cmb_filter_method.currentIndexChanged.connect(self.on_method_changed)
        layout.addWidget(QLabel("過濾方式："))
        layout.addWidget(self.cmb_filter_method)
        
        # 動態輸入區 (StackedWidget)
        self.filter_stacked = QStackedWidget()
        
        # 頁面 0: 空白 (全部)
        page_empty = QWidget()
        self.filter_stacked.addWidget(page_empty)
        
        # 頁面 1: 文字輸入框 (範圍欄位)
        page_text = QWidget()
        layout_text = QVBoxLayout(page_text)
        layout_text.setContentsMargins(0, 0, 0, 0)
        self.txt_filter_input = QLineEdit()
        self.txt_filter_input.setPlaceholderText("輸入過濾文字或正規表達式")
        layout_text.addWidget(self.txt_filter_input)
        self.filter_stacked.addWidget(page_text)
        
        # 頁面 2: 欄位比對下拉選單
        page_col = QWidget()
        layout_col = QVBoxLayout(page_col)
        layout_col.setContentsMargins(0, 0, 0, 0)
        self.cmb_col1 = QComboBox()
        self.cmb_col2 = QComboBox()
        layout_col.addWidget(QLabel("欄位一："))
        layout_col.addWidget(self.cmb_col1)
        layout_col.addWidget(QLabel("欄位二："))
        layout_col.addWidget(self.cmb_col2)
        self.filter_stacked.addWidget(page_col)
        
        layout.addWidget(self.filter_stacked)
        
        # 開始過濾按鈕
        self.btn_start_filter = QPushButton("開始過濾")
        self.btn_start_filter.clicked.connect(self.on_filter_clicked)
        layout.addWidget(self.btn_start_filter)
        
        layout.addStretch()

    def on_method_changed(self, idx):
        if idx == 0:
            self.filter_stacked.setCurrentIndex(0)
        elif 1 <= idx <= 3:
            self.filter_stacked.setCurrentIndex(1)
        elif idx == 4:
            self.filter_stacked.setCurrentIndex(2)
            
    def update_column_dropdowns(self, num_cols, headers=None):
        self.cmb_col1.clear()
        self.cmb_col2.clear()
        for i in range(num_cols):
            text = f"{i+1}. {headers[i]}" if headers and i < len(headers) else f"第 {i+1} 欄"
            self.cmb_col1.addItem(text, i) # userData contains 0-based index
            self.cmb_col2.addItem(text, i)
            
    def on_filter_clicked(self):
        method = self.cmb_filter_method.currentText()
        text = self.txt_filter_input.text()
        col1 = self.cmb_col1.currentData() if self.cmb_col1.count() > 0 else 0
        col2 = self.cmb_col2.currentData() if self.cmb_col2.count() > 0 else 0
        
        # 驗證
        if method in ("範圍欄位─完全符合", "範圍欄位─包含", "範圍欄位─正規表達式"):
            if not text.strip():
                QMessageBox.warning(self, "錯誤", "過濾文字不可為空。")
                return
            if method == "範圍欄位─正規表達式":
                import re
                try:
                    re.compile(text)
                except re.error:
                    QMessageBox.warning(self, "錯誤", "正規表達式語法錯誤。")
                    return
        elif method == "欄位比對":
            if col1 == col2:
                QMessageBox.warning(self, "錯誤", "欄位比對必須選擇不同的欄位。")
                return
                
        self.request_filter.emit(method, text, col1, col2)

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
