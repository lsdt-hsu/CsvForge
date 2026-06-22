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

    # ── 面板組態還原 ──────────────────────────────────────────────────────────

    def _restore_all_panel_configs(self: "MainWindow") -> None:
        """
        依序從 AppContext 取得各 Config 物件，還原各面板的 UI 初始狀態。
        在 SettingsManager.load() 完成後、視窗顯示前由 __init__ 呼叫。
        """
        try:
            self._restore_io_panel()
            self._restore_side_panel()
            self._restore_status_panel()
            self.edit_content_panel.restore_from_config()
            self.update_start_button_ui()
        except Exception:
            pass  # 設定還原失敗時靜默略過，避免影響程式啟動

    def _restore_io_panel(self: "MainWindow") -> None:
        """從 IoPanelConfig 還原輸入與輸出面板的控件初始值。"""
        cfg = self.context.io_panel_config

        self.txt_src_path.setText(cfg.source_path)
        self.txt_out_path.setText(cfg.output_path)

        # 安全檢查：來源與輸出路徑不可相同
        src_path = self.txt_src_path.text().strip()
        out_path = self.txt_out_path.text().strip()
        if src_path and out_path and src_path == out_path:
            QMessageBox.warning(
                self,
                "路徑重複",
                "偵測到儲存的來源 CSV 與輸出 CSV 路徑相同！已自動清空輸出路徑以防檔案毀損。",
            )
            self.txt_out_path.clear()

        self.txt_start_row.setText(cfg.start_row)
        self.txt_end_row.setText(cfg.end_row)
        self.txt_src_col.setText(cfg.src_col)
        self.txt_tgt_col.setText(cfg.tgt_col)

        # 折疊狀態
        if cfg.collapsed:
            self.files_content_widget.setVisible(False)
            self.btn_toggle_files.setText("▼")
        else:
            self.files_content_widget.setVisible(True)
            self.btn_toggle_files.setText("▲")

    def _restore_side_panel(self: "MainWindow") -> None:
        """從 SidePanelConfig 還原側邊欄折疊狀態；從 MainConfig 還原功能分頁。"""
        side_cfg = self.context.side_panel_config
        main_cfg = self.context.main_config

        if side_cfg.collapsed:
            self.sidebar.setVisible(False)
            self.v_line.setVisible(False)
            self.left_container.setFixedWidth(SIDEBAR_MIN_WIDTH)
            self.btn_translate.setProperty("active", False)
            self.btn_edit.setProperty("active", False)
        else:
            self.switch_sidebar_tab(main_cfg.active_tab, force_expand=True)

    def _restore_status_panel(self: "MainWindow") -> None:
        """從 StatusPanelConfig 還原日誌面板的展開/收合狀態。"""
        cfg = self.context.status_panel_config

        if cfg.collapsed:
            self.txt_log.setVisible(False)
            self.btn_toggle_status.setText("▼")
            self.grp_status.setMinimumHeight(0)
            self.grp_status.setMaximumHeight(50)
        else:
            self.txt_log.setVisible(True)
            self.btn_toggle_status.setText("▲")
            self.grp_status.setMinimumHeight(140)
            self.grp_status.setMaximumHeight(16777215)

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
        self._update_main_config()
        self._update_side_panel_config()
        self._update_io_panel_config()
        self._update_status_panel_config()
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

    def _update_main_config(self: "MainWindow") -> None:
        if self.sidebar_stacked.currentWidget() == self.translation_panel:
            active_tab = "translate"
        else:
            active_tab = "edit"
        cfg = self.context.main_config
        cfg.active_tab = active_tab
        cfg.dirty = True

    def _update_side_panel_config(self: "MainWindow") -> None:
        cfg = self.context.side_panel_config
        cfg.collapsed = not self.sidebar.isVisible()
        cfg.dirty = True

    def _update_io_panel_config(self: "MainWindow") -> None:
        cfg = self.context.io_panel_config
        cfg.source_path = self.txt_src_path.text().strip()
        cfg.output_path = self.txt_out_path.text().strip()
        cfg.start_row = self.txt_start_row.text()
        cfg.end_row = self.txt_end_row.text()
        cfg.src_col = self.txt_src_col.text()
        cfg.tgt_col = self.txt_tgt_col.text()
        cfg.collapsed = not self.files_content_widget.isVisible()
        cfg.dirty = True

    def _update_status_panel_config(self: "MainWindow") -> None:
        cfg = self.context.status_panel_config
        # 若目前展開，先更新最新展開高度
        if not cfg.collapsed:
            sizes = self.right_splitter.sizes()
            if len(sizes) > 1 and sizes[1] > 0:
                cfg.expanded_height = sizes[1]
        cfg.dirty = True

    # ── 面板展開/收合 ─────────────────────────────────────────────────────────

    def toggle_files_panel(self: "MainWindow") -> None:
        collapsed = self.files_content_widget.isVisible()
        self.files_content_widget.setVisible(not collapsed)
        self.btn_toggle_files.setText("▼" if collapsed else "▲")
        # 即時更新 Config dirty flag（切換本身不觸發存檔）
        self.context.io_panel_config.collapsed = collapsed
        self.context.io_panel_config.dirty = True

    def toggle_status_panel(self: "MainWindow") -> None:
        cfg = self.context.status_panel_config
        cfg.collapsed = not cfg.collapsed
        cfg.dirty = True

        self.txt_log.setVisible(not cfg.collapsed)
        self.btn_toggle_status.setText("▲" if not cfg.collapsed else "▼")

        if not cfg.collapsed:
            self.grp_status.setMinimumHeight(140)
            self.grp_status.setMaximumHeight(16777215)

            sizes = self.right_splitter.sizes()
            if len(sizes) > 1:
                total_h = sum(sizes)
                status_h = max(140, cfg.expanded_height)
                editor_h = max(200, total_h - status_h)
                if editor_h < 200:
                    editor_h = 200
                    status_h = max(140, total_h - 200)
                self.right_splitter.setSizes([editor_h, status_h])
        else:
            sizes = self.right_splitter.sizes()
            if len(sizes) > 1 and sizes[1] > 100:
                cfg.expanded_height = sizes[1]

            header_h = self.status_header_widget.sizeHint().height() + 30
            if header_h < 50:
                header_h = 50

            self.grp_status.setMinimumHeight(0)
            self.grp_status.setMaximumHeight(header_h)

            sizes = self.right_splitter.sizes()
            if len(sizes) > 1:
                total_h = sum(sizes)
                self.right_splitter.setSizes([total_h - header_h, header_h])

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

    def apply_splitter_sizes(self: "MainWindow") -> None:
        cfg = self.context.status_panel_config
        total_h = self.right_splitter.height()
        handle_w = self.right_splitter.handleWidth()
        available_h = total_h - handle_w

        if not cfg.collapsed:
            self.grp_status.setMinimumHeight(140)
            self.grp_status.setMaximumHeight(16777215)
            status_h = max(140, cfg.expanded_height)
            editor_h = max(200, available_h - status_h)
            if editor_h < 200:
                editor_h = 200
                status_h = max(140, available_h - 200)
            self.right_splitter.setSizes([editor_h, status_h])
        else:
            header_h = self.status_header_widget.sizeHint().height() + 30
            if header_h < 50:
                header_h = 50
            self.grp_status.setMinimumHeight(0)
            self.grp_status.setMaximumHeight(header_h)
            editor_h = max(200, available_h - header_h)
            self.right_splitter.setSizes([editor_h, header_h])
