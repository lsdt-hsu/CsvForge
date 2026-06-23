import os
import csv
from PyQt6.QtCore import QThread, pyqtSignal
from utils import detect_encoding, detect_delimiter

class BaseCSVWorker(QThread):
    progress_updated = pyqtSignal(int, int)      # 已處理列數, 總列數
    status_updated = pyqtSignal(str)             # 狀態欄更新日誌
    log_emitted = pyqtSignal(str, str)           # 級別 (INFO/SUCCESS/WARNING/ERROR), 訊息
    finished_successfully = pyqtSignal(str)      # 成功時的輸出檔案路徑
    finished_with_error = pyqtSignal(str)        # 錯誤原因

    def __init__(self, source_path, output_path, start_row, end_row):
        super().__init__()
        self.source_path = source_path
        self.output_path = output_path
        self.start_row = start_row
        self.end_row = end_row
        self._is_paused = False
        self._is_cancelled = False
        self.encoding = None
        self.delimiter = ","

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def cancel(self):
        self._is_cancelled = True

    def detect_format(self):
        """
        輔助方法：偵測 CSV 的編碼與分隔符。
        回傳: (encoding, delimiter)
        """
        self.log_emitted.emit("INFO", "正在檢測檔案編碼與格式...")
        self.encoding = detect_encoding(self.source_path)
        self.delimiter = detect_delimiter(self.source_path, self.encoding)
        self.log_emitted.emit("INFO", f"檢測到檔案編碼: {self.encoding}，分隔符: '{self.delimiter}'")
        return self.encoding, self.delimiter

    def count_total_rows(self, encoding, delimiter):
        """
        輔助方法：讀取檔案總行數。
        """
        with open(self.source_path, 'r', encoding=encoding, errors='replace') as f:
            total_rows = sum(1 for _ in csv.reader(f, delimiter=delimiter))
        return total_rows

    def get_success_message(self, out_path):
        return "成功", f"工作已完成！\n檔案已儲存至：\n{out_path}"

    def get_cancel_message(self, out_path):
        return "中斷", f"工作已取消！\n檔案已儲存至：\n{out_path}"

    def get_error_message(self, err_msg):
        return "出錯", f"工作執行時發生錯誤：\n{err_msg}"

    def validate_inputs(self):
        """
        驗證通用輸入欄位（路徑與行號），並在成功時將其轉換為整數/適當型別。
        回傳: (is_valid, error_message)
        """
        if not self.source_path or not os.path.exists(self.source_path):
            return False, "請選擇正確的來源 CSV 檔案路徑"
        if not self.output_path:
            return False, "請指定輸出檔案路徑"
            
        start_row_str = str(self.start_row).strip() if self.start_row is not None else ""
        if start_row_str == "":
            self.start_row = 1
        else:
            try:
                start_row_val = int(start_row_str)
                if start_row_val < 1:
                    return False, "起始行號必須是大於或等於 1 的正整數"
                self.start_row = start_row_val
            except (ValueError, TypeError):
                return False, "起始行號必須是大於或等於 1 的正整數"

        if self.end_row is not None and str(self.end_row).strip() != "":
            try:
                end_row_val = int(self.end_row)
                if end_row_val < self.start_row:
                    return False, "結束行號不能小於起始行號"
                self.end_row = end_row_val
            except (ValueError, TypeError):
                return False, "結束行號必須是正整數"
        else:
            self.end_row = None
                
        return self.validate_specific_inputs()

    def validate_specific_inputs(self):
        """
        子類別可覆寫此方法以進行其特有的欄位驗證與轉型。
        """
        return True, ""
