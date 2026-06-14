import csv
import os
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from base_panel import BasePanel
from utils import detect_encoding, detect_delimiter

PREVIEW_DEFAULT_SECTION_SIZE = 110
PREVIEW_VERTICAL_SECTION_SIZE = 28

class PreviewPanel(BasePanel):
    preview_loaded = pyqtSignal(int)  # 發送總行數給主視窗以更新結束行號佔位字

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rightFrame")
        self.setMinimumHeight(200)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        # 預覽標頭列（包含狀態訊息）
        preview_header_widget = QWidget()
        preview_header_layout = QHBoxLayout(preview_header_widget)
        preview_header_layout.setContentsMargins(0, 0, 0, 0)
        preview_header_layout.setSpacing(10)

        lbl_preview_title = QLabel("來源檔案預覽 (前 10 行)")
        lbl_preview_title.setObjectName("sectionHeader")
        preview_header_layout.addWidget(lbl_preview_title)

        preview_header_layout.addStretch()

        self.lbl_preview_status = QLabel("尚未選擇來源 CSV 檔案")
        self.lbl_preview_status.setObjectName("previewStatus")
        self.lbl_preview_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        preview_header_layout.addWidget(self.lbl_preview_status)

        layout.addWidget(preview_header_widget)

        self.table_preview = QTableWidget()
        self.table_preview.setRowCount(0)
        self.table_preview.setColumnCount(0)
        self.table_preview.horizontalHeader().setDefaultSectionSize(PREVIEW_DEFAULT_SECTION_SIZE)
        self.table_preview.verticalHeader().setDefaultSectionSize(PREVIEW_VERTICAL_SECTION_SIZE)
        layout.addWidget(self.table_preview)

    def clear_preview(self):
        self.table_preview.clear()
        self.table_preview.setRowCount(0)
        self.table_preview.setColumnCount(0)
        self.lbl_preview_status.setText("請選擇來源檔案，或來源檔案不存在")

    def load_preview(self, file_path):
        if not file_path or not os.path.exists(file_path):
            self.clear_preview()
            return

        try:
            encoding = detect_encoding(file_path)
            delimiter = detect_delimiter(file_path, encoding)
            
            rows = []
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                reader = csv.reader(f, delimiter=delimiter)
                for i, row in enumerate(reader):
                    if i >= 10:
                        break
                    rows.append(row)
            
            if not rows:
                self.lbl_preview_status.setText("來源檔案為空，無法進行預覽")
                return

            max_cols = max(len(r) for r in rows)
            
            self.table_preview.clear()
            self.table_preview.setRowCount(len(rows))
            self.table_preview.setColumnCount(max_cols)
            
            # 設定列與行標頭
            col_headers = [f"第 {i+1} 欄" for i in range(max_cols)]
            self.table_preview.setHorizontalHeaderLabels(col_headers)
            
            row_headers = [f"第 {i+1} 行" for i in range(len(rows))]
            self.table_preview.setVerticalHeaderLabels(row_headers)
            
            for r_idx, row in enumerate(rows):
                for c_idx in range(max_cols):
                    val = row[c_idx] if c_idx < len(row) else ""
                    item = QTableWidgetItem(val)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    self.table_preview.setItem(r_idx, c_idx, item)
            
            self.table_preview.resizeColumnsToContents()
            self.lbl_preview_status.setText(f"預覽載入完成 (編碼: {encoding}, 分隔符: '{delimiter}')")
            
            # 計算總行數並以 Signal 傳出
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                total_rows = sum(1 for _ in csv.reader(f, delimiter=delimiter))
            self.preview_loaded.emit(total_rows)

        except Exception as e:
            self.lbl_preview_status.setText(f"載入預覽失敗: {str(e)}")
