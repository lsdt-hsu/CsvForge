import csv
import os
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel, QTableWidget, QTableWidgetItem,
    QCheckBox
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
        self.cached_rows = []
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

        # 新增「第一行為標題」核取方塊
        self.chk_first_row_header = QCheckBox("第一行為標題")
        self.chk_first_row_header.setObjectName("chkFirstRowHeader")
        self.chk_first_row_header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_first_row_header.stateChanged.connect(self.on_header_checkbox_changed)
        preview_header_layout.addWidget(self.chk_first_row_header)

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
        self.table_preview.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.table_preview)

    def on_header_checkbox_changed(self, state):
        self.display_preview()

    def display_preview(self):
        if not self.cached_rows:
            self.table_preview.clear()
            self.table_preview.setRowCount(0)
            self.table_preview.setColumnCount(0)
            return

        max_cols = max(len(r) for r in self.cached_rows)
        is_header = self.chk_first_row_header.isChecked()

        self.table_preview.clear()

        if is_header:
            # 第一行作為欄位標題
            header_row = self.cached_rows[0]
            col_headers = [header_row[i] if i < len(header_row) else "" for i in range(max_cols)]
            # 填補空白標題
            col_headers = [h if h.strip() else f"第 {i+1} 欄" for i, h in enumerate(col_headers)]
            # 加上編號格式 "n. <欄位內容>"
            col_headers = [f"{i+1}. {h}" for i, h in enumerate(col_headers)]
            self.table_preview.setColumnCount(max_cols)
            self.table_preview.setHorizontalHeaderLabels(col_headers)

            content_rows = self.cached_rows[1:]
            self.table_preview.setRowCount(len(content_rows))

            row_headers = [str(i+2) for i in range(len(content_rows))]
            self.table_preview.setVerticalHeaderLabels(row_headers)

            for r_idx, row in enumerate(content_rows):
                for c_idx in range(max_cols):
                    val = row[c_idx] if c_idx < len(row) else ""
                    item = QTableWidgetItem(val)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    self.table_preview.setItem(r_idx, c_idx, item)
        else:
            # 普通顯示（第一行也是內容）
            self.table_preview.setColumnCount(max_cols)
            col_headers = [f"第 {i+1} 欄" for i in range(max_cols)]
            self.table_preview.setHorizontalHeaderLabels(col_headers)

            self.table_preview.setRowCount(len(self.cached_rows))

            row_headers = [str(i+1) for i in range(len(self.cached_rows))]
            self.table_preview.setVerticalHeaderLabels(row_headers)

            for r_idx, row in enumerate(self.cached_rows):
                for c_idx in range(max_cols):
                    val = row[c_idx] if c_idx < len(row) else ""
                    item = QTableWidgetItem(val)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    self.table_preview.setItem(r_idx, c_idx, item)

        self.table_preview.resizeColumnsToContents()

    def clear_preview(self):
        self.cached_rows = []
        self.display_preview()
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
                self.cached_rows = []
                self.display_preview()
                self.lbl_preview_status.setText("來源檔案為空，無法進行預覽")
                return

            self.cached_rows = rows
            self.lbl_preview_status.setText(f"預覽載入完成 (編碼: {encoding}, 分隔符: '{delimiter}')")
            self.display_preview()
            
            # 計算總行數並以 Signal 傳出
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                total_rows = sum(1 for _ in csv.reader(f, delimiter=delimiter))
            self.preview_loaded.emit(total_rows)

        except Exception as e:
            self.cached_rows = []
            self.display_preview()
            self.lbl_preview_status.setText(f"載入預覽失敗: {str(e)}")

    def is_first_row_header(self) -> bool:
        return self.chk_first_row_header.isChecked()

    def set_first_row_header(self, checked: bool):
        self.chk_first_row_header.setChecked(checked)
