import os
import csv
import time
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
from csv_worker import BaseCSVWorker
from utils import ThrottledProgress

def save_csv_file(out_path: str, all_rows: list, delimiter: str) -> None:
    """底層純同步寫檔函數"""
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerows(all_rows)


class CSVWriteWorker(BaseCSVWorker):
    def __init__(self, output_path, all_rows, delimiter):
        super().__init__(source_path="", output_path=output_path)
        self.all_rows = all_rows
        self.delimiter = delimiter
        self.task_name = "儲存中..."
        
        self.progress_throttler = ThrottledProgress(self.progress_updated, min_interval=0.2)
        self.log_throttler = ThrottledProgress(self.log_emitted, min_interval=0.2)

    def run(self):
        try:
            self.log_throttler.emit("INFO", "開始儲存 CSV 資料...", force=True)
            total_rows = len(self.all_rows)
            
            out_dir = os.path.dirname(self.output_path)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
                
            with open(self.output_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f, delimiter=self.delimiter)
                
                # 一行一行寫入以回報進度，在大檔案下不卡 UI
                for idx, row in enumerate(self.all_rows):
                    if self._is_cancelled:
                        raise RuntimeError("使用者已取消儲存工作")
                    
                    writer.writerow(row)
                    
                    # 限頻發送進度
                    self.progress_throttler.emit(idx + 1, total_rows)
                    self.log_throttler.emit("INFO", f"已寫入 {idx + 1} 行...")
            
            self.progress_throttler.emit(total_rows, total_rows, force=True)
            self.log_throttler.emit("SUCCESS", f"資料儲存成功，共 {total_rows} 行。", force=True)
            self.finished_successfully.emit(self.output_path)
            
        except Exception as e:
            self.log_throttler.emit("ERROR", f"儲存過程發生錯誤：{str(e)}", force=True)
            self.finished_with_error.emit(str(e))

    def get_success_message(self, out_path):
        return "成功", "編輯資料儲存完成！"

    def get_cancel_message(self, out_path):
        return "中斷", "已取消編輯資料儲存！"

    def get_error_message(self, err_msg):
        return "儲存中斷", f"儲存過程發生錯誤：\n{err_msg}"


class CSVWriter(QObject):
    request_start_worker = pyqtSignal(object)
    save_completed = pyqtSignal(str)
    save_error = pyqtSignal(str)
    
    started = pyqtSignal()
    finished = pyqtSignal()
    cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_win = parent  # MainWindow
        self._current_worker = None
        self.is_silent = False

    def is_running(self) -> bool:
        return self._current_worker is not None and self._current_worker.isRunning()

    def is_cancelled(self) -> bool:
        return self._current_worker is not None and getattr(self._current_worker, "_is_cancelled", False)

    def cancel_task(self):
        if self._current_worker:
            self._current_worker.cancel()

    def start_save_task(self, output_path: str, all_rows: list, delimiter: str, silent: bool = False):
        self.is_silent = silent
        worker_instance = CSVWriteWorker(output_path, all_rows, delimiter)
        self._current_worker = worker_instance

        # 連接完成與錯誤信號
        worker_instance.finished_successfully.connect(self._on_worker_success)
        worker_instance.finished_with_error.connect(self._on_worker_error)

        # 請求主視窗啟動 Worker Thread
        self.request_start_worker.emit(worker_instance)
        self.started.emit()

    def _on_worker_success(self, out_path):
        self.save_completed.emit(out_path)
        
        # 僅在非靜默狀態下彈出提示
        if not self.is_silent:
            parent_win = self.parent_win.window() if self.parent_win else None
            QMessageBox.information(parent_win, "成功", f"存檔成功！\n檔案已儲存至：\n{out_path}")
            
        self.finished.emit()
        self._current_worker = None

    def _on_worker_error(self, err_msg):
        if "使用者已取消" in err_msg:
            self.cancelled.emit()
        else:
            self.save_error.emit(err_msg)
            # 僅在非靜默狀態下彈出錯誤提示
            if not self.is_silent:
                parent_win = self.parent_win.window() if self.parent_win else None
                QMessageBox.critical(parent_win, "儲存中斷", f"儲存過程發生錯誤：\n{err_msg}")
            self.finished.emit()
        self._current_worker = None
