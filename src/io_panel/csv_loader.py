import os
import csv
from PyQt6.QtCore import QObject, pyqtSignal
from csv_worker import BaseCSVWorker
from common_data.csv_data import LoadedCSVData
from io_panel.io_panel_validator import validate_io_panel_inputs

class CSVEditWorker(BaseCSVWorker):
    def __init__(self, source_path, output_path, start_row, end_row):
        super().__init__(source_path, output_path, start_row, end_row)
        self.loaded_rows = []
        self.task_name = "載入中..."

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


class CSVLoader(QObject):
    request_start_worker = pyqtSignal(object)
    load_completed = pyqtSignal(LoadedCSVData)
    load_error = pyqtSignal(str)

    def __init__(self, parent=None, context=None):
        super().__init__(parent)
        self.parent_win = parent  # MainWindow
        self.context = context
        self._current_worker = None

    def start_load_task(self):
        is_valid, parsed = validate_io_panel_inputs(
            self.parent_win,
            self.context,
            require_source_path=True,
            require_output_path=False,
            require_source_col=False,
            require_target_col=False,
        )
        if not is_valid:
            return

        worker_instance = CSVEditWorker(
            source_path=self.context.source_path,
            output_path=self.context.output_path,
            start_row=parsed["start_row"],
            end_row=parsed["end_row"]
        )
        self._current_worker = worker_instance

        # 連接完成與錯誤信號，包裝為 LoadedCSVData 後轉發
        worker_instance.finished_successfully.connect(self._on_worker_success)
        worker_instance.finished_with_error.connect(self._on_worker_error)

        # 請求主視窗啟動 Worker Thread
        self.request_start_worker.emit(worker_instance)

    def _on_worker_success(self, out_path):
        if not self._current_worker:
            return
        worker = self._current_worker
        
        # 轉換為共用資料結構 LoadedCSVData
        data = LoadedCSVData(
            all_rows=worker.loaded_rows,
            start_row=worker.start_row,
            end_row=worker.end_row,
            delimiter=getattr(worker, "delimiter", ","),
            encoding=getattr(worker, "encoding", "utf-8"),
            file_path=worker.source_path
        )
        self.load_completed.emit(data)
        self._current_worker = None

    def _on_worker_error(self, err_msg):
        self.load_error.emit(err_msg)
        self._current_worker = None
