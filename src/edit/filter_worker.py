import re
import time
from PyQt6.QtCore import QThread, pyqtSignal

class FilterWorker(QThread):
    progress_updated = pyqtSignal(int, int)
    filter_completed = pyqtSignal(object, float)  # 傳回: 匹配的索引列表, 執行時間(秒)
    filter_error = pyqtSignal(str)

    def __init__(self, all_rows, start_row, end_row, is_header, 
                 filter_method, filter_text, src_col, tgt_col, 
                 col1_idx, col2_idx, parent=None):
        super().__init__(parent)
        self.all_rows = all_rows
        self.start_row = start_row
        self.end_row = end_row
        self.is_header = is_header
        
        self.filter_method = filter_method
        self.filter_text = filter_text
        self.src_col = src_col
        self.tgt_col = tgt_col
        self.col1_idx = col1_idx
        self.col2_idx = col2_idx
        
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
            
            # 若為「全部」，不需過濾，回傳 None 交給 Model 處理
            if self.filter_method == "全部":
                self.filter_completed.emit(None, time.time() - start_time)
                return

            # 正規表達式預先編譯
            regex_pattern = None
            if self.filter_method == "範圍欄位─正規表達式":
                try:
                    regex_pattern = re.compile(self.filter_text)
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
                # 注意：這裡使用 is_header 的調整邏輯，第一行不在此處判斷，
                # 但需要滿足 >= start_row 且 <= end_bound
                actual_start = max(2, self.start_row) if self.is_header else self.start_row
                if not (actual_start <= r_num <= end_bound):
                    continue
                
                is_match = False
                
                if self.filter_method in ("範圍欄位─完全符合", "範圍欄位─包含", "範圍欄位─正規表達式"):
                    # 將 1-based 的欄號轉為 0-based 索引
                    start_c = max(0, self.src_col - 1)
                    end_c = min(len(row) - 1, self.tgt_col - 1)
                    
                    for c_idx in range(start_c, end_c + 1):
                        cell_val = row[c_idx] if c_idx < len(row) else ""
                        
                        if self.filter_method == "範圍欄位─完全符合":
                            if cell_val == self.filter_text:
                                is_match = True
                                break
                        elif self.filter_method == "範圍欄位─包含":
                            if self.filter_text in cell_val:
                                is_match = True
                                break
                        elif self.filter_method == "範圍欄位─正規表達式":
                            if regex_pattern.search(cell_val):
                                is_match = True
                                break
                                
                elif self.filter_method == "欄位比對":
                    val1 = row[self.col1_idx] if self.col1_idx < len(row) else ""
                    val2 = row[self.col2_idx] if self.col2_idx < len(row) else ""
                    if val1 == val2:
                        is_match = True
                
                if is_match:
                    matched_indices.append(i)

            self.progress_updated.emit(total_rows, total_rows)
            self.filter_completed.emit(matched_indices, time.time() - start_time)

        except Exception as e:
            self.filter_error.emit(f"過濾發生未預期錯誤: {e}")
