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
        self.status_panel.append_log(level, message)

    def set_ui_enabled(self: "MainWindow", enabled: bool) -> None:
        self._ui_locked = not enabled

        # 啟用/停用各面板
        self.io_panel.set_enabled(enabled)
        self.left_panel.set_enabled(enabled)

        # 第一行為標題與存檔按鈕 (在 DataEditorPanel 內)
        if hasattr(self, "edit_content_panel"):
            self.edit_content_panel.chk_first_row_header.setEnabled(enabled)
            # 禁止/允許編輯 TableView
            self.edit_content_panel.set_table_editable(enabled)

    def switch_sidebar_tab(self: "MainWindow", tab_name: str, force_expand: bool = False) -> None:
        self.left_panel.switch_sidebar_tab(tab_name, force_expand)

    def get_active_panel(self: "MainWindow"):
        return self.left_panel.get_active_plugin()

    def lock_ui_from_panel(self: "MainWindow", lock: bool) -> None:
        self.set_ui_enabled(not lock)

    def on_panel_progress(self: "MainWindow", current: int, total: int) -> None:
        sender = self.sender()
        from plugin_sdk import BasePluginPanel
        if isinstance(sender, BasePluginPanel) and sender != self.left_panel.get_active_plugin():
            return
        self.on_worker_progress(current, total)

    def on_panel_status(self: "MainWindow", status: str) -> None:
        sender = self.sender()
        from plugin_sdk import BasePluginPanel
        if isinstance(sender, BasePluginPanel) and sender != self.left_panel.get_active_plugin():
            return
        self.task_status_str = status
        self.update_status_summary()

    def on_panel_log(self: "MainWindow", level: str, message: str) -> None:
        sender = self.sender()
        from plugin_sdk import BasePluginPanel
        if isinstance(sender, BasePluginPanel) and sender != self.left_panel.get_active_plugin():
            return
        self.append_log(level, message)
