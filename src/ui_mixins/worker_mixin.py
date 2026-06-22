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

        # 重置 UI 顯示狀態
        self.txt_log.clear()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0/0")
        self.elapsed_time_str = "00:00:00"

        # 根據 Worker 型別設定狀態文字
        from translation.translation_worker import CSVTranslatorWorker
        from data_editor.edit_worker import CSVEditWorker
        from edit.filter_worker import FilterWorker

        if isinstance(worker_instance, CSVEditWorker):
            self.task_status_str = "載入中..."
        elif isinstance(worker_instance, CSVTranslatorWorker):
            self.task_status_str = "翻譯中..."
        elif isinstance(worker_instance, FilterWorker):
            self.task_status_str = "過濾中..."
            self.edit_panel.update_status("過濾中...")
            self.edit_panel.write_log("INFO", "開始執行 CSV 資料過濾...")
            
            rows_count = len(self.context.all_rows)
            self.progress_bar.setRange(0, rows_count)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat(f"0/{rows_count}")
        else:
            self.task_status_str = "執行中..."

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

        # 針對不同 Worker 綁定完成/錯誤回呼
        if isinstance(worker_instance, FilterWorker):
            worker_instance.filter_completed.connect(self.on_filter_completed)
            worker_instance.filter_error.connect(self.on_filter_error)
        else:
            worker_instance.finished_successfully.connect(self.on_worker_success)
            worker_instance.finished_with_error.connect(self.on_worker_error)

        worker_instance.start()

        # 防止系統休眠（僅翻譯任務）
        if isinstance(worker_instance, CSVTranslatorWorker):
            from utils import prevent_sleep
            self._worker_sleep_prevented = prevent_sleep(True)
            if self._worker_sleep_prevented:
                self.append_log("INFO", "已成功通知系統在翻譯期間不要進入休眠狀態。")

        active_panel.lock_ui(True)

    def update_status_summary(self: "MainWindow") -> None:
        self.lbl_status_summary.setText(
            f"已用時間：{self.elapsed_time_str} | 狀態：{self.task_status_str}"
        )

    def on_worker_progress(self: "MainWindow", current: int, total: int) -> None:
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{current}/{total}")

    def update_elapsed_time(self: "MainWindow") -> None:
        elapsed = int(time.time() - self.start_time)
        hrs = elapsed // 3600
        mins = (elapsed % 3600) // 60
        secs = elapsed % 60
        self.elapsed_time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        self.update_status_summary()

    def on_worker_success(self: "MainWindow", out_path: str) -> None:
        self.timer.stop()
        self.get_active_panel().lock_ui(False)

        # 恢復系統休眠
        if getattr(self, "_worker_sleep_prevented", False):
            from utils import prevent_sleep
            prevent_sleep(False)
            self._worker_sleep_prevented = False
            self.append_log("INFO", "已恢復系統正常休眠設定。")

        if self.worker and self.worker._is_cancelled:
            self.task_status_str = "已取消"
            self.update_status_summary()
            title, msg = self.worker.get_cancel_message(out_path)
            from data_editor.edit_worker import CSVEditWorker
            if not isinstance(self.worker, CSVEditWorker):
                QMessageBox.information(self, title, msg)
        else:
            self.task_status_str = "完成"
            self.update_status_summary()

            from data_editor.edit_worker import CSVEditWorker
            if isinstance(self.worker, CSVEditWorker) and hasattr(self.worker, "loaded_rows"):
                start_row = 1
                try:
                    start_row = int(self.context.start_row)
                except ValueError:
                    pass
                end_row = None
                if self.context.end_row:
                    try:
                        end_row = int(self.context.end_row)
                    except ValueError:
                        pass

                src_path = self.context.source_path
                self.edit_content_panel.load_data(self.worker.loaded_rows, start_row, end_row, file_path=src_path)
                self.edit_content_panel.set_delimiter(getattr(self.worker, "delimiter", ","))

                # 更新結束行號 Placeholder
                total_rows = len(self.worker.loaded_rows)
                self.txt_end_row.setPlaceholderText(f"預設至檔尾 ({total_rows})")

                # 更新過濾面板與翻譯面板控制項
                loaded_rows = self.worker.loaded_rows
                if loaded_rows:
                    num_cols = max(len(r) for r in loaded_rows)
                    is_hdr = self.edit_content_panel.is_first_row_header()
                    headers = loaded_rows[0] if is_hdr else None
                    # 重新套用的 rules 設定由 EditPanel.restore_from_config() 負責，
                    # 新架構不需要此先前的防重置邏輯
                    self.edit_panel.update_column_dropdowns(num_cols, headers)
                    self.translation_panel.show_controls()

                    # 儲存設定由 on_request_start_worker 負責，此處不重複存檔

            if not isinstance(self.worker, CSVEditWorker):
                title, msg = self.worker.get_success_message(out_path)
                QMessageBox.information(self, title, msg)

    def on_worker_error(self: "MainWindow", err_msg: str) -> None:
        self.timer.stop()
        self.task_status_str = "錯誤"
        self.update_status_summary()
        self.get_active_panel().lock_ui(False)

        # 恢復系統休眠
        if getattr(self, "_worker_sleep_prevented", False):
            from utils import prevent_sleep
            prevent_sleep(False)
            self._worker_sleep_prevented = False
            self.append_log("INFO", "已恢復系統正常休眠設定。")

        title, msg = self.worker.get_error_message(err_msg)
        QMessageBox.critical(self, title, msg)

    def cancel_task(self: "MainWindow") -> None:
        if self.worker:
            self.task_status_str = "正在中斷工作..."
            self.update_status_summary()
            self.worker.cancel()
            self.update_start_button_ui()

    def on_filter_completed(self: "MainWindow", matched_indices, elapsed_time: float) -> None:
        self.timer.stop()
        self.edit_content_panel.apply_filter(matched_indices)
        self.edit_panel.lock_ui(False)
        self.edit_panel.update_status("完成")
        self.edit_panel.write_log("SUCCESS", f"過濾完成！共匹配 {len(matched_indices) if matched_indices is not None else 0} 筆資料，耗時 {elapsed_time:.2f} 秒。")

    def on_filter_error(self: "MainWindow", err_msg: str) -> None:
        self.timer.stop()
        self.edit_panel.lock_ui(False)
        self.edit_panel.update_status("錯誤")
        self.edit_panel.write_log("ERROR", f"過濾錯誤：{err_msg}")
        QMessageBox.critical(self, "過濾錯誤", err_msg)
