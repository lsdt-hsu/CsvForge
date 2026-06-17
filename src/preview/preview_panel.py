import csv
import os
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel, QTableView,
    QCheckBox, QStyledItemDelegate, QStyle, QStyleOptionViewItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QFontMetrics
from base_panel import BasePanel
from utils import detect_encoding, detect_delimiter

PREVIEW_DEFAULT_SECTION_SIZE = 110
PREVIEW_VERTICAL_SECTION_SIZE = 28

class CsvNoFocusDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        if opt.state & QStyle.StateFlag.State_HasFocus:
            opt.state = opt.state & ~QStyle.StateFlag.State_HasFocus
        super().paint(painter, opt, index)

class CSVPreviewModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_rows = []           # 儲存完整的 CSV 二維陣列數據
        self.is_header = False       # 第一行是否為標題
        self.num_cols = 0            # 快取欄位數量

    def set_data(self, all_rows, is_header):
        self.beginResetModel()
        self.all_rows = all_rows
        self.is_header = is_header
        self.num_cols = max(len(row) for row in all_rows) if all_rows else 0
        self.endResetModel()

    def set_is_header(self, is_header):
        self.beginResetModel()
        self.is_header = is_header
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        if self.is_header and self.all_rows:
            return max(0, len(self.all_rows) - 1)
        return len(self.all_rows)

    def columnCount(self, parent=QModelIndex()):
        return self.num_cols

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
            
        if role == Qt.ItemDataRole.DisplayRole:
            r = index.row()
            if self.is_header:
                r += 1
            c = index.column()
            row_data = self.all_rows[r]
            return row_data[c] if c < len(row_data) else ""
            
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if self.is_header and self.all_rows:
                    header_row = self.all_rows[0]
                    h = header_row[section] if section < len(header_row) else ""
                    h = h if h.strip() else f"第 {section+1} 欄"
                    return f"{section+1}. {h}"
                else:
                    return f"第 {section+1} 欄"
            else:
                # 直向標題：顯示原始 CSV 中的行號
                actual_row_num = section + 2 if self.is_header else section + 1
                return str(actual_row_num)
                
        return None

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

        lbl_preview_title = QLabel("來源檔案預覽")
        lbl_preview_title.setObjectName("sectionHeader")
        preview_header_layout.addWidget(lbl_preview_title)

        # 「第一行為標題」核取方塊
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

        # 使用 QTableView 支援大數據虛擬滾動
        self.table_preview = QTableView()
        self.table_preview.horizontalHeader().setDefaultSectionSize(PREVIEW_DEFAULT_SECTION_SIZE)
        self.table_preview.verticalHeader().setDefaultSectionSize(PREVIEW_VERTICAL_SECTION_SIZE)
        self.table_preview.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        self.table_model = CSVPreviewModel()
        self.table_preview.setModel(self.table_model)
        self.table_preview.setItemDelegate(CsvNoFocusDelegate(self.table_preview))
        layout.addWidget(self.table_preview)

    def on_header_checkbox_changed(self, state):
        self.table_model.set_is_header(self.chk_first_row_header.isChecked())
        self.resize_columns_fast()

    def display_preview(self):
        self.table_model.set_data(self.cached_rows, self.chk_first_row_header.isChecked())
        self.resize_columns_fast()

    def resize_columns_fast(self):
        """
        為防大檔案計算凍結，僅針對前 100 行內容估算並調整欄寬。
        """
        model = self.table_model
        if not model or not model.all_rows:
            return
            
        num_cols = model.columnCount()
        num_rows = min(100, model.rowCount())
        font = self.table_preview.font()
        fm = QFontMetrics(font)
        
        for col in range(num_cols):
            max_width = 80 # 最小預設欄寬
            
            # 計算橫向標題寬度
            header_text = model.headerData(col, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            if header_text:
                max_width = max(max_width, fm.horizontalAdvance(str(header_text)) + 25)
            
            # 遍歷前 100 行計算最大寬度
            for row in range(num_rows):
                index = model.index(row, col)
                val = model.data(index, Qt.ItemDataRole.DisplayRole)
                if val:
                    max_width = max(max_width, fm.horizontalAdvance(str(val)) + 15)
                    
            self.table_preview.setColumnWidth(col, min(400, max_width))

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
                for row in reader:
                    rows.append(row)
            
            if not rows:
                self.cached_rows = []
                self.display_preview()
                self.lbl_preview_status.setText("來源檔案為空，無法進行預覽")
                return

            self.cached_rows = rows
            self.lbl_preview_status.setText(f"預覽載入完成 (共 {len(rows)} 行，編碼: {encoding}, 分隔符: '{delimiter}')")
            self.display_preview()
            
            # 計算總行數並以 Signal 傳出
            self.preview_loaded.emit(len(rows))

        except Exception as e:
            self.cached_rows = []
            self.display_preview()
            self.lbl_preview_status.setText(f"載入預覽失敗: {str(e)}")

    def is_first_row_header(self) -> bool:
        return self.chk_first_row_header.isChecked()

    def set_first_row_header(self, checked: bool):
        self.chk_first_row_header.setChecked(checked)
