# src/ui_mixins/worker_mixin.py
"""
WorkerMixin — Worker 生命週期管理 (重構解耦版)

職責：管理背景任務生命週期通知（啟動、結束、取消）、已用時間計時、防止休眠等。
本模組完全不接觸與持有具體的 QThread Worker 實例，亦無 hasattr/getattr 猜測。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui import MainWindow


class WorkerMixin:

    def is_any_task_running(self: "MainWindow") -> bool:
        """查詢系統目前是否有背景任務（載入、儲存或外掛）正在執行"""
        # 1. 查詢活動外掛
        active = self.left_panel.get_active_plugin()
        if active and active.is_task_running():
            return True
        # 2. 查詢 IO 面板
        if self.io_panel.loader.is_running() or self.io_panel.writer.is_running():
            return True
        return False

    def on_task_started(self: "MainWindow", task_name: str, total_rows: int, initial_log: str, prevent_sleep: bool) -> None:
        """當背景任務啟動時由 Panel/IO 元件觸發"""
        # 開始任務前統一儲存設定（鎖定 UI 前）
        self.save_settings()
        self._task_failed = False

        # 重置 UI 顯示狀態
        # 🔪 用全新 QTextDocument 取代 clear()，徹底釋放舊 Document 的 fragment pool 記憶體
        from PyQt6.QtGui import QTextDocument
        if self.status_panel:
            old_doc = self.status_panel.txt_log.document()
            self.status_panel.txt_log.setDocument(QTextDocument(self.status_panel.txt_log))
            if old_doc:
                old_doc.deleteLater()
        self.elapsed_time_str = "00:00:00"

        # 根據參數設定進度條與狀態文字
        if self.status_panel:
            if total_rows > 0:
                self.status_panel.progress_bar.setRange(0, total_rows)
                self.status_panel.progress_bar.setValue(0)
                self.status_panel.progress_bar.setFormat(f"0/{total_rows}")
            else:
                self.status_panel.progress_bar.setRange(0, 0)
                self.status_panel.progress_bar.setValue(0)
                self.status_panel.progress_bar.setFormat("0/0")

        self.task_status_str = task_name

        # 記錄初始日誌
        if initial_log:
            self.append_log("INFO", initial_log)

        self.update_status_summary()

        self.start_time = time.time()
        self.timer.start(1000)

        # 根據參數決定是否防止系統休眠
        if prevent_sleep:
            self._worker_sleep_prevented = self._set_sleep_prevention(True)
            if self._worker_sleep_prevented:
                self.append_log("INFO", "已成功通知系統在任務期間不要進入休眠狀態。")

        # 鎖定當前活動面板 UI
        self.lock_ui_from_panel(True)

    def update_status_summary(self: "MainWindow") -> None:
        if self.status_panel:
            self.status_panel.update_status(self.elapsed_time_str, self.task_status_str)

    def on_worker_progress(self: "MainWindow", current: int, total: int) -> None:
        if self.status_panel:
            self.status_panel.update_progress(current, total)

    def update_elapsed_time(self: "MainWindow") -> None:
        elapsed = int(time.time() - self.start_time)
        hrs = elapsed // 3600
        mins = (elapsed % 3600) // 60
        secs = elapsed % 60
        self.elapsed_time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        self.update_status_summary()

    def on_task_finished(self: "MainWindow", status: str) -> None:
        """當背景任務結束時由 Panel/IO 元件觸發"""
        self.timer.stop()
        
        # 解鎖 UI
        self.lock_ui_from_panel(False)

        # 恢復系統休眠設定
        if getattr(self, "_worker_sleep_prevented", False):
            self._set_sleep_prevention(False)
            self._worker_sleep_prevented = False
            self.append_log("INFO", "已恢復系統正常休眠設定。")

        # 根據狀態決定狀態列文字
        if status == "error":
            self.task_status_str = "錯誤"
            self._task_failed = True
        elif status == "cancelled":
            self.task_status_str = "已取消"
        else:
            self.task_status_str = "完成"

        self.update_status_summary()

    def cancel_task(self: "MainWindow") -> None:
        """使用者點擊取消按鈕時觸發"""
        active_panel = self.get_active_panel()
        if active_panel and active_panel.is_task_running():
            self.task_status_str = "正在中斷工作..."
            self.update_status_summary()
            active_panel.cancel_task()
        elif self.io_panel.loader.is_running():
            self.task_status_str = "正在中斷工作..."
            self.update_status_summary()
            self.io_panel.loader.cancel_task()
        elif self.io_panel.writer.is_running():
            self.task_status_str = "正在中斷工作..."
            self.update_status_summary()
            self.io_panel.writer.cancel_task()

    def _set_sleep_prevention(self, prevent: bool = True) -> bool:
        """
        Prevent Windows from sleeping when prevent is True, and restore sleep behavior when False.
        Returns True if the operation succeeded, False otherwise.
        """
        import os
        if os.name == 'nt':
            try:
                import ctypes
                ES_CONTINUOUS = 0x80000000
                ES_SYSTEM_REQUIRED = 0x00000001
                if prevent:
                    # Prevent sleep
                    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
                else:
                    # Restore sleep behavior
                    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                return True
            except Exception as e:
                print(f"Failed to set thread execution state: {e}")
                return False
        return False

