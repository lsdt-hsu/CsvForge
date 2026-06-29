import os
import csv
from PyQt6.QtCore import QThread, pyqtSignal
def _detect_encoding(file_path):
    encodings = ['utf-8-sig', 'utf-8', 'cp950', 'gbk', 'utf-16', 'latin-1']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                f.read(4096)
            return enc
        except UnicodeDecodeError:
            continue
    return 'utf-8'

def _detect_delimiter(file_path, encoding):
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            sample = f.read(2048)
            dialect = csv.Sniffer().sniff(sample)
            return dialect.delimiter
    except Exception:
        return ','


class CSVWorker(QThread):
    progress_updated = pyqtSignal(int, int)      # 已處理列數, 總列數
    status_updated = pyqtSignal(str)             # 狀態欄更新日誌
    log_emitted = pyqtSignal(str, str)           # 級別 (INFO/SUCCESS/WARNING/ERROR), 訊息
    finished_successfully = pyqtSignal(str)      # 成功時的輸出檔案路徑
    finished_with_error = pyqtSignal(str)        # 錯誤原因

    def __init__(self, source_path, output_path):
        super().__init__()
        self.source_path = source_path
        self.output_path = output_path
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
        self.encoding = _detect_encoding(self.source_path)
        self.delimiter = _detect_delimiter(self.source_path, self.encoding)
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
