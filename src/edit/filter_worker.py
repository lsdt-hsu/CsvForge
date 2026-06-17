import re
import time
from PyQt6.QtCore import QThread, pyqtSignal

class FilterWorker(QThread):
    progress_updated = pyqtSignal(int, int)
    filter_completed = pyqtSignal(object, float)  # 傳回: 匹配的索引列表, 執行時間(秒)
    filter_error = pyqtSignal(str)

    def __init__(self, all_rows, start_row, end_row, is_header, 
                 compare_col, compare_method, compare_target, compare_value, 
                 src_col, tgt_col, parent=None):
        super().__init__(parent)
        self.all_rows = all_rows
        self.start_row = start_row
        self.end_row = end_row
        self.is_header = is_header
        
        self.compare_col = compare_col
        self.compare_method = compare_method
        self.compare_target = compare_target
        self.compare_value = compare_value
        self.src_col = src_col
        self.tgt_col = tgt_col
        
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        start_time = time.time()
        matched_indices = []
        
        try:
            total_rows = len(self.all_rows)
            end_bound = self.end_row if self.end_row is not None else total_rows
            end_bound = min(end_bound, total_rows)
            
            # 若為「不過濾」，回傳 None 交給 Model 處理
            if self.compare_col == "none":
                self.filter_completed.emit(None, time.time() - start_time)
                return

            # 正規表達式預先編譯
            regex_pattern = None
            if self.compare_method == "正規表達式" and self.compare_target == "manual":
                try:
                    regex_pattern = re.compile(self.compare_value)
                except re.error as e:
                    self.filter_error.emit(f"正規表達式語法錯誤: {e}")
                    return

            for i, row in enumerate(self.all_rows):
                if self._is_cancelled:
                    return
                
                # 報告進度
                if i % 10000 == 0:
                    self.progress_updated.emit(i, total_rows)
                
                # 排除標題行
                r_num = i + 1
                if self.is_header and r_num == 1:
                    continue
                    
                # 僅檢查在 start_row 與 end_row 之間的資料
                actual_start = max(2, self.start_row) if self.is_header else self.start_row
                if not (actual_start <= r_num <= end_bound):
                    continue
                
                # 決定比對範圍欄位索引集合
                if self.compare_col == "all":
                    cols_to_check = list(range(len(row)))
                elif self.compare_col == "range":
                    start_c = max(0, self.src_col - 1)
                    end_c = min(len(row) - 1, self.tgt_col - 1)
                    cols_to_check = list(range(start_c, end_c + 1))
                else:
                    # 特定欄位 (整數)
                    cols_to_check = [self.compare_col]

                # 決定比對目標值
                if self.compare_target == "manual":
                    target_val = self.compare_value
                else:
                    # 特定欄位的值 (整數)
                    t_idx = self.compare_target
                    target_val = row[t_idx] if t_idx < len(row) else ""

                is_match = False
                
                if self.compare_method == "完全符合":
                    is_match = any((row[c] if c < len(row) else "") == target_val for c in cols_to_check)
                elif self.compare_method == "包含":
                    is_match = any(target_val in (row[c] if c < len(row) else "") for c in cols_to_check)
                elif self.compare_method == "未包含":
                    # 「未包含」：所有欄位皆不包含 target_val (AND 邏輯)
                    is_match = all(target_val not in (row[c] if c < len(row) else "") for c in cols_to_check)
                elif self.compare_method == "正規表達式":
                    if self.compare_target == "manual" and regex_pattern:
                        is_match = any(bool(regex_pattern.search(row[c] if c < len(row) else "")) for c in cols_to_check)
                    else:
                        # 欄位比對當作正規表達式（以 target_val 做為 pattern）
                        try:
                            t_regex = re.compile(target_val)
                            is_match = any(bool(t_regex.search(row[c] if c < len(row) else "")) for c in cols_to_check)
                        except re.error:
                            is_match = False

                if is_match:
                    matched_indices.append(i)

            self.progress_updated.emit(total_rows, total_rows)
            self.filter_completed.emit(matched_indices, time.time() - start_time)

        except Exception as e:
            self.filter_error.emit(f"過濾發生未預期錯誤: {e}")
