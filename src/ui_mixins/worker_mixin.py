"""
WorkerMixin — Worker 生命週期管理

職責：啟動/取消 Worker 執行緒、進度更新、成功/失敗回調處理。

私有屬性命名前綴：無（Worker 狀態屬性由 MainWindow.__init__ 定義）
  self.worker          — 當前執行中的 Worker 實例
  self.start_time      — 任務開始的 UNIX timestamp
  self.timer           — QTimer，每秒更新已用時間
  self._worker_sleep_prevented — 是否已阻止系統休眠（此 Mixin 專用）
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from ui import MainWindow


class WorkerMixin:

    def on_request_start_worker(self: "MainWindow", worker_instance) -> None:
        # 開始任務前統一儲存設定（鎖定 UI 前）
        self.save_settings()
        self.worker = worker_instance
        self._task_failed = False

        # 重置 UI 顯示狀態
        self.status_panel.txt_log.clear()
        self.elapsed_time_str = "00:00:00"

        # 根據 Worker 屬性設定進度條與狀態文字
        total_rows = getattr(worker_instance, "initial_progress_total", 0)
        if total_rows > 0:
            self.status_panel.progress_bar.setRange(0, total_rows)
            self.status_panel.progress_bar.setValue(0)
            self.status_panel.progress_bar.setFormat(f"0/{total_rows}")
        else:
            self.status_panel.progress_bar.setRange(0, 0)
            self.status_panel.progress_bar.setValue(0)
            self.status_panel.progress_bar.setFormat("0/0")

        self.task_status_str = getattr(worker_instance, "task_name", "執行中...")

        # 讀取並記錄初始日誌
        initial_log = getattr(worker_instance, "initial_log", None)
        if initial_log:
            self.append_log("INFO", initial_log)

        self.update_status_summary()

        self.start_time = time.time()
        self.timer.start(1000)

        active_panel = self.get_active_panel()

        # 連接共同訊號
        if hasattr(worker_instance, "progress_updated"):
            worker_instance.progress_updated.connect(active_panel.update_progress)
        if hasattr(worker_instance, "log_emitted"):
            worker_instance.log_emitted.connect(active_panel.write_log)
        if hasattr(worker_instance, "status_updated"):
            worker_instance.status_updated.connect(active_panel.update_status)

        # 監聽通用錯誤以判定結束狀態
        if hasattr(worker_instance, "finished_with_error"):
            worker_instance.finished_with_error.connect(self._on_worker_error_generic)
        if hasattr(worker_instance, "filter_error"):
            worker_instance.filter_error.connect(self._on_worker_error_generic)

        # 連接 QThread 標準結束訊號進行通用清理
        worker_instance.finished.connect(self.on_worker_finished)

        worker_instance.start()

        # 根據 Worker 需求決定是否防止系統休眠
        if getattr(worker_instance, "prevent_sleep", False):
            from utils import prevent_sleep
            self._worker_sleep_prevented = prevent_sleep(True)
            if self._worker_sleep_prevented:
                self.append_log("INFO", "已成功通知系統在任務期間不要進入休眠狀態。")

        active_panel.lock_ui(True)

    def update_status_summary(self: "MainWindow") -> None:
        self.status_panel.update_status(self.elapsed_time_str, self.task_status_str)

    def on_worker_progress(self: "MainWindow", current: int, total: int) -> None:
        self.status_panel.update_progress(current, total)

    def update_elapsed_time(self: "MainWindow") -> None:
        elapsed = int(time.time() - self.start_time)
        hrs = elapsed // 3600
        mins = (elapsed % 3600) // 60
        secs = elapsed % 60
        self.elapsed_time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        self.update_status_summary()

    def _on_worker_error_generic(self: "MainWindow", err_msg: str) -> None:
        self._task_failed = True

    def on_worker_finished(self: "MainWindow") -> None:
        self.timer.stop()
        
        # 解鎖 UI
        active_panel = self.get_active_panel()
        if active_panel:
            active_panel.lock_ui(False)

        # 恢復系統休眠設定
        if getattr(self, "_worker_sleep_prevented", False):
            from utils import prevent_sleep
            prevent_sleep(False)
            self._worker_sleep_prevented = False
            self.append_log("INFO", "已恢復系統正常休眠設定。")

        # 根據狀態決定狀態列文字
        if getattr(self, "_task_failed", False):
            self.task_status_str = "錯誤"
        elif self.worker and getattr(self.worker, "_is_cancelled", False):
            self.task_status_str = "已取消"
        else:
            self.task_status_str = "完成"

        self.update_status_summary()

    def cancel_task(self: "MainWindow") -> None:
        if self.worker:
            self.task_status_str = "正在中斷工作..."
            self.update_status_summary()
            self.worker.cancel()

