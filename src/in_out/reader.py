import os
import csv
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
from .csv_worker import CSVWorker
from common_data.csv_data import CsvData
from utils import ThrottledProgress

class CSVEditWorker(CSVWorker):
    def __init__(self, source_path, output_path):
        super().__init__(source_path, output_path)
        self.loaded_rows = []
        self.task_name = "載入中..."
        
        self.progress_throttler = ThrottledProgress(self.progress_updated, min_interval=0.2)
        self.log_throttler = ThrottledProgress(self.log_emitted, min_interval=0.2)

    def run(self):
        try:
            self.log_throttler.emit("INFO", "開始載入 CSV 資料以供編輯...", force=True)
            encoding, delimiter = self.detect_format()
            
            # 統計總行數
            total_file_rows = self.count_total_rows(encoding, delimiter)
            self.log_throttler.emit("INFO", f"來源檔案讀取完成，共 {total_file_rows} 行。", force=True)

            all_rows = []
            num_cols = 0
            with open(self.source_path, 'r', encoding=encoding, errors='replace') as f:
                reader = csv.reader(f, delimiter=delimiter)
                for idx, row in enumerate(reader):
                    if self._is_cancelled:
                        raise RuntimeError("使用者已取消載入編輯工作")
                        
                    all_rows.append(row)
                    row_len = len(row)
                    if row_len > num_cols:
                        num_cols = row_len
                    
                    # 限制進度更新頻率為每秒最多 5 次
                    self.progress_throttler.emit(idx, total_file_rows)
                    self.log_throttler.emit("INFO", f"已讀取 {idx} 行...")

            self.progress_throttler.emit(total_file_rows, total_file_rows, force=True)
            self.loaded_rows = all_rows
            self.num_cols = num_cols
            self.log_throttler.emit("SUCCESS", f"編輯資料載入成功，共 {len(all_rows)} 行。", force=True)
            self.finished_successfully.emit(self.output_path)

        except Exception as e:
            self.log_throttler.emit("ERROR", f"載入編輯過程發生錯誤：{str(e)}", force=True)
            self.finished_with_error.emit(str(e))

    def get_success_message(self, out_path):
        return "成功", "編輯資料載入完成！"

    def get_cancel_message(self, out_path):
        return "中斷", "已取消編輯資料載入！"

    def get_error_message(self, err_msg):
        return "載入中斷", f"載入編輯過程發生錯誤：\n{err_msg}"


class CSVReader(QObject):
    task_started = pyqtSignal(str, int, str, bool)
    task_finished = pyqtSignal(str)
    load_completed = pyqtSignal(CsvData)
    load_error = pyqtSignal(str)
    
    started = pyqtSignal()
    finished = pyqtSignal()
    cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_win = parent  # MainWindow
        self._current_worker = None

    def is_running(self) -> bool:
        return self._current_worker is not None and self._current_worker.isRunning()

    def is_cancelled(self) -> bool:
        return self._current_worker is not None and getattr(self._current_worker, "_is_cancelled", False)

    def cancel_task(self):
        if self._current_worker:
            self._current_worker.cancel()

    def start_load_task(self, source_path: str, output_path: str):
        from .io_panel_validator import validate_io_panel_inputs
        is_valid, parsed = validate_io_panel_inputs(
            self.parent_win,
            source_path=source_path,
            output_path=output_path,
            require_source_path=True,
            require_output_path=False,
        )
        if not is_valid:
            return

        worker_instance = CSVEditWorker(
            source_path=source_path,
            output_path=output_path
        )
        self._current_worker = worker_instance

        # 連接完成與錯誤信號
        worker_instance.finished_successfully.connect(self._on_worker_success)
        worker_instance.finished_with_error.connect(self._on_worker_error)

        # 連接進度、狀態、日誌信號到主視窗槽函數
        if self.parent_win:
            worker_instance.progress_updated.connect(self.parent_win.on_panel_progress)
            worker_instance.log_emitted.connect(self.parent_win.on_panel_log)
            worker_instance.status_updated.connect(self.parent_win.on_panel_status)

        # 啟動 Worker
        worker_instance.start()
        
        # 通知主視窗任務開始
        self.task_started.emit("載入中...", 0, "開始載入 CSV 資料以供編輯...", False)
        self.started.emit()

    def _on_worker_success(self, out_path):
        if not self._current_worker:
            return
        worker = self._current_worker
        
        # 轉換為共用資料結構 CsvData
        data = CsvData(
            all_rows=worker.loaded_rows,
            delimiter=getattr(worker, "delimiter", ","),
            encoding=getattr(worker, "encoding", "utf-8"),
            file_path=worker.source_path,
            num_cols=getattr(worker, "num_cols", 0)
        )
        # 先行標記背景載入任務結束，解鎖 UI，防止後續在 load_completed 回呼中自動啟動新任務時發生衝突
        self.task_finished.emit("finished")
        self.load_completed.emit(data)
        self.finished.emit()
        self._current_worker = None

    def _on_worker_error(self, err_msg):
        if "使用者已取消" in err_msg or "取消" in err_msg:
            self.task_finished.emit("cancelled")
            self.cancelled.emit()
        else:
            self.load_error.emit(err_msg)
            parent_win = self.parent_win.window() if self.parent_win else None
            QMessageBox.critical(parent_win, "載入中斷", f"載入編輯過程發生錯誤：\n{err_msg}")
            self.task_finished.emit("error")
            self.finished.emit()
        self._current_worker = None
