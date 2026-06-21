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

    def start_load_task(self: "MainWindow") -> None:
        # 讀取通用設定值
        src_path = self.txt_src_path.text().strip()
        out_path = self.txt_out_path.text().strip()
        start_row = self.txt_start_row.text().strip()
        end_row = self.txt_end_row.text().strip()

        from data_editor.edit_worker import CSVEditWorker
        worker_instance = CSVEditWorker(
            source_path=src_path,
            output_path=out_path,
            start_row=start_row,
            end_row=end_row
        )

        # 多態輸入驗證
        is_valid, err_msg = worker_instance.validate_inputs()
        if not is_valid:
            QMessageBox.warning(self, "輸入錯誤", err_msg)
            return

        self.worker = worker_instance

        # 重置 UI 顯示狀態
        self.txt_log.clear()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0/0")
        self.elapsed_time_str = "00:00:00"
        self.task_status_str = "載入中..."
        self.update_status_summary()

        self.start_time = time.time()
        self.timer.start(1000)

        active_panel = self.get_active_panel()
        self.worker.progress_updated.connect(active_panel.update_progress)
        self.worker.log_emitted.connect(active_panel.write_log)
        self.worker.finished_successfully.connect(self.on_worker_success)
        self.worker.finished_with_error.connect(self.on_worker_error)

        self.worker.start()

        active_panel.lock_ui(True)

    def start_translation_task(self: "MainWindow") -> None:
        # 檢查點：來源與輸出不為空且相同
        src_path = self.txt_src_path.text().strip()
        out_path = self.txt_out_path.text().strip()
        if src_path and out_path and src_path == out_path:
            QMessageBox.warning(self, "路徑重複", "來源 CSV 與輸出 CSV 路徑相同，無法開始任務！請變更輸出路徑。")
            return

        start_row = self.txt_start_row.text().strip()
        end_row = self.txt_end_row.text().strip()

        from translation.translation_worker import CSVTranslatorWorker
        src_col = self.txt_src_col.text().strip()
        tgt_col = self.txt_tgt_col.text().strip()
        src_lang = self.translation_panel.get_src_lang()
        tgt_lang = self.translation_panel.get_tgt_lang()
        batch_interval = self.translation_panel.get_batch_interval()
        single_interval = self.translation_panel.get_single_interval()
        batch_size = self.translation_panel.get_batch_size()

        worker_instance = CSVTranslatorWorker(
            source_path=src_path,
            output_path=out_path,
            start_row=start_row,
            end_row=end_row,
            source_col=src_col,
            target_col=tgt_col,
            source_lang=src_lang,
            target_lang=tgt_lang,
            batch_interval=batch_interval,
            single_interval=single_interval,
            batch_size=batch_size
        )

        # 多態輸入驗證
        is_valid, err_msg = worker_instance.validate_inputs()
        if not is_valid:
            QMessageBox.warning(self, "輸入錯誤", err_msg)
            return

        self.worker = worker_instance

        # 重置 UI 顯示狀態
        self.txt_log.clear()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0/0")
        self.elapsed_time_str = "00:00:00"
        self.task_status_str = "翻譯中..."
        self.update_status_summary()

        self.start_time = time.time()
        self.timer.start(1000)

        active_panel = self.get_active_panel()
        self.worker.progress_updated.connect(active_panel.update_progress)
        self.worker.log_emitted.connect(active_panel.write_log)
        if hasattr(self.worker, "status_updated"):
            self.worker.status_updated.connect(active_panel.update_status)
        self.worker.finished_successfully.connect(self.on_worker_success)
        self.worker.finished_with_error.connect(self.on_worker_error)

        self.worker.start()

        # 防止系統休眠（僅翻譯任務）
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
                    start_row = int(self.txt_start_row.text())
                except ValueError:
                    pass
                end_row = None
                if self.txt_end_row.text().strip():
                    try:
                        end_row = int(self.txt_end_row.text())
                    except ValueError:
                        pass

                src_path = self.txt_src_path.text().strip()
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
                    self.edit_panel.update_column_dropdowns(num_cols, headers)
                    self.translation_panel.show_controls()

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
