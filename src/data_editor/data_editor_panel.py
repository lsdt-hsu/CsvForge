import os
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel, QCheckBox, QTableView,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem, QPushButton,
    QAbstractItemView, QMessageBox
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSize, pyqtSignal
from PyQt6.QtGui import QFontMetrics, QIcon
from base.main_base_panel import BasePanel
from common_data.csv_data import CsvData


PREVIEW_DEFAULT_SECTION_SIZE = 110
PREVIEW_VERTICAL_SECTION_SIZE = 28

class CsvTableDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        if opt.state & QStyle.StateFlag.State_HasFocus:
            opt.state = opt.state & ~QStyle.StateFlag.State_HasFocus
        super().paint(painter, opt, index)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

class CsvTableView(QTableView):
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            selected = self.selectionModel().selectedIndexes()
            if not selected:
                super().keyPressEvent(event)
                return

            m = len(set(idx.row() for idx in selected))
            n = len(set(idx.column() for idx in selected))

            if len(selected) == 1:
                reply = QMessageBox.question(
                    self,
                    "確認刪除",
                    "確定要清除選取資料嗎？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            elif len(selected) > 1:
                reply = QMessageBox.question(
                    self,
                    "確認刪除",
                    f"確定要清除選取的 {m}  × {n} = {len(selected)} 格資料嗎？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            model = self.model()
            if model:
                for index in selected:
                    model.setData(index, "", Qt.ItemDataRole.EditRole)
        else:
            super().keyPressEvent(event)


class CSVTableModel(QAbstractTableModel):
    def __init__(self, csv_data: CsvData, parent=None):
        super().__init__(parent)
        self.csv_data = csv_data
        
        # 本地屬性快取
        self._visible_indices = []
        self._num_cols = 0
        self._is_header = False
        self._update_local_cache()
        
        # 連接 Model 的事件通知
        self.csv_data.data_loaded.connect(self.on_data_loaded)
        self.csv_data.data_changed.connect(self.on_data_changed)
        self.csv_data.filter_changed.connect(self.on_filter_changed)
        self.csv_data.header_state_changed.connect(self.on_header_state_changed)

    def _update_local_cache(self):
        if self.csv_data:
            self._visible_indices = self.csv_data.get_visible_indices()
            self._num_cols = self.csv_data.num_cols
            self._is_header = self.csv_data.is_header
        else:
            self._visible_indices = []
            self._num_cols = 0
            self._is_header = False

    def on_data_loaded(self):
        self._update_local_cache()
        self.beginResetModel()
        self.endResetModel()

    def on_data_changed(self):
        self._update_local_cache()
        # 局部資料改變，發射 layoutChanged 以讓 View 重繪目前可見格
        self.layoutChanged.emit()

    def on_filter_changed(self):
        self._update_local_cache()
        self.beginResetModel()
        self.endResetModel()

    def on_header_state_changed(self, is_header):
        self._update_local_cache()
        self.beginResetModel()
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._visible_indices)

    def columnCount(self, parent=QModelIndex()):
        return self._num_cols

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not self.csv_data:
            return None
            
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            r = self._visible_indices[index.row()]
            c = index.column()
            row_data = self.csv_data.all_rows[r]
            return row_data[c] if c < len(row_data) else ""
            
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if index.isValid() and role == Qt.ItemDataRole.EditRole and self.csv_data:
            r = self._visible_indices[index.row()]
            c = index.column()
            
            # 確保該 row 寬度足夠
            row_data = self.csv_data.all_rows[r]
            while len(row_data) <= c:
                row_data.append("")
                
            self.csv_data.update_cell(r, c, str(value))
            return True
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and self.csv_data:
            if orientation == Qt.Orientation.Horizontal:
                return self.csv_data.get_column_header(section)
            else:
                actual_row_num = self._visible_indices[section] + 1
                return str(actual_row_num)
                
        return None

class DataEditorPanel(BasePanel):
    def __init__(self, parent=None, context=None):
        super().__init__(parent, context=context)
        self.setObjectName("rightFrame")
        self.setMinimumHeight(200)
        self._delimiter = ","
        self.init_ui()
        
        # 訂閱資料載入信號以自動調整欄寬與更新狀態文字
        if self.context and self.context.csv_data:
            self.context.csv_data.data_loaded.connect(self.on_model_loaded)
            self.context.csv_data.filter_changed.connect(self.on_status_updated)
            self.context.csv_data.header_state_changed.connect(self.on_status_updated)

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

        layout.addWidget(header_widget)

        # 使用 CsvTableView 支援大數據虛擬滾動
        self.table_view = CsvTableView()
        self.table_view.horizontalHeader().setDefaultSectionSize(PREVIEW_DEFAULT_SECTION_SIZE)
        self.table_view.verticalHeader().setDefaultSectionSize(PREVIEW_VERTICAL_SECTION_SIZE)
        self.table_view.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # 關聯 Model 與 Delegate (使用全域共享的 csv_data)
        csv_data = self.context.csv_data if self.context else CsvData()
        self.table_model = CSVTableModel(csv_data, self.table_view)
        self.table_view.setModel(self.table_model)
        self.table_view.setItemDelegate(CsvTableDelegate(self.table_view))
        
        layout.addWidget(self.table_view)

    # ── 公開介面方法 ──────────────────────────────────────────────────────────

    def get_all_rows(self) -> list:
        return self.context.csv_data.all_rows if self.context and self.context.csv_data else []

    def has_data(self) -> bool:
        return bool(self.get_all_rows())

    def get_delimiter(self) -> str:
        return self._delimiter

    def set_delimiter(self, delimiter: str):
        self._delimiter = delimiter

    # ── 內部控制方法 ──────────────────────────────────────────────────────────

    def on_header_checkbox_changed(self, state):
        is_checked = self.chk_first_row_header.isChecked()
        if self.context and self.context.csv_data:
            self.context.csv_data.set_is_header(is_checked)
        self.resize_columns_fast()
        
        # 直接操作 DataEditorConfig（資料相依性）
        if self.context:
            self.context.data_editor_config.first_row_header = is_checked
            self.context.data_editor_config.dirty = True

    def on_status_updated(self):
        if not self.context or not self.context.csv_data:
            self.lbl_status.setText("尚未載入資料")
            return
            
        csv_data = self.context.csv_data
        if not csv_data.file_path:
            filename = "未命名"
        else:
            filename = os.path.basename(csv_data.file_path)
            
        n = len(csv_data.get_visible_indices())
        m = len(csv_data.all_rows)
        
        self.lbl_status.setText(f"<{filename}> 共 {n} / {m} 行")

    def on_model_loaded(self) -> None:
        # 🔪 終極解法：信號定向除疤。不銷毀實體，只把重複 connect 的舊線剪斷
        if hasattr(self, "table_view") and self.table_view:
            model = self.table_view.model()
            if model and hasattr(model, "csv_data") and model.csv_data:
                # 🎯 拔除 Model 內部重複疊加的全域信號
                try:
                    model.csv_data.data_loaded.disconnect(model.on_data_loaded)
                    model.csv_data.data_changed.disconnect(model.on_data_changed)
                    model.csv_data.filter_changed.disconnect(model.on_filter_changed)
                    model.csv_data.header_state_changed.disconnect(model.on_header_state_changed)
                except Exception:
                    pass # 防止未連結時拋出異常
                
                # 🎯 重新只連一條乾淨的線，維持外掛面板的穩定度
                model.csv_data.data_loaded.connect(model.on_data_loaded)
                model.csv_data.data_changed.connect(model.on_data_changed)
                model.csv_data.filter_changed.connect(model.on_filter_changed)
                model.csv_data.header_state_changed.connect(model.on_header_state_changed)

        # 🎯 拔除 Panel 本身重複疊加的全域信號（防止 resize_columns_fast 執行次數呈等差級數暴增）
        if self.context and self.context.csv_data:
            try:
                self.context.csv_data.data_loaded.disconnect(self.on_model_loaded)
                self.context.csv_data.filter_changed.disconnect(self.on_status_updated)
                self.context.csv_data.header_state_changed.disconnect(self.on_status_updated)
            except Exception:
                pass
            
            # 重新綁定唯一的合法連線
            self.context.csv_data.data_loaded.connect(self.on_model_loaded)
            self.context.csv_data.filter_changed.connect(self.on_status_updated)
            self.context.csv_data.header_state_changed.connect(self.on_status_updated)

        # 更新狀態與重算欄寬
        self.on_status_updated()
        self.resize_columns_fast()
        
        # 強制讓 Python GC 把剛才斷開的信號殘留空殼收走
        import gc
        gc.collect()

    def resize_columns_fast(self):
        csv_data = self.context.csv_data if self.context else None
        if not csv_data or not csv_data.all_rows:
            return
            
        num_cols = self.table_model.columnCount()
        num_rows = min(100, self.table_model.rowCount())
        font = self.table_view.font()
        fm = QFontMetrics(font)
        
        for col in range(num_cols):
            max_width = 80 # 最小預設欄寬
            
            header_text = self.table_model.headerData(col, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            if header_text:
                max_width = max(max_width, fm.horizontalAdvance(str(header_text)) + 25)
            
            for row in range(num_rows):
                index = self.table_model.index(row, col)
                val = self.table_model.data(index, Qt.ItemDataRole.DisplayRole)
                if val:
                    max_width = max(max_width, fm.horizontalAdvance(str(val)) + 15)
                    
            self.table_view.setColumnWidth(col, min(400, max_width))

    def is_first_row_header(self) -> bool:
        return self.chk_first_row_header.isChecked()

    def restore_from_config(self) -> None:
        if not self.context:
            return
        checked = self.context.data_editor_config.first_row_header
        self.chk_first_row_header.blockSignals(True)
        self.chk_first_row_header.setChecked(checked)
        if self.context.csv_data:
            self.context.csv_data.set_is_header(checked)
        self.chk_first_row_header.blockSignals(False)

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
