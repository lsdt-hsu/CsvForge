"""
FilterMixin — 過濾協調

職責：接收 EditPanel 發射的 request_filter Signal，建立 FilterWorker
並將結果傳回 DataEditorPanel。

私有屬性命名前綴 _filter_：
  self._filter_worker   — FilterWorker 執行緒實例
  self._filter_progress — QProgressDialog 進度對話框
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from ui import MainWindow


class FilterMixin:

    def start_filtering(self: "MainWindow", filter_config: dict) -> None:
        rows = self.edit_content_panel.get_all_rows()
        if not rows:
            QMessageBox.warning(self, "錯誤", "請先載入 CSV 資料。")
            return

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

        src_col = 1
        try:
            src_col = int(self.txt_src_col.text())
        except ValueError:
            pass

        tgt_col = 1
        try:
            tgt_col = int(self.txt_tgt_col.text())
        except ValueError:
            pass

        is_header = self.edit_content_panel.is_first_row_header()

        from edit.filter_worker import FilterWorker

        self.edit_panel.lock_ui(True)
        self.edit_panel.update_status("過濾中...")
        self.edit_panel.write_log("INFO", "開始執行 CSV 資料過濾...")

        self.progress_bar.setRange(0, len(rows))
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"0/{len(rows)}")
        self.elapsed_time_str = "00:00:00"
        self.update_status_summary()

        self.start_time = time.time()
        self.timer.start(1000)

        self._filter_worker = FilterWorker(
            all_rows=rows,
            start_row=start_row,
            end_row=end_row,
            is_header=is_header,
            src_col=src_col,
            tgt_col=tgt_col,
            filter_config=filter_config,
            parent=self
        )
        self._filter_worker.progress_updated.connect(self.edit_panel.update_progress)
        self._filter_worker.filter_completed.connect(self.on_filter_completed)
        self._filter_worker.filter_error.connect(self.on_filter_error)
        self._filter_worker.start()

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
