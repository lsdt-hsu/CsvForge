from PyQt6.QtCore import QObject, pyqtSignal
from typing import List, Optional
from src.utils.profiler import profiler

class CsvData(QObject):
    data_loaded = pyqtSignal()
    data_changed = pyqtSignal()
    filter_changed = pyqtSignal()
    header_state_changed = pyqtSignal(bool)
    modified_changed = pyqtSignal(bool)

    # 開啟/關閉 memory leak 診斷區塊的變數
    ENABLE_DIAG = False

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

        傳回格式說明：
        - 若 col 超過有效範圍，或未勾選「第一行為標題」，傳回「第 {col+1} 欄」。
        - 若已勾選「第一行為標題」，傳回「{col+1}. {標題}」的格式（若標題為空則以「第 {col+1} 欄」代替標題）。

        [開發規範 - 一致性要求 & 禁止變更]：
        此介面為所有面板取得單一欄位標題的標準介面。為了保持全域 UI 一致性，
        各 Panel (如翻譯、過濾、編輯、AI 面板等) 在顯示或處理欄位標題時，必須直接使用此
        方法回傳的字串，嚴禁在各自 Panel 的程式碼中自行添加或修改修飾性前綴/後綴，
        亦禁止 AI 主動提議變更此處定義的標準傳回格式。
        """
        if col < 0 or not self.all_rows or col >= len(self.all_rows[0]):
            return f"第 {col+1} 欄"

        if not self.is_header:
            return f"第 {col+1} 欄"

        h = str(self.all_rows[0][col]).strip()
        if not h:
            h = f"第 {col+1} 欄"
        return f"{col+1}. {h}"

    def set_csv_data(self, all_rows: List[List[str]], delimiter: str, encoding: str, file_path: Optional[str] = None, num_cols: Optional[int] = None):
        # ═══════════ [DIAG] Memory leak 診斷區塊 START ═══════════
        if self.ENABLE_DIAG:
            profiler.start_diagnostic(self.all_rows, "all_rows")
        # ═══════════ [DIAG] 診斷區塊 PAUSE ═══════════

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

        # ═══════════ [DIAG] Memory leak 診斷區塊 END ═══════════
        if self.ENABLE_DIAG:
            profiler.end_diagnostic()
        # ═══════════ [DIAG] 診斷區塊 DONE ═══════════

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
