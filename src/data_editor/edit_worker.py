import os
import csv
from csv_worker import BaseCSVWorker

class CSVEditWorker(BaseCSVWorker):
    def __init__(self, source_path, output_path, start_row, end_row):
        super().__init__(source_path, output_path, start_row, end_row)
        self.loaded_rows = []



    def run(self):
        try:
            self.log_emitted.emit("INFO", "開始載入 CSV 資料以供編輯...")
            encoding, delimiter = self.detect_format()
            
            # 統計總行數
            total_file_rows = self.count_total_rows(encoding, delimiter)
            self.log_emitted.emit("INFO", f"來源檔案讀取完成，共 {total_file_rows} 行。")

            all_rows = []
            with open(self.source_path, 'r', encoding=encoding, errors='replace') as f:
                reader = csv.reader(f, delimiter=delimiter)
                for idx, row in enumerate(reader):
                    if self._is_cancelled:
                        raise RuntimeError("使用者已取消載入編輯工作")
                        
                    all_rows.append(row)
                    
                    # 每 10000 行更新一次進度，避免太頻繁發送訊號
                    if idx % 10000 == 0:
                        self.progress_updated.emit(idx, total_file_rows)
                        self.log_emitted.emit("INFO", f"已讀取 {idx} 行...")

            self.progress_updated.emit(total_file_rows, total_file_rows)
            self.loaded_rows = all_rows
            self.log_emitted.emit("SUCCESS", f"編輯資料載入成功，共 {len(all_rows)} 行。")
            self.finished_successfully.emit(self.output_path)

        except Exception as e:
            self.log_emitted.emit("ERROR", f"載入編輯過程發生錯誤：{str(e)}")
            self.finished_with_error.emit(str(e))

    def get_success_message(self, out_path):
        return "成功", "編輯資料載入完成！"

    def get_cancel_message(self, out_path):
        return "中斷", "已取消編輯資料載入！"

    def get_error_message(self, err_msg):
        return "載入中斷", f"載入編輯過程發生錯誤：\n{err_msg}"
