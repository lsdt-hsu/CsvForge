"""
UiStateMixin — UI 狀態管理

職責：日誌輸出、控制項啟停、側邊欄分頁切換、開始按鈕狀態維護。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt

from ui_constants import SIDEBAR_FULL_WIDTH, SIDEBAR_MIN_WIDTH

if TYPE_CHECKING:
    from ui import MainWindow


class UiStateMixin:

    @property
    def is_ui_locked(self: "MainWindow") -> bool:
        return getattr(self, "_ui_locked", False)

    def append_log(self: "MainWindow", level: str, message: str) -> None:
        color_map = {
            "INFO": "#c0caf5",
            "SUCCESS": "#9ece6a",
            "WARNING": "#e0af68",
            "ERROR": "#f7768e",
        }
        color = color_map.get(level, "#c0caf5")
        timestamp = time.strftime("[%H:%M:%S]")
        log_html = (
            f'<font color="#565f89">{timestamp}</font> '
            f'<font color="{color}">[{level}] {message}</font>'
        )

        # 將新日誌插入至頂端（倒序顯示）
        cursor = self.txt_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.insertHtml(log_html)
        cursor.insertBlock()

        # 超過 10001 行時移除最舊的一行
        if self.txt_log.document().blockCount() > 10001:
            end_cursor = self.txt_log.textCursor()
            end_cursor.movePosition(end_cursor.MoveOperation.End)
            end_cursor.movePosition(
                end_cursor.MoveOperation.PreviousBlock, end_cursor.MoveMode.KeepAnchor
            )
            end_cursor.removeSelectedText()

    def set_ui_enabled(self: "MainWindow", enabled: bool) -> None:
        self._ui_locked = not enabled

        # 來源與輸出 CSV 編輯與瀏覽
        self.txt_src_path.setEnabled(enabled)
        self.txt_out_path.setEnabled(enabled)
        if hasattr(self, "btn_src_browse"):
            self.btn_src_browse.setEnabled(enabled)
        if hasattr(self, "btn_out_browse"):
            self.btn_out_browse.setEnabled(enabled)
        if hasattr(self, "btn_swap"):
            self.btn_swap.setEnabled(enabled)

        # 編輯參數
        self.txt_start_row.setEnabled(enabled)
        self.txt_end_row.setEnabled(enabled)
        self.txt_src_col.setEnabled(enabled)
        self.txt_tgt_col.setEnabled(enabled)

        # 功能面板
        self.translation_panel.set_enabled(enabled)
        self.edit_panel.set_enabled(enabled)

        # 第一行為標題與存檔按鈕 (在 DataEditorPanel 內)
        if hasattr(self, "edit_content_panel"):
            self.edit_content_panel.chk_first_row_header.setEnabled(enabled)
            self.edit_content_panel.btn_save.setEnabled(enabled and self.edit_content_panel.is_modified)
            # 禁止/允許編輯 TableView
            self.edit_content_panel.set_table_editable(enabled)

        # 切換功能面板按鈕
        if hasattr(self, "btn_translate"):
            self.btn_translate.setEnabled(enabled)
        if hasattr(self, "btn_edit"):
            self.btn_edit.setEnabled(enabled)

        self.update_start_button_ui()

    def switch_sidebar_tab(self: "MainWindow", tab_name: str) -> None:
        if self.is_ui_locked:
            return

        is_task_running = self.worker is not None and self.worker.isRunning()

        # 判斷點選的是否為當前活躍的分頁
        is_same_tab = False
        if tab_name == "translate" and self.sidebar_stacked.currentWidget() == self.translation_panel:
            is_same_tab = True
        elif tab_name == "edit" and self.sidebar_stacked.currentWidget() == self.edit_panel:
            is_same_tab = True

        # 任務執行中禁止切換至其他功能面板
        if is_task_running and not is_same_tab:
            return

        if self.sidebar.isVisible() and is_same_tab:
            # 收合
            self.sidebar.setVisible(False)
            self.v_line.setVisible(False)
            self.left_container.setFixedWidth(SIDEBAR_MIN_WIDTH)
            self.btn_translate.setProperty("active", False)
            self.btn_edit.setProperty("active", False)
        else:
            # 展開並切換
            self.sidebar.setVisible(True)
            self.v_line.setVisible(True)
            self.left_container.setFixedWidth(SIDEBAR_FULL_WIDTH)

            if tab_name == "translate":
                self.sidebar_stacked.setCurrentWidget(self.translation_panel)
                self.btn_translate.setProperty("active", True)
                self.btn_edit.setProperty("active", False)
            elif tab_name == "edit":
                self.sidebar_stacked.setCurrentWidget(self.edit_panel)
                self.btn_translate.setProperty("active", False)
                self.btn_edit.setProperty("active", True)

        # 刷新按鈕樣式
        self.btn_translate.style().polish(self.btn_translate)
        self.btn_edit.style().polish(self.btn_edit)

        self.update_start_button_ui()

    def get_active_panel(self: "MainWindow"):
        if self.sidebar.isVisible() and self.sidebar_stacked.currentWidget() == self.edit_panel:
            return self.edit_panel
        return self.translation_panel

    def get_start_button_state(self: "MainWindow") -> str:
        if self.worker is not None and self.worker.isRunning():
            if self.worker._is_cancelled:
                return "disabled"
            else:
                return "critical"
        return "normal"

    def update_start_button_ui(self: "MainWindow") -> None:
        from translation.translation_worker import CSVTranslatorWorker
        from data_editor.edit_worker import CSVEditWorker

        state = self.get_start_button_state()

        style_disabled = "background-color: #24283b; color: #565f89;"
        style_critical = "background-color: #f7768e; color: #1a1b26;"
        style_normal = ""

        # 1. 載入按鈕 (btn_start)
        if self.worker is not None and isinstance(self.worker, CSVEditWorker) and self.worker.isRunning():
            if state == "disabled":
                self.btn_start.setText("正在停止...")
                self.btn_start.setEnabled(False)
                self.btn_start.setStyleSheet(style_disabled)
            else:  # critical
                self.btn_start.setText("停止載入")
                self.btn_start.setEnabled(True)
                self.btn_start.setStyleSheet(style_critical)
        else:
            self.btn_start.setText("載入")
            is_any_running = self.worker is not None and self.worker.isRunning()
            self.btn_start.setEnabled(not is_any_running)
            self.btn_start.setStyleSheet(style_normal)

        # 2. 開始翻譯按鈕 (translation_panel.btn_start)
        if hasattr(self.translation_panel, "btn_start"):
            if self.worker is not None and isinstance(self.worker, CSVTranslatorWorker) and self.worker.isRunning():
                if state == "disabled":
                    self.translation_panel.btn_start.setText("正在停止...")
                    self.translation_panel.btn_start.setEnabled(False)
                    self.translation_panel.btn_start.setStyleSheet(style_disabled)
                else:  # critical
                    self.translation_panel.btn_start.setText("停止翻譯")
                    self.translation_panel.btn_start.setEnabled(True)
                    self.translation_panel.btn_start.setStyleSheet(style_critical)
            else:
                self.translation_panel.btn_start.setText("開始翻譯")
                is_any_running = self.worker is not None and self.worker.isRunning()
                self.translation_panel.btn_start.setEnabled(not is_any_running)
                self.translation_panel.btn_start.setStyleSheet(style_normal)

    def on_start_button_clicked(self: "MainWindow") -> None:
        state = self.get_start_button_state()
        if state == "disabled":
            return

        sender = self.sender()
        if hasattr(self.translation_panel, "btn_start") and sender == self.translation_panel.btn_start:
            if state == "critical":
                self.cancel_task()
            else:
                self.translation_panel.start_translation_task()
        else:
            if state == "critical":
                self.cancel_task()
            else:
                self.edit_content_panel.start_load_task()

    def lock_ui_from_panel(self: "MainWindow", lock: bool) -> None:
        self.set_ui_enabled(not lock)

    def on_panel_progress(self: "MainWindow", current: int, total: int) -> None:
        self.on_worker_progress(current, total)

    def on_panel_status(self: "MainWindow", status: str) -> None:
        self.task_status_str = status
        self.update_status_summary()

    def on_panel_log(self: "MainWindow", level: str, message: str) -> None:
        self.append_log(level, message)
