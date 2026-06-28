# demo_plugin/plugin.py
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QLineEdit
from base.main_base_panel import BasePanel

class PanelClass(BasePanel):
    def __init__(self, parent=None, context=None):
        super().__init__(parent, title_text="外掛示範面板", require_data_loading=True, context=context)
        
        # 1. 說明文字
        label = QLabel("這是一個功能完整的測試外掛")
        self.controls_layout.addWidget(label)
        
        # 2. 測試設定檔還原與儲存
        self.controls_layout.addWidget(QLabel("外掛自訂設定輸入欄："))
        self.txt_test = QLineEdit()
        self.txt_test.setPlaceholderText("請輸入測試文字...")
        self.controls_layout.addWidget(self.txt_test)
        
        # 3. 測試修改資料
        btn_modify = QPushButton("測試：修改 CSV 第 1 列第 1 欄資料")
        btn_modify.clicked.connect(self.modify_data)
        self.controls_layout.addWidget(btn_modify)
        
        # 4. 測試過濾資料
        btn_filter = QPushButton("測試：僅保留第 1, 3 列資料 (0-indexed 0, 2)")
        btn_filter.clicked.connect(self.apply_custom_filter)
        self.controls_layout.addWidget(btn_filter)
        
        self.controls_layout.addStretch()

    def get_uuid(self) -> str:
        return "test-plugin-uuid-12345"

    def get_package_name(self) -> str:
        return "demo_plugin"

    def serialize_config(self) -> dict:
        return {
            "saved_text": self.txt_test.text()
        }

    def deserialize_config(self, data: dict) -> None:
        if "saved_text" in data:
            self.txt_test.setText(data["saved_text"])

    def modify_data(self) -> None:
        if self.context and self.context.is_data_loaded:
            # 修改 CsvData 中的資料並觸發更新
            self.context.csv_data.update_cell(0, 0, "外掛修改成功！")
            self.write_log("INFO", "外掛已修改 CSV 第 1 列第 1 欄資料")

    def apply_custom_filter(self) -> None:
        if self.context and self.context.is_data_loaded:
            # 對 CsvData 套用自訂列索引過濾
            self.context.csv_data.set_filtered_indices([0, 2])
            self.write_log("INFO", "外掛已套用自訂資料過濾（僅保留第 0、2 列）")
