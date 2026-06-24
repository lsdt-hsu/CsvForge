import os
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel, QCheckBox, QTableView,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem, QPushButton,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSize, pyqtSignal
from PyQt6.QtGui import QFontMetrics, QIcon
from base_panel import BasePanel
from common_data.csv_data import LoadedCSVData


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
        self.is_header = False      # 第一行是否為標題
        self.num_cols = 0            # 快取欄位數量，避免 O(N) 重複計算
        self.filtered_indices = None # None = 未啟用過濾; list = 過濾後的 0-based 索引
        self.visible_row_indices = [] # 儲存當前可見資料行在 all_rows 中的索引值

    def set_data(self, all_rows, is_header):
        self.beginResetModel()
        self.all_rows = all_rows
        self.is_header = is_header
        self.num_cols = max(len(row) for row in all_rows) if all_rows else 0
        self.filtered_indices = None
        self.update_visible_rows()
        self.endResetModel()

    def set_is_header(self, is_header):
        self.beginResetModel()
        self.is_header = is_header
        self.update_visible_rows()
        self.endResetModel()

    def set_filtered_indices(self, indices):
        self.beginResetModel()
        self.filtered_indices = indices
        self.update_visible_rows()
        self.endResetModel()

    def update_visible_rows(self):
        if not self.all_rows:
            self.visible_row_indices = []
            return
        total = len(self.all_rows)
        data_start = 1 if self.is_header else 0  # 有標題則跳過第 0 行（索引 0）
        if self.filtered_indices is None:
            self.visible_row_indices = list(range(data_start, total))
        else:
            self.visible_row_indices = [i for i in self.filtered_indices if i >= data_start]

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

class DataEditorPanel(BasePanel):
    """
    資料編輯面板：顯示並允許使用者直接在 Table 中編輯 CSV 資料。

    公開介面（供主視窗與其他元件使用）：
      - load_data(all_rows)
      - clear()
      - get_all_rows() -> list
      - has_data() -> bool
      - apply_filter(indices: list | None)
      - get_delimiter() -> str
      - set_delimiter(delimiter: str)
      - is_first_row_header() -> bool
      - set_first_row_header(checked: bool)
      - set_modified(modified: bool)

    Signals：
      - request_save：使用者點擊存檔按鈕時發射
    """
    request_save = pyqtSignal()
    header_state_changed = pyqtSignal(bool)

    def __init__(self, parent=None, context=None):
        super().__init__(parent, require_data_loading=False, context=context)
        self.setObjectName("rightFrame")
        self.setMinimumHeight(200)
        self.is_modified = False
        self._delimiter = ","
        self.init_ui()

    def init_ui(self):
        layout = self.controls_layout
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

        self.lbl_status = QLabel("尚未載入資料")
        self.lbl_status.setObjectName("previewStatus")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(self.lbl_status)

        # 存檔按鈕
        self.btn_save = QPushButton()
        self.btn_save.setObjectName("btnSaveData")
        self.btn_save.setFixedSize(30, 30)
        save_icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "save.png")
        self.btn_save.setIcon(QIcon(save_icon_path))
        self.btn_save.setIconSize(QSize(20, 20))
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.request_save.emit)
        header_layout.addWidget(self.btn_save)

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
        
        # 監聽資料異動
        self.table_model.dataChanged.connect(lambda: self.set_modified(True))
        
        layout.addWidget(self.table_view)

    # ── 公開介面方法 ──────────────────────────────────────────────────────────

    def get_all_rows(self) -> list:
        """取得目前在記憶體中的全部 CSV 二維陣列（未經過濾的原始資料）。"""
        return self.table_model.all_rows

    def has_data(self) -> bool:
        """判斷面板是否已載入 CSV 資料。"""
        return bool(self.table_model.all_rows)

    def apply_filter(self, indices):
        """
        套用過濾結果至資料表。
        :param indices: 符合過濾條件的 0-based 行索引列表；傳入 None 表示清除過濾。
        """
        self.table_model.set_filtered_indices(indices)

    def get_delimiter(self) -> str:
        """取得當前使用的 CSV 分隔符。"""
        return self._delimiter

    def set_delimiter(self, delimiter: str):
        """設定 CSV 分隔符（通常在資料載入後由主視窗呼叫）。"""
        self._delimiter = delimiter

    # ── 內部控制方法 ──────────────────────────────────────────────────────────

    def set_modified(self, modified):
        self.is_modified = modified
        self.btn_save.setEnabled(modified)

    def on_header_checkbox_changed(self, state):
        is_checked = self.chk_first_row_header.isChecked()
        self.table_model.set_is_header(is_checked)
        self.resize_columns_fast()
        self.header_state_changed.emit(is_checked)
        # 直接操作 DataEditorConfig（資料相依性），見 settings_manager.py 模組說明
        if self.context:
            self.context.data_editor_config.first_row_header = is_checked
            self.context.data_editor_config.dirty = True

    def load_data(self, all_rows, file_path=None):
        self.table_model.set_data(
            all_rows, 
            self.chk_first_row_header.isChecked()
        )
        
        prefix = ""
        if file_path:
            base_name = os.path.basename(file_path)
            main_name, _ = os.path.splitext(base_name)
            prefix = f"{main_name}: "
            
        self.lbl_status.setText(f"{prefix}共 {len(all_rows)} 行")
        self.set_modified(False)
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

    def restore_from_config(self) -> None:
        """
        從 AppContext 的 DataEditorConfig 還原面板初始狀態。
        由 MainWindow._restore_all_panel_configs() 在啟動時呼叫。
        """
        if not self.context:
            return
        checked = self.context.data_editor_config.first_row_header
        # blockSignals 避免觸發 on_header_checkbox_changed 時誤設 dirty flag
        self.chk_first_row_header.blockSignals(True)
        self.chk_first_row_header.setChecked(checked)
        self.table_model.set_is_header(checked)
        self.chk_first_row_header.blockSignals(False)

    def clear(self):
        self.table_model.set_data([], False)
        self.lbl_status.setText("尚未載入資料")
        self.set_modified(False)

    def set_table_editable(self, editable: bool):
        if not editable:
            self._orig_edit_triggers = self.table_view.editTriggers()
            self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        else:
            if hasattr(self, "_orig_edit_triggers"):
                self.table_view.setEditTriggers(self._orig_edit_triggers)
            else:
                self.table_view.setEditTriggers(
                    QAbstractItemView.EditTrigger.DoubleClicked | 
                    QAbstractItemView.EditTrigger.EditKeyPressed | 
                    QAbstractItemView.EditTrigger.AnyKeyPressed
                )

    def set_csv_data(self, data: LoadedCSVData):
        self.set_delimiter(data.delimiter)
        self.load_data(data.all_rows, file_path=data.file_path)

