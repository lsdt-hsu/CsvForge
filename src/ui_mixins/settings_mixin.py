"""
SettingsMixin — 設定持久化與 Splitter 尺寸管理

職責：讀寫 settings.json；管理面板展開/收合；
      在視窗首次顯示後套用 Splitter 尺寸。

Qt 事件覆寫注意事項：
  showEvent() 必須呼叫 super().showEvent(event)，以確保 MRO
  鏈最終傳遞到 QMainWindow，不中斷 Qt 原生視窗初始化流程。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox

from ui_constants import (
    WINDOW_DEFAULT_WIDTH,
    WINDOW_DEFAULT_HEIGHT,
    SIDEBAR_MIN_WIDTH,
)

if TYPE_CHECKING:
    from ui import MainWindow


class SettingsMixin:

    # ── 設定儲存 ──────────────────────────────────────────────────────────────

    def get_current_settings_dict(self: "MainWindow") -> dict:
        is_max = self.isMaximized()
        geom = self.normalGeometry() if is_max else self.geometry()

        if self.sidebar_stacked.currentWidget() == self.translation_panel:
            active_tab = "translate"
        else:
            active_tab = "edit"

        # 在儲存前更新最新狀態面板的展開高度
        if self.status_expanded:
            sizes = self.right_splitter.sizes()
            if len(sizes) > 1:
                self.status_expanded_height = sizes[1]

        # 關鍵防重置邏輯：
        # 如果編輯過濾面板尚未初始化完成（未載入 CSV 時，控制項隱藏），
        # 則 filter_panel 設定應保留先前自 settings.json 載入的值，防止因 UI 為空而覆蓋。
        if hasattr(self, "edit_panel") and self.edit_panel.controls_container.isVisible():
            filter_panel_cfg = self.edit_panel.get_config()
        else:
            filter_panel_cfg = getattr(self, "loaded_settings", {}).get("filter_panel", {})

        return {
            "window": {
                "x": geom.x(),
                "y": geom.y(),
                "width": geom.width(),
                "height": geom.height(),
                "is_maximized": is_max,
            },
            "main": {
                "source_path": self.txt_src_path.text().strip(),
                "output_path": self.txt_out_path.text().strip(),
                "start_row": self.txt_start_row.text(),
                "end_row": self.txt_end_row.text(),
                "src_col": self.txt_src_col.text(),
                "tgt_col": self.txt_tgt_col.text(),
                "active_tab": active_tab,
            },
            "side_panel": {
                "collapsed": not self.sidebar.isVisible(),
            },
            "translate_panel": self.translation_panel.get_config(),
            "filter_panel": filter_panel_cfg,
            "status_panel": {
                "expanded_height": self.status_expanded_height,
                "collapsed": not self.status_expanded,
            },
            "files_panel": {
                "collapsed": not self.files_content_widget.isVisible(),
                "first_row_header": self.edit_content_panel.is_first_row_header(),
            },
        }

    def save_settings(self: "MainWindow") -> None:
        """
        儲存設定的主要入口。
        
        【儲存時機】
        僅在以下特定時期呼叫：
        1. 載入檔案完成 (worker_mixin.py - on_worker_success)
        2. 執行功能面板的大型任務（會鎖定UI的任務，如翻譯、過濾） (translation_panel.py - start_translation_task / edit_panel.py - on_filter_clicked)
        3. 關閉程式 (ui.py - closeEvent)
        (已移除在 UI 佈局微調如折疊面板、切換 tab 時的即時儲存)

        【儲存條件】
        - 僅在當前 UI 設定狀態與 loaded_settings 有所變更時，才寫入 settings.json。
        - 若未載入 CSV 檔案，過濾規則（Rules）會沿用載入時的暫存值，防範因欄位未初始化而重置。
        """
        data = self.get_current_settings_dict()

        # 比對是否有變更，若無變更則不寫入檔案
        if getattr(self, "loaded_settings", {}) == data:
            return

        self.settings_manager.save(data)
        self.loaded_settings = data

    # ── 設定還原 ──────────────────────────────────────────────────────────────

    def restore_settings(self: "MainWindow") -> None:
        data = self.settings_manager.load()
        self.loaded_settings = data if data else {}
        if not data:
            return

        try:
            # 1. 恢復視窗幾何
            if "window" in data:
                w_data = data["window"]
                x = w_data.get("x", 100)
                y = w_data.get("y", 100)
                width = w_data.get("width", WINDOW_DEFAULT_WIDTH)
                height = w_data.get("height", WINDOW_DEFAULT_HEIGHT)
                self.setGeometry(x, y, width, height)
                if w_data.get("is_maximized", False):
                    self.showMaximized()

            # 2. 恢復主程式欄位
            if "main" in data:
                m_data = data["main"]
                self.txt_src_path.setText(m_data.get("source_path", ""))
                self.txt_out_path.setText(m_data.get("output_path", ""))

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

                self.txt_start_row.setText(m_data.get("start_row", "2"))
                self.txt_end_row.setText(m_data.get("end_row", ""))
                self.txt_src_col.setText(m_data.get("src_col", "1"))
                self.txt_tgt_col.setText(m_data.get("tgt_col", "2"))

                active_tab = m_data.get("active_tab", "translate")

            # 3. 恢復側邊欄收合狀態與功能分頁
            collapsed = False
            if "side_panel" in data:
                side_cfg = data["side_panel"]
                collapsed = side_cfg.get("collapsed", False)

            if collapsed:
                self.sidebar.setVisible(False)
                self.v_line.setVisible(False)
                self.left_container.setFixedWidth(SIDEBAR_MIN_WIDTH)
                self.btn_translate.setProperty("active", False)
                self.btn_edit.setProperty("active", False)
            else:
                self.switch_sidebar_tab(active_tab)

            # 4. 恢復面板組態
            if "translate_panel" in data:
                self.translation_panel.set_config(data["translate_panel"])

            if "filter_panel" in data:
                self.edit_panel.set_config(data["filter_panel"])

            if "status_panel" in data:
                status_cfg = data["status_panel"]
                self.status_expanded_height = status_cfg.get("expanded_height", 250)
                status_collapsed = status_cfg.get("collapsed", False)
                self.status_expanded = not status_collapsed
                self.btn_toggle_status.setText("▲" if self.status_expanded else "▼")
                self.txt_log.setVisible(self.status_expanded)
                if not self.status_expanded:
                    self.grp_status.setMinimumHeight(0)
                    self.grp_status.setMaximumHeight(50)
                else:
                    self.grp_status.setMinimumHeight(140)
                    self.grp_status.setMaximumHeight(16777215)

            if "files_panel" in data:
                files_cfg = data["files_panel"]
                files_collapsed = files_cfg.get("collapsed", False)
                if files_collapsed:
                    self.files_content_widget.setVisible(False)
                    self.btn_toggle_files.setText("▼")
                else:
                    self.files_content_widget.setVisible(True)
                    self.btn_toggle_files.setText("▲")

                first_row_hdr = files_cfg.get("first_row_header", False)
                self.edit_content_panel.set_first_row_header(first_row_hdr)

            self.update_start_button_ui()

        except Exception:
            pass  # 設定恢復失敗時靜默略過，以避免影響程式啟動

    # ── 面板展開/收合 ─────────────────────────────────────────────────────────

    def toggle_files_panel(self: "MainWindow") -> None:
        collapsed = self.files_content_widget.isVisible()
        self.files_content_widget.setVisible(not collapsed)
        self.btn_toggle_files.setText("▼" if collapsed else "▲")

    def toggle_status_panel(self: "MainWindow") -> None:
        self.status_expanded = not self.status_expanded
        self.txt_log.setVisible(self.status_expanded)
        self.btn_toggle_status.setText("▲" if self.status_expanded else "▼")

        if self.status_expanded:
            self.grp_status.setMinimumHeight(140)
            self.grp_status.setMaximumHeight(16777215)

            sizes = self.right_splitter.sizes()
            if len(sizes) > 1:
                total_h = sum(sizes)
                status_h = max(140, self.status_expanded_height)
                editor_h = max(200, total_h - status_h)
                if editor_h < 200:
                    editor_h = 200
                    status_h = max(140, total_h - 200)
                self.right_splitter.setSizes([editor_h, status_h])
        else:
            sizes = self.right_splitter.sizes()
            if len(sizes) > 1 and sizes[1] > 100:
                self.status_expanded_height = sizes[1]

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
        if self.status_expanded:
            sizes = self.right_splitter.sizes()
            if len(sizes) > 1:
                self.status_expanded_height = sizes[1]

    def showEvent(self: "MainWindow", event) -> None:
        """Qt 事件覆寫：視窗首次顯示後套用 Splitter 初始尺寸。
        必須呼叫 super().showEvent(event) 維持 MRO 鏈完整性。
        """
        super().showEvent(event)  # ← MRO 鏈傳遞至 QMainWindow，勿省略
        if not self.settings_restored:
            self.settings_restored = True
            QTimer.singleShot(0, self.apply_splitter_sizes)

    def apply_splitter_sizes(self: "MainWindow") -> None:
        total_h = self.right_splitter.height()
        handle_w = self.right_splitter.handleWidth()
        available_h = total_h - handle_w

        if self.status_expanded:
            self.grp_status.setMinimumHeight(140)
            self.grp_status.setMaximumHeight(16777215)
            status_h = max(140, self.status_expanded_height)
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
