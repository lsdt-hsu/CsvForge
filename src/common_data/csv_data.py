from PyQt6.QtCore import QObject, pyqtSignal
from typing import List, Optional

class LoadedCSVData(QObject):
    data_loaded = pyqtSignal()
    data_changed = pyqtSignal()
    filter_changed = pyqtSignal()
    header_state_changed = pyqtSignal(bool)
    modified_changed = pyqtSignal(bool)

    def __init__(self, all_rows: List[List[str]] = None, delimiter: str = ",", encoding: str = "utf-8", file_path: Optional[str] = None, num_cols: Optional[int] = None):
        super().__init__()
        self.all_rows = all_rows if all_rows is not None else []
        self.delimiter = delimiter
        self.encoding = encoding
        self.file_path = file_path
        self.is_header = False
        self.filtered_indices = None
        self.is_modified = False
        self.num_cols = num_cols if num_cols is not None else (max(len(row) for row in self.all_rows) if self.all_rows else 0)
        self.visible_indices = []
        self._update_visible_indices()

    def _update_visible_indices(self):
        # 1. 更新可見列索引
        if not self.all_rows:
            self.visible_indices = []
        else:
            total = len(self.all_rows)
            data_start = 1 if self.is_header else 0
            if self.filtered_indices is None:
                self.visible_indices = list(range(data_start, total))
            else:
                self.visible_indices = [i for i in self.filtered_indices if i >= data_start]

    def get_column_header(self, col: int) -> str:
        """
        即時取得第 col 欄的標頭（col 為 0-indexed 的欄位索引）。
        如果 col >= self.num_cols，則一律回傳 "第 col+1 欄"。

        [開發規範 - 一致性要求]：
        此介面為所有面板取得單一欄位標題的標準介面。為了保持全域 UI 一致性，
        各 Panel (如翻譯、過濾、編輯面板等) 在顯示欄位標題時，必須直接使用此
        方法回傳的字串，嚴禁在各自 Panel 的程式碼中自行添加修飾性或裝飾性的
        前綴/後綴 (如 "C1:" 或 "欄位 1" 等)。
        """
        if col < 0:
            return f"第 {col+1} 欄"
            
        if self.is_header and self.all_rows and col < len(self.all_rows[0]):
            h = self.all_rows[0][col].strip()
            return f"{col+1}. {h}" if h else f"{col+1}. 第 {col+1} 欄"
            
        return f"第 {col+1} 欄"

    @property
    def headers(self) -> List[str]:
        """
        唯讀動態屬性，僅供需要列出所有標題的面板使用。

        [開發規範 - 一致性要求]：
        此屬性為所有面板列出全域欄位標題的標準介面。為了保持全域 UI 一致性，
        各 Panel (如翻譯、過濾、編輯面板等) 在顯示欄位清單時，必須直接使用此
        列表提供的字串，嚴禁在各自 Panel 的程式碼中自行添加修飾性或裝飾性的
        前綴/後綴 (如 "C1:" 或 "欄位 1" 等)。
        """
        return [self.get_column_header(i) for i in range(self.num_cols)]

    def set_csv_data(self, all_rows: List[List[str]], delimiter: str, encoding: str, file_path: Optional[str] = None, num_cols: Optional[int] = None):
        self.all_rows = all_rows
        self.delimiter = delimiter
        self.encoding = encoding
        self.file_path = file_path
        # 沿用原來的 self.is_header 狀態，不進行任何變更與覆寫
        self.filtered_indices = None
        self.num_cols = num_cols if num_cols is not None else (max(len(row) for row in self.all_rows) if self.all_rows else 0)
        self._update_visible_indices()
        self.set_modified(False)
        self.data_loaded.emit()

    def get_visible_indices(self) -> List[int]:
        return self.visible_indices

    def get_visible_rows(self) -> List[List[str]]:
        return [self.all_rows[i] for i in self.visible_indices]

    def set_filtered_indices(self, indices: Optional[List[int]]):
        self.filtered_indices = indices
        self._update_visible_indices()
        self.filter_changed.emit()

    def set_is_header(self, is_header: bool):
        if self.is_header != is_header:
            self.is_header = is_header
            self._update_visible_indices()
            self.header_state_changed.emit(is_header)

    def set_modified(self, modified: bool):
        if self.is_modified != modified:
            self.is_modified = modified
            self.modified_changed.emit(modified)

    def update_cell(self, row: int, col: int, value: str):
        self.all_rows[row][col] = value
        if col >= self.num_cols:
            self.num_cols = col + 1
            self._update_visible_indices()
        self.set_modified(True)
        self.data_changed.emit()
