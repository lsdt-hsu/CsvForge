"""
FilterMixin — 過濾協調

職責：接收 EditPanel 發射的 request_filter Signal，建立 FilterWorker
並將結果傳回 DataEditorPanel。

私有屬性命名前綴 _filter_：
  self._filter_worker   — FilterWorker 執行緒實例
  self._filter_progress — QProgressDialog 進度對話框
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QMessageBox, QProgressDialog

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

        self._filter_progress = QProgressDialog("正在執行過濾...", "取消", 0, len(rows), self)
        self._filter_progress.setWindowTitle("請稍候")
        self._filter_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._filter_progress.setAutoClose(False)
        self._filter_progress.setAutoReset(False)
        self._filter_progress.show()

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
        self._filter_progress.canceled.connect(self._filter_worker.cancel)
        self._filter_worker.progress_updated.connect(self._filter_progress.setValue)
        self._filter_worker.filter_completed.connect(self.on_filter_completed)
        self._filter_worker.filter_error.connect(self.on_filter_error)
        self._filter_worker.start()

    def on_filter_completed(self: "MainWindow", matched_indices, elapsed_time: float) -> None:
        self.edit_content_panel.apply_filter(matched_indices)

        def close_dialog() -> None:
            if getattr(self, "_filter_progress", None):
                self._filter_progress.close()
                self._filter_progress = None

        if elapsed_time < 0.7:
            QTimer.singleShot(int((0.7 - elapsed_time) * 1000), close_dialog)
        else:
            close_dialog()

    def on_filter_error(self: "MainWindow", err_msg: str) -> None:
        if getattr(self, "_filter_progress", None):
            self._filter_progress.close()
            self._filter_progress = None
        QMessageBox.critical(self, "過濾錯誤", err_msg)
