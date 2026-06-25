# -*- coding: utf-8 -*-
"""
SettingsMixin — 設定持久化與 Splitter 尺寸管理

職責：
  - 套用視窗組態（apply_window_config）
  - 還原所有面板的 UI 初始狀態（_restore_all_panel_configs）
  - 在特定時機呼叫 SettingsManager.save() 觸發存檔
  - 管理面板展開/收合（toggle_*），切換時立即更新對應 Config 的 dirty flag，
    但不觸發存檔（存檔時機由 save_settings() 統一控制）

Qt 事件覆寫注意事項：
  showEvent() 必須呼叫 super().showEvent(event)，以確保 MRO
  鏈最終傳遞到 QMainWindow，不中斷 Qt 原生視窗初始化流程。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox

from settings_manager import SettingsManager
from ui_constants import (
    WINDOW_DEFAULT_WIDTH,
    WINDOW_DEFAULT_HEIGHT,
    SIDEBAR_MIN_WIDTH,
)

if TYPE_CHECKING:
    from ui import MainWindow


class SettingsMixin:

    # ── 視窗組態套用 ──────────────────────────────────────────────────────────

    def apply_window_config(self: "MainWindow") -> None:
        """從 WindowConfig 套用視窗幾何（座標、大小、最大化）。"""
        cfg = self.context.window_config
        self.setGeometry(cfg.x, cfg.y, cfg.width, cfg.height)
        if cfg.is_maximized:
            self.showMaximized()

    def _restore_all_panel_configs(self: "MainWindow") -> None:
        """
        依序從 AppContext 取得各 Config 物件，還原各面板的 UI 初始狀態。
        在 SettingsManager.load() 完成後、視窗顯示前由 __init__ 呼叫。
        """
        try:
            self.io_panel.apply_config(self.context.io_panel_config)
            self.left_panel.apply_config(self.context.side_panel_config, self.context.main_config)
            self.status_panel.apply_config(self.context.status_panel_config)
            self.edit_content_panel.restore_from_config()
        except Exception:
            pass  # 設定還原失敗時靜默略過，避免影響程式啟動


    # ── 設定儲存 ──────────────────────────────────────────────────────────────

    def save_settings(self: "MainWindow") -> None:
        """
        更新所有由 MainWindow 管理的 Config 物件，再呼叫 SettingsManager.save()。

        【儲存時機】
        由 MainWindow 在以下特定時機呼叫（透過 WorkerMixin 或 closeEvent）：
        1. 開始大型任務（載入檔案、翻譯、過濾）— WorkerMixin.on_request_start_worker()
        2. 關閉程式 — ui.py closeEvent()

        【忽略機制】
        若所有 Config 的 dirty == False，SettingsManager.save() 將直接回傳，不寫入檔案。
        """
        self._update_window_config()
        self.left_panel.update_config(self.context.side_panel_config, self.context.main_config)
        self.io_panel.update_config(self.context.io_panel_config)
        self.status_panel.update_config(self.context.status_panel_config, self.right_splitter.sizes())
        SettingsManager.save(self._configs, self.settings_path)

    def _update_window_config(self: "MainWindow") -> None:
        is_max = self.isMaximized()
        geom = self.normalGeometry() if is_max else self.geometry()
        cfg = self.context.window_config
        cfg.x = geom.x()
        cfg.y = geom.y()
        cfg.width = geom.width()
        cfg.height = geom.height()
        cfg.is_maximized = is_max
        cfg.dirty = True

    # ── Splitter 事件 ─────────────────────────────────────────────────────────

    def on_splitter_moved(self: "MainWindow", pos: int, index: int) -> None:
        cfg = self.context.status_panel_config
        if not cfg.collapsed:
            sizes = self.right_splitter.sizes()
            if len(sizes) > 1:
                cfg.expanded_height = sizes[1]
                cfg.dirty = True

    def showEvent(self: "MainWindow", event) -> None:
        """Qt 事件覆寫：視窗首次顯示後套用 Splitter 初始尺寸。
        必須呼叫 super().showEvent(event) 維持 MRO 鏈完整性。
        """
        super().showEvent(event)  # ← MRO 鏈傳遞至 QMainWindow，勿省略
        if not self._splitter_applied:
            self._splitter_applied = True
            QTimer.singleShot(0, self.apply_splitter_sizes)

    def _calc_splitter_sizes(self: "MainWindow", available_h: int, expanded_height: int) -> tuple[int, int]:
        """依可用高度與展開高度計算 [editor_h, status_h]。"""
        status_h = max(140, expanded_height)
        editor_h = max(200, available_h - status_h)
        if editor_h < 200:
            editor_h = 200
            status_h = max(140, available_h - 200)
        return editor_h, status_h

    def apply_splitter_sizes(self: "MainWindow") -> None:
        cfg = self.context.status_panel_config
        total_h = self.right_splitter.height()
        handle_w = self.right_splitter.handleWidth()
        available_h = total_h - handle_w

        if not cfg.collapsed:
            self.status_panel.setMinimumHeight(140)
            self.status_panel.setMaximumHeight(16777215)
            editor_h, status_h = self._calc_splitter_sizes(available_h, cfg.expanded_height)
            self.right_splitter.setSizes([editor_h, status_h])
        else:
            header_h = self.status_panel.header_height()
            self.status_panel.setMinimumHeight(0)
            self.status_panel.setMaximumHeight(header_h)
            editor_h = max(200, available_h - header_h)
            self.right_splitter.setSizes([editor_h, header_h])

