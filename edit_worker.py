import shutil
from csv_worker import BaseCSVWorker

class CSVEditWorker(BaseCSVWorker):
    def __init__(self, source_path, output_path, start_row, end_row):
        super().__init__(source_path, output_path, start_row, end_row)

    def run(self):
        try:
            self.log_emitted.emit("INFO", "開始執行 CSV 編輯工作...")
            encoding, delimiter = self.detect_format()
            total_file_rows = self.count_total_rows(encoding, delimiter)
            self.log_emitted.emit("INFO", f"來源檔案讀取完成，共 {total_file_rows} 行。")

            # 模擬工作流程
            end_row_val = self.end_row if self.end_row is not None else total_file_rows
            total_to_process = max(0, end_row_val - self.start_row + 1)
            self.log_emitted.emit("INFO", f"欲處理範圍：自 {self.start_row} 行至 {end_row_val} 行 (共 {total_to_process} 行)")
            
            # 空實作：只做一個簡單的模擬迴圈，每隔一段時間更新進度，並支援取消
            for i in range(1, 11):
                if self._is_cancelled:
                    raise RuntimeError("使用者已取消編輯工作")
                self.msleep(150) # 模擬工作耗時
                current_progress = int(i * (total_to_process / 10))
                self.progress_updated.emit(min(current_progress, total_to_process), total_to_process)
                self.log_emitted.emit("INFO", f"正在處理資料...進度 {i*10}%")

            # 成功完成，將來源檔案複製到輸出檔案以完成空實作
            shutil.copy2(self.source_path, self.output_path)
            self.log_emitted.emit("SUCCESS", f"編輯工作完成！檔案已複製至：{self.output_path}")
            self.finished_successfully.emit(self.output_path)

        except Exception as e:
            self.log_emitted.emit("ERROR", f"編輯過程發生錯誤：{str(e)}")
            self.finished_with_error.emit(str(e))

    def get_success_message(self, out_path):
        return "成功", f"編輯完成！\n檔案已儲存至：\n{out_path}"

    def get_cancel_message(self, out_path):
        return "中斷", f"已取消編輯！\n檔案已儲存至：\n{out_path}"

    def get_error_message(self, err_msg):
        return "編輯中斷", f"編輯過程發生錯誤：\n{err_msg}"
