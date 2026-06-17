from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QWidget, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from base_panel import BasePanel

class EditPanel(BasePanel):
    request_filter = pyqtSignal(object, str, object, str) # compare_col, compare_method, compare_target, compare_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl_sec = QLabel("編輯過濾")
        lbl_sec.setObjectName("sectionHeader")
        layout.addWidget(lbl_sec)

        # 1. 比對欄位下拉選單
        self.lbl_compare_col = QLabel("比對欄位：")
        self.cmb_compare_col = QComboBox()
        self.cmb_compare_col.addItem("不過濾", "none")
        self.cmb_compare_col.addItem("所有欄位", "all")
        self.cmb_compare_col.addItem("來源-目標欄位", "range")
        self.cmb_compare_col.currentIndexChanged.connect(self.on_compare_col_changed)
        
        layout.addWidget(self.lbl_compare_col)
        layout.addWidget(self.cmb_compare_col)

        # 建立一個容器以群組「比對方式」與「比對目標」，便於一併隱藏/顯示
        self.filter_options_widget = QWidget()
        self.filter_options_layout = QVBoxLayout(self.filter_options_widget)
        self.filter_options_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_options_layout.setSpacing(8)

        # 2. 比對方式下拉選單
        self.lbl_compare_method = QLabel("比對方式：")
        self.cmb_compare_method = QComboBox()
        self.cmb_compare_method.addItems(["完全符合", "包含", "未包含", "正規表達式"])
        self.filter_options_layout.addWidget(self.lbl_compare_method)
        self.filter_options_layout.addWidget(self.cmb_compare_method)

        # 3. 比對目標下拉選單
        self.lbl_compare_target = QLabel("比對目標：")
        self.cmb_compare_target = QComboBox()
        self.cmb_compare_target.addItem("手動輸入", "manual")
        self.cmb_compare_target.currentIndexChanged.connect(self.on_compare_target_changed)
        self.filter_options_layout.addWidget(self.lbl_compare_target)
        self.filter_options_layout.addWidget(self.cmb_compare_target)

        # 4. 比對值輸入框 (手動輸入的子項目，採用內縮佈局且無 label)
        self.value_container = QWidget()
        value_layout = QHBoxLayout(self.value_container)
        value_layout.setContentsMargins(20, 0, 0, 0)  # 內縮 20 像素
        value_layout.setSpacing(0)
        self.txt_compare_value = QLineEdit()
        self.txt_compare_value.setPlaceholderText("輸入比對值或正規表達式")
        value_layout.addWidget(self.txt_compare_value)
        self.filter_options_layout.addWidget(self.value_container)

        layout.addWidget(self.filter_options_widget)

        # 開始過濾按鈕
        self.btn_start_filter = QPushButton("開始過濾")
        self.btn_start_filter.clicked.connect(self.on_filter_clicked)
        layout.addWidget(self.btn_start_filter)

        layout.addStretch()

        # 初始化控制項顯示狀態
        self.on_compare_col_changed(0)

    def on_compare_col_changed(self, idx):
        # 取得目前比對欄位的值
        col_type = self.cmb_compare_col.currentData()
        if col_type == "none":
            # 隱藏所有選項目標與輸入框
            self.filter_options_widget.setVisible(False)
        else:
            self.filter_options_widget.setVisible(True)
            # 根據比對目標決定輸入框是否顯示
            self.on_compare_target_changed(self.cmb_compare_target.currentIndex())

    def on_compare_target_changed(self, idx):
        target_type = self.cmb_compare_target.currentData()
        if target_type == "manual":
            self.value_container.setVisible(True)
        else:
            self.value_container.setVisible(False)

    def update_column_dropdowns(self, num_cols, headers=None):
        # 記下目前選取的狀態，以便重整時儘量保留
        old_col_idx = self.cmb_compare_col.currentIndex()
        old_target_idx = self.cmb_compare_target.currentIndex()

        # 1. 重整比對欄位
        self.cmb_compare_col.clear()
        self.cmb_compare_col.addItem("不過濾", "none")
        self.cmb_compare_col.addItem("所有欄位", "all")
        self.cmb_compare_col.addItem("來源-目標欄位", "range")
        for i in range(num_cols):
            text = f"{i+1}. {headers[i]}" if headers and i < len(headers) else f"第 {i+1} 欄"
            self.cmb_compare_col.addItem(text, i)  # userData contains 0-based index

        # 2. 重整比對目標
        self.cmb_compare_target.clear()
        self.cmb_compare_target.addItem("手動輸入", "manual")
        for i in range(num_cols):
            text = f"{i+1}. {headers[i]}" if headers and i < len(headers) else f"第 {i+1} 欄"
            self.cmb_compare_target.addItem(text, i)  # userData contains 0-based index

        # 還原或重設選取狀態
        if old_col_idx < self.cmb_compare_col.count():
            self.cmb_compare_col.setCurrentIndex(old_col_idx)
        else:
            self.cmb_compare_col.setCurrentIndex(0)

        if old_target_idx < self.cmb_compare_target.count():
            self.cmb_compare_target.setCurrentIndex(old_target_idx)
        else:
            self.cmb_compare_target.setCurrentIndex(0)

    def on_filter_clicked(self):
        compare_col = self.cmb_compare_col.currentData()
        compare_method = self.cmb_compare_method.currentText()
        compare_target = self.cmb_compare_target.currentData()
        compare_value = self.txt_compare_value.text()

        # 驗證
        if compare_col != "none":
            if compare_target == "manual":
                if compare_method == "正規表達式":
                    import re
                    try:
                        re.compile(compare_value)
                    except re.error as e:
                        QMessageBox.warning(self, "錯誤", f"正規表達式語法錯誤: {e}")
                        return
            else:
                # 欄位比對
                if compare_col == compare_target:
                    QMessageBox.warning(self, "錯誤", "欄位比對必須選擇不同的欄位。")
                    return
                
        self.request_filter.emit(compare_col, compare_method, compare_target, compare_value)

    def set_enabled(self, enabled):
        self.cmb_compare_col.setEnabled(enabled)
        self.cmb_compare_method.setEnabled(enabled)
        self.cmb_compare_target.setEnabled(enabled)
        self.txt_compare_value.setEnabled(enabled)
        self.btn_start_filter.setEnabled(enabled)

    def get_config(self) -> dict:
        return {
            "compare_col": self.cmb_compare_col.currentIndex(),
            "compare_method": self.cmb_compare_method.currentIndex(),
            "compare_target": self.cmb_compare_target.currentIndex(),
            "compare_value": self.txt_compare_value.text()
        }

    def set_config(self, config: dict):
        if "compare_col" in config:
            self.cmb_compare_col.setCurrentIndex(config["compare_col"])
        if "compare_method" in config:
            self.cmb_compare_method.setCurrentIndex(config["compare_method"])
        if "compare_target" in config:
            self.cmb_compare_target.setCurrentIndex(config["compare_target"])
        if "compare_value" in config:
            self.txt_compare_value.setText(config["compare_value"])

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
