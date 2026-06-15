from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel, QCheckBox, QTableView,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QFontMetrics
from base_panel import BasePanel

PREVIEW_DEFAULT_SECTION_SIZE = 110
PREVIEW_VERTICAL_SECTION_SIZE = 28

class CsvTableDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        if opt.state & QStyle.StateFlag.State_HasFocus:
            opt.state = opt.state & ~QStyle.StateFlag.State_HasFocus
        super().paint(painter, opt, index)

    def updateEditorGeometry(self, editor, option, index):
        # 將編輯元件高度與寬度拉伸到整個儲存格大小（包含格線內框）
        editor.setGeometry(option.rect)

class CSVTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_rows = []           # 儲存完整的 CSV 二維陣列數據
        self.start_row = 1          # 起始行號 (1-based)
        self.end_row = None         # 結束行號 (1-based, None 表示至結尾)
        self.is_header = False      # 第一行是否為標題
        self.num_cols = 0            # 快取欄位數量，避免 O(N) 重複計算
        self.visible_row_indices = [] # 儲存當前可見資料行在 all_rows 中的索引值

    def set_data(self, all_rows, start_row, end_row, is_header):
        self.beginResetModel()
        self.all_rows = all_rows
        self.start_row = start_row
        self.end_row = end_row
        self.is_header = is_header
        self.num_cols = max(len(row) for row in all_rows) if all_rows else 0
        self.update_visible_rows()
        self.endResetModel()

    def set_is_header(self, is_header):
        self.beginResetModel()
        self.is_header = is_header
        self.update_visible_rows()
        self.endResetModel()

    def update_visible_rows(self):
        self.visible_row_indices = []
        if not self.all_rows:
            return

        total_rows = len(self.all_rows)
        end_idx = self.end_row if self.end_row is not None else total_rows
        end_idx = min(end_idx, total_rows)

        if self.is_header:
            start = max(2, self.start_row)
        else:
            start = self.start_row

        if start <= end_idx:
            self.visible_row_indices = list(range(start - 1, end_idx))

    def rowCount(self, parent=QModelIndex()):
        return len(self.visible_row_indices)

    def columnCount(self, parent=QModelIndex()):
        return self.num_cols

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
            
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            r = self.visible_row_indices[index.row()]
            c = index.column()
            row_data = self.all_rows[r]
            return row_data[c] if c < len(row_data) else ""
            
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if index.isValid() and role == Qt.ItemDataRole.EditRole:
            r = self.visible_row_indices[index.row()]
            c = index.column()
            
            row_data = self.all_rows[r]
            while len(row_data) <= c:
                row_data.append("")
                
            row_data[c] = str(value)
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

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
                # 直向標題：顯示該資料行在原始 CSV 中的 1-based 行號
                actual_row_num = self.visible_row_indices[section] + 1
                return str(actual_row_num)
                
        return None

class EditContentPanel(BasePanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rightFrame")
        self.setMinimumHeight(200)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        # 預覽標頭列
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        lbl_title = QLabel("CSV 檔案編輯器")
        lbl_title.setObjectName("sectionHeader")
        header_layout.addWidget(lbl_title)

        # 「第一行為標題」核取方塊
        self.chk_first_row_header = QCheckBox("第一行為標題")
        self.chk_first_row_header.setObjectName("chkFirstRowHeader")
        self.chk_first_row_header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_first_row_header.stateChanged.connect(self.on_header_checkbox_changed)
        header_layout.addWidget(self.chk_first_row_header)

        header_layout.addStretch()

        self.lbl_status = QLabel("尚未載入編輯資料")
        self.lbl_status.setObjectName("previewStatus")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(self.lbl_status)

        layout.addWidget(header_widget)

        # 使用 QTableView 支援大數據虛擬滾動
        self.table_view = QTableView()
        self.table_view.horizontalHeader().setDefaultSectionSize(PREVIEW_DEFAULT_SECTION_SIZE)
        self.table_view.verticalHeader().setDefaultSectionSize(PREVIEW_VERTICAL_SECTION_SIZE)
        self.table_view.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # 關聯 Model 與 Delegate
        self.table_model = CSVTableModel()
        self.table_view.setModel(self.table_model)
        self.table_view.setItemDelegate(CsvTableDelegate(self.table_view))
        
        layout.addWidget(self.table_view)

    def on_header_checkbox_changed(self, state):
        self.table_model.set_is_header(self.chk_first_row_header.isChecked())
        self.resize_columns_fast()

    def load_data(self, all_rows, start_row, end_row):
        self.table_model.set_data(
            all_rows, 
            start_row, 
            end_row, 
            self.chk_first_row_header.isChecked()
        )
        
        end_row_val = end_row if end_row is not None else len(all_rows)
        self.lbl_status.setText(f"已載入資料 (共 {len(all_rows)} 行，顯示第 {start_row} 至 {end_row_val} 行)")
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
        font = self.table_view.font()
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
                    
            self.table_view.setColumnWidth(col, min(400, max_width))

    def is_first_row_header(self) -> bool:
        return self.chk_first_row_header.isChecked()

    def set_first_row_header(self, checked: bool):
        self.chk_first_row_header.setChecked(checked)
