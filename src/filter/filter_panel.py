"""
filter_panel.py — 過濾面板
"""

import os
import re
from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QWidget, QHBoxLayout, QMessageBox, QRadioButton, QTextEdit,
    QScrollArea, QFrame, QDialog
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QPainter, QPen, QColor, QTransform, QPixmap, QIcon, QIntValidator
from common_data.task_status import TaskStatus
from plugin_sdk.panel_base import BasePluginPanel
from plugin_sdk.theme import applyStandardLabelStyle, applyStandardLineEditStyle, applyPrimaryButtonStyle, applyStandardButtonStyle

from filter.logic_tree import logic_tree
from filter.logic_tree_editor.logic_tree_editor_dialog import LogicTreeEditorDialog
from filter.rule_widget import RuleWidget, CircularToggleButton
from filter.filter_config import FilterPanelConfig, serialize_filter_config, deserialize_filter_config, CompareMethod



class FilterPanel(BasePluginPanel):
    request_filter = pyqtSignal(dict)
    MAX_RULES: int = 10

    def __init__(self, parent=None, context=None):
        super().__init__(parent, title_text="過濾", require_data_loading=True, context=context)
        self.config = FilterPanelConfig()
        self.num_cols = 0
        self.worker = None

        self.rules = []
        self.logic_tree = None
        self.expression_is_valid = True

        self.init_ui()

    def on_csv_data_refreshed(self):
        if self.context and self.context.is_data_loaded:
            if not self.controls_container.isVisible():
                self.show_controls()
            self.update_column_dropdowns(self.context.csv_data.num_cols)
            self.on_filter_clicked()
        else:
            self.hide_controls()

    def init_ui(self):
        # 行號範圍輸入
        range_widget = QWidget()
        range_layout = QHBoxLayout(range_widget)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(10)

        lbl_start = QLabel("行號：")
        applyStandardLabelStyle(lbl_start)
        self.txt_filter_start_row = QLineEdit("1")
        applyStandardLineEditStyle(self.txt_filter_start_row)
        self.txt_filter_start_row.setPlaceholderText("1")
        self.txt_filter_start_row.setValidator(QIntValidator(1, 9999999))
        self.txt_filter_start_row.setFixedWidth(80)
        self.txt_filter_start_row.textChanged.connect(self._on_row_range_changed)

        lbl_end = QLabel("~")
        applyStandardLabelStyle(lbl_end)
        lbl_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_filter_end_row = QLineEdit()
        applyStandardLineEditStyle(self.txt_filter_end_row)
        self.txt_filter_end_row.setPlaceholderText("檔尾")
        self.txt_filter_end_row.setValidator(QIntValidator(1, 9999999))
        self.txt_filter_end_row.setFixedWidth(80)
        self.txt_filter_end_row.textChanged.connect(self._on_row_range_changed)

        range_layout.addWidget(lbl_start)
        range_layout.addWidget(self.txt_filter_start_row)
        range_layout.addWidget(lbl_end)
        range_layout.addWidget(self.txt_filter_end_row)
        range_layout.addStretch()

        self.controls_layout.addWidget(range_widget)

        # 分割線
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("color: #3b4261; margin-bottom: 5px;")
        self.controls_layout.addWidget(sep)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(self.scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(12)

        self.rule_list_widget = QWidget()
        self.rule_list_layout = QVBoxLayout(self.rule_list_widget)
        self.rule_list_layout.setContentsMargins(0, 0, 0, 0)
        self.rule_list_layout.setSpacing(12)
        scroll_layout.addWidget(self.rule_list_widget)

        self.add_btn_container = QWidget()
        add_btn_layout = QHBoxLayout(self.add_btn_container)
        add_btn_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_add_rule = CircularToggleButton()
        self.btn_add_rule.set_minus(False)  # ⊕
        self.btn_add_rule.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_rule.setStyleSheet("border: none; background: transparent;")
        self.btn_add_rule.clicked.connect(self.add_rule)
        
        add_btn_layout.addWidget(self.btn_add_rule)
        add_btn_layout.addStretch()
        scroll_layout.addWidget(self.add_btn_container)

        scroll_layout.addStretch(1)

        self.scroll_area.setWidget(self.scroll_content)
        self.controls_layout.addWidget(self.scroll_area, stretch=1)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)

        self.btn_ui_edit = QPushButton("邏輯")
        applyStandardButtonStyle(self.btn_ui_edit)
        self.btn_ui_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ui_edit.clicked.connect(self.open_logic_tree_editor)

        self.btn_start_filter = QPushButton("開始過濾")
        applyPrimaryButtonStyle(self.btn_start_filter, is_running=False)
        self.btn_start_filter.clicked.connect(self.on_filter_clicked)

        btn_layout.addWidget(self.btn_ui_edit, 1)
        btn_layout.addWidget(self.btn_start_filter, 2)
        self.controls_layout.addLayout(btn_layout)

        self.hide_controls()

    def _on_row_range_changed(self):
        cfg = self.config
        cfg.start_row = self.txt_filter_start_row.text().strip()
        cfg.end_row = self.txt_filter_end_row.text().strip()
        cfg.dirty = True

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def hide_controls(self):
        super().hide_controls()
        self.num_cols = 0

    def check_expression_validity(self):
        if not self.expression_is_valid:
            QMessageBox.warning(self, "錯誤", "當前規則邏輯表達式不合法，請先修正紅框內的表達式。")
            return False
        return True

    def on_rule_content_changed(self):
        self._sync_rules_to_config()

    def add_rule(self):
        if not self.check_expression_validity():
            return
        if len(self.rules) >= self.MAX_RULES:
            return

        new_idx = len(self.rules) + 1
        
        self.logic_tree = logic_tree.add_rule_node(self.logic_tree, new_idx)
        
        w = RuleWidget(new_idx, self)
        self.rules.append(w)
        
        self.rule_list_layout.addWidget(w)

        if len(self.rules) >= self.MAX_RULES:
            self.btn_add_rule.setVisible(False)

        self.expression_is_valid = True
        self._sync_rules_to_config()

    def delete_rule(self, del_idx):
        if not self.check_expression_validity():
            return
        if len(self.rules) == 0:
            return

        self.logic_tree = logic_tree.remove_rule_node(self.logic_tree, del_idx)

        w_to_del = self.rules[del_idx - 1]
        self.rule_list_layout.removeWidget(w_to_del)
        w_to_del.deleteLater()
        self.rules.pop(del_idx - 1)

        for i, w in enumerate(self.rules):
            w.index = i + 1
            w.lbl_rule_title.setText(f"規則 #{w.index}")
            w.btn_delete.setVisible(True)

        if len(self.rules) < self.MAX_RULES:
            self.btn_add_rule.setVisible(True)

        self.expression_is_valid = True
        self._sync_rules_to_config()

    def open_logic_tree_editor(self):
        """開啟邏輯樹編輯器 Modal 對話框。"""
        current_expr = logic_tree.to_string(self.logic_tree) if self.logic_tree else ""
        dialog = LogicTreeEditorDialog(expression_text=current_expr, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_expr = dialog.get_expression_text()
            try:
                self.logic_tree = logic_tree.parse_expression(new_expr, len(self.rules))
                self.expression_is_valid = True
                self._sync_rules_to_config()
            except ValueError:
                pass

    def update_column_dropdowns(self, num_cols):
        self.num_cols = num_cols

        for r in self.rules:
            r.update_columns(num_cols)

    def on_filter_clicked(self):
        # 防止 Worker 累積：清理上一個尚未結束的 Worker
        if self.worker is not None:
            self.worker.cancel()
            self.worker.all_rows = None
            self.worker.filter_config = None
            self.worker = None

        if not self.check_expression_validity():
            return

        rows = self.context.csv_data.all_rows
        if not rows:
            QMessageBox.warning(self, "錯誤", "請先載入 CSV 資料。")
            return

        for r in self.rules:
            cfg = r.get_config()
            col = cfg["compare_col"]
            method = cfg["compare_method"]
            target = cfg["compare_target"]
            val = cfg["compare_value"]

            # 檢查比對欄位是否無法對應
            if col >= 0 and col >= self.num_cols:
                QMessageBox.warning(self, "錯誤", f"規則 #{r.index}：比對欄位「欄位{col+1}」在當前 CSV 中不存在。")
                return

            if col == -2:  # 欄位範圍
                range_start = cfg.get("range_start")
                range_end = cfg.get("range_end")
                start_val = range_start if range_start is not None else 0
                end_val = range_end if range_end is not None else (self.num_cols - 1 if self.num_cols > 0 else 0)
                if start_val > end_val:
                    QMessageBox.warning(self, "錯誤", f"規則 #{r.index}：欄位範圍「從欄位」不可大於「到欄位」。")
                    return

            # 檢查比對目標欄位是否無法對應
            if method != CompareMethod.BELONG and target >= 0 and target >= self.num_cols:
                QMessageBox.warning(self, "錯誤", f"規則 #{r.index}：比對目標「欄位{target+1}」在當前 CSV 中不存在。")
                return

            if method != CompareMethod.BELONG:
                if target == -1:  # 手動輸入
                    if method == CompareMethod.REGEX:
                        try:
                            re.compile(val)
                        except re.error as e:
                            QMessageBox.warning(self, "錯誤", f"規則 #{r.index} 正規表達式語法錯誤: {e}")
                            return
                else:
                    if col == target:
                        QMessageBox.warning(self, "錯誤", f"規則 #{r.index}：欄位比對不可選擇相同的欄位。")
                        return

        # 這裡直接複製 get_config 回傳的 dict 結構，不需要額外的相容性轉換
        normalized_rules = [r.get_config().copy() for r in self.rules]

        filter_config = {
            "rules": normalized_rules,
            "logic_tree": logic_tree.serialize_tree(self.logic_tree)
        }

        # 驗證行號輸入
        start_row_str = self.txt_filter_start_row.text().strip()
        if start_row_str == "":
            start_row_val = 1
        else:
            try:
                start_row_val = int(start_row_str)
                if start_row_val < 1:
                    QMessageBox.warning(self, "輸入錯誤", "起始行號必須是大於或等於 1 的正整數")
                    return
            except ValueError:
                QMessageBox.warning(self, "輸入錯誤", "起始行號必須是大於或等於 1 的正整數")
                return

        end_row_str = self.txt_filter_end_row.text().strip()
        if end_row_str != "":
            try:
                end_row_val = int(end_row_str)
                if end_row_val < start_row_val:
                    QMessageBox.warning(self, "輸入錯誤", "結束行號不能小於起始行號")
                    return
            except ValueError:
                QMessageBox.warning(self, "輸入錯誤", "結束行號必須是正整數")
                return
        else:
            end_row_val = None

        is_header = self.context.is_first_row_header

        from filter.filter_worker import FilterWorker
        worker_instance = FilterWorker(
            all_rows=rows,
            start_row=start_row_val,
            end_row=end_row_val,
            is_header=is_header,
            filter_config=filter_config,
        )

        self.worker = worker_instance

        # 連接業務信號（面板自身處理的部分）
        worker_instance.filter_completed.connect(self.on_filter_completed)
        worker_instance.log_emitted.connect(self.api.write_log)
        # 連接完成信號：面板負責更新狀態與錯誤處理
        worker_instance.finished.connect(self._on_filter_done)

        # 委託主程式管理 Thread 生命週期（含 ThrottledProgress、GC、finish_task）
        self.api.run_worker(
            worker_instance,
            task_name="過濾中...",
            total=len(rows),
            initial_log="開始執行 CSV 資料過濾...",
            prevent_sleep=False
        )

    def on_filter_completed(self, matched_indices, elapsed_time: float) -> None:
        """FilterWorker 順利完成過濾時的業務回調（圖式更新）。"""
        self.context.csv_data.set_filtered_indices(matched_indices)
        self.api.update_status("完成")
        count = len(matched_indices) if matched_indices is not None else 0
        self.api.write_log("SUCCESS", f"過濾完成！共匹配 {count} 筆資料，耗時 {elapsed_time:.2f} 秒。")

    def _on_filter_done(self, status: TaskStatus) -> None:
        """標準完成回調。由 worker.finished 信號觸發，在 Adapter 自動呼叫 finish_task 前執行。"""
        if status == TaskStatus.ERROR and self.worker is not None:
            err_msg = getattr(self.worker, "_last_error", "未知錯誤")
            if err_msg:
                QMessageBox.critical(self, "過濾錯誤", err_msg)
        # 🔪 斷開 FilterPanel 自己連接的業務信號，防止信號表阻止 GC
        if self.worker is not None:
            try:
                self.worker.filter_completed.disconnect(self.on_filter_completed)
                self.worker.log_emitted.disconnect(self.api.write_log)
                self.worker.finished.disconnect(self._on_filter_done)
            except (TypeError, RuntimeError):
                pass
            # 主動清除 Worker 持有的大型資料引用
            self.worker.all_rows = None
            self.worker.filter_config = None
            self.worker = None

    def _internal_set_enabled(self, enabled: bool) -> None:
        """主程式 UI 鎖定/解鎖時同步更新內部元件狀態。"""
        self.txt_filter_start_row.setEnabled(enabled)
        self.txt_filter_end_row.setEnabled(enabled)
        self.btn_add_rule.setEnabled(enabled)
        self.btn_start_filter.setEnabled(enabled)
        self.btn_ui_edit.setEnabled(enabled)
        for r in self.rules:
            r.setEnabled(enabled)

    # ── Interface 實作 ────────────────────────────────────────────────────────
    def _internal_get_package_name(self) -> str:
        return "filter_panel"

    def _internal_get_uuid(self) -> str:
        return "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"

    def _internal_serialize_config(self) -> dict:
        return serialize_filter_config(self.config)

    def _internal_deserialize_config(self, data: dict) -> None:
        self.config = deserialize_filter_config(data)
        self.restore_from_config()

    def _sync_rules_to_config(self) -> None:
        cfg = self.config
        cfg.rules = [r.get_config() for r in self.rules]
        cfg.logic_tree = logic_tree.serialize_tree(self.logic_tree)
        cfg.expr_text = logic_tree.to_string(self.logic_tree) if self.logic_tree else ""
        cfg.start_row = self.txt_filter_start_row.text().strip()
        cfg.end_row = self.txt_filter_end_row.text().strip()
        cfg.dirty = True

    def _apply_config_to_ui(self, config: dict) -> None:
        if not config:
            return

        self.txt_filter_start_row.blockSignals(True)
        self.txt_filter_end_row.blockSignals(True)

        self.txt_filter_start_row.setText(config.get("start_row", "1"))
        self.txt_filter_end_row.setText(config.get("end_row", ""))

        self.txt_filter_start_row.blockSignals(False)
        self.txt_filter_end_row.blockSignals(False)

        self.clear_layout(self.rule_list_layout)
        self.rules.clear()

        rules_cfg = config.get("rules", [])
        for i, r_cfg in enumerate(rules_cfg):
            w = RuleWidget(i + 1, self)
            self.rules.append(w)
            self.rule_list_layout.addWidget(w)
            w.set_config(r_cfg)

        lt_cfg = config.get("logic_tree")
        if lt_cfg:
            self.logic_tree = logic_tree.deserialize_tree(lt_cfg)
        elif config.get("expr_text"):
            try:
                self.logic_tree = logic_tree.parse_expression(config.get("expr_text"), len(self.rules))
            except ValueError:
                self.logic_tree = None
        else:
            self.logic_tree = None

        self.btn_add_rule.setVisible(len(self.rules) < self.MAX_RULES)

    def restore_from_config(self) -> None:
        cfg = self.config
        config_dict = {
            "rules": cfg.rules,
            "logic_tree": cfg.logic_tree,
            "expr_text": cfg.expr_text,
            "start_row": cfg.start_row,
            "end_row": cfg.end_row,
        }
        self._apply_config_to_ui(config_dict)


