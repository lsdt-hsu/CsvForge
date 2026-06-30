"""
filter_panel.py — 過濾面板
"""

import os
import re
from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QWidget, QHBoxLayout, QMessageBox, QRadioButton, QTextEdit,
    QScrollArea, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QPainter, QPen, QColor, QTransform, QPixmap, QIcon, QIntValidator
from dataclasses import dataclass, field
from plugin_sdk.panel_base import BasePluginPanel
from plugin_sdk.theme import applyStandardLabelStyle, applyStandardLineEditStyle, applyPrimaryButtonStyle

from filter import logic_tree
from filter.rule_widget import RuleWidget, CircularToggleButton

class CustomTextEdit(QTextEdit):
    focus_out_signal = pyqtSignal()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.focus_out_signal.emit()


@dataclass
class FilterPanelConfig:
    dirty: bool = False
    rules: list = field(default_factory=list)
    logic_tree: dict = field(default_factory=dict)
    expr_text: str = "#1"
    start_row: str = "1"
    end_row: str = ""

class FilterPanel(BasePluginPanel):
    request_filter = pyqtSignal(dict)

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
        else:
            self.reset_panel()

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

        self.btn_start_filter = QPushButton("開始過濾")
        applyPrimaryButtonStyle(self.btn_start_filter, is_running=False)
        self.btn_start_filter.clicked.connect(self.on_filter_clicked)
        self.controls_layout.addWidget(self.btn_start_filter)

        self.lbl_expr_title = QLabel("當前規則邏輯 (可編輯)：")
        applyStandardLabelStyle(self.lbl_expr_title)
        self.lbl_expr_title.setStyleSheet(self.lbl_expr_title.styleSheet() + " font-weight: bold; margin-top: 5px;")
        self.controls_layout.addWidget(self.lbl_expr_title)

        self.txt_expression = CustomTextEdit()
        applyStandardLineEditStyle(self.txt_expression)
        self.txt_expression.setPlaceholderText("例如: #1 AND (#2 OR #3)")
        self.txt_expression.setFixedHeight(45)
        self.txt_expression.setAcceptRichText(False)
        self.txt_expression.focus_out_signal.connect(self.on_expression_focus_out)
        self.controls_layout.addWidget(self.txt_expression)

        self.reset_panel()

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

    def reset_panel(self):
        super().reset_panel()
        self.num_cols = 0

        self.clear_layout(self.rule_list_layout)
        self.rules.clear()

        self.logic_tree = logic_tree.LogicNode("LEAF", leaf_idx=1)
        self.expression_is_valid = True
        self.txt_expression.setStyleSheet("")

        w = RuleWidget(1, self)
        self.rules.append(w)
        self.rule_list_layout.addWidget(w)

        self.btn_add_rule.setVisible(True)
        self.txt_expression.setPlainText("#1")

        if hasattr(self, "txt_filter_start_row") and hasattr(self, "txt_filter_end_row"):
            self.txt_filter_start_row.blockSignals(True)
            self.txt_filter_end_row.blockSignals(True)
            self.txt_filter_start_row.setText("1")
            self.txt_filter_end_row.clear()
            self.txt_filter_start_row.blockSignals(False)
            self.txt_filter_end_row.blockSignals(False)

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
        if len(self.rules) >= 5:
            return

        new_idx = len(self.rules) + 1
        
        self.logic_tree = logic_tree.add_rule_node(self.logic_tree, new_idx)
        
        w = RuleWidget(new_idx, self)
        self.rules.append(w)
        
        self.rule_list_layout.addWidget(w)

        if len(self.rules) >= 5:
            self.btn_add_rule.setVisible(False)

        new_expr = logic_tree.to_string(self.logic_tree)
        self.txt_expression.blockSignals(True)
        self.txt_expression.setPlainText(new_expr)
        self.txt_expression.setStyleSheet("")
        self.txt_expression.blockSignals(False)
        self.expression_is_valid = True
        self._sync_rules_to_config()

    def delete_rule(self, del_idx):
        if not self.check_expression_validity():
            return
        if len(self.rules) <= 1:
            return

        self.logic_tree = logic_tree.remove_rule_node(self.logic_tree, del_idx)

        w_to_del = self.rules[del_idx - 1]
        self.rule_list_layout.removeWidget(w_to_del)
        w_to_del.deleteLater()
        self.rules.pop(del_idx - 1)

        for i, w in enumerate(self.rules):
            w.index = i + 1
            w.lbl_rule_title.setText(f"規則 #{w.index}")
            w.btn_delete.setVisible(w.index > 1)

        if len(self.rules) < 5:
            self.btn_add_rule.setVisible(True)

        new_expr = logic_tree.to_string(self.logic_tree)
        self.txt_expression.blockSignals(True)
        self.txt_expression.setPlainText(new_expr)
        self.txt_expression.setStyleSheet("")
        self.txt_expression.blockSignals(False)
        self.expression_is_valid = True
        self._sync_rules_to_config()

    def on_expression_focus_out(self):
        expr = self.txt_expression.toPlainText().strip()
        
        if not expr:
            expr = " AND ".join(f"#{i}" for i in range(1, len(self.rules) + 1))
            self.txt_expression.setPlainText(expr)

        try:
            tree = logic_tree.parse_expression(expr, len(self.rules))
            self.logic_tree = tree
            
            formatted_expr = logic_tree.to_string(tree)
            self.txt_expression.blockSignals(True)
            self.txt_expression.setPlainText(formatted_expr)
            applyStandardLineEditStyle(self.txt_expression)
            self.txt_expression.blockSignals(False)

            self.expression_is_valid = True
            self._sync_rules_to_config()
        except ValueError as e:
            self.txt_expression.setStyleSheet("border: 2px solid #f7768e; border-radius: 6px;")
            self.expression_is_valid = False

    def update_column_dropdowns(self, num_cols):
        self.num_cols = num_cols

        for r in self.rules:
            r.update_columns(num_cols)

    def on_filter_clicked(self):
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

            # 正規化以供後續驗證與比較
            if col == -1:
                col = "none"
            elif col == -2:
                col = "all"
            elif col == -3:
                col = "range"
                
            if target == -1:
                target = "manual"

            # 檢查比對欄位是否無法對應
            if isinstance(col, int) and (col >= self.num_cols or col < 0):
                QMessageBox.warning(self, "錯誤", f"規則 #{r.index}：比對欄位「欄位{col+1}」在當前 CSV 中不存在。")
                return

            if col == "range":
                range_start = cfg.get("range_start")
                range_end = cfg.get("range_end")
                start_val = range_start if range_start is not None else 0
                end_val = range_end if range_end is not None else (self.num_cols - 1 if self.num_cols > 0 else 0)
                if start_val > end_val:
                    QMessageBox.warning(self, "錯誤", f"規則 #{r.index}：欄位範圍「從欄位」不可大於「到欄位」。")
                    return

            # 檢查比對目標欄位是否無法對應
            if method not in ("屬於", "不屬於") and isinstance(target, int) and (target >= self.num_cols or target < 0):
                QMessageBox.warning(self, "錯誤", f"規則 #{r.index}：比對目標「欄位{target+1}」在當前 CSV 中不存在。")
                return

            if col != "none":
                if method not in ("屬於", "不屬於"):
                    if target == "manual":
                        if method == "正規表達式":
                            try:
                                re.compile(val)
                            except re.error as e:
                                QMessageBox.warning(self, "錯誤", f"規則 #{r.index} 正規表達式語法錯誤: {e}")
                                return
                    else:
                        if col == target:
                            QMessageBox.warning(self, "錯誤", f"規則 #{r.index}：欄位比對不可選擇相同的欄位。")
                            return

        # 正規化 rules 設定以符合 FilterWorker 所需的舊版字串格式規格
        normalized_rules = []
        for r in self.rules:
            rc = r.get_config().copy()
            if rc["compare_col"] == -1:
                rc["compare_col"] = "none"
            elif rc["compare_col"] == -2:
                rc["compare_col"] = "all"
            elif rc["compare_col"] == -3:
                rc["compare_col"] = "range"
                
            if rc["compare_target"] == -1:
                rc["compare_target"] = "manual"
            normalized_rules.append(rc)

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
            parent=self.window()
        )
        
        worker_instance.task_name = "過濾中..."
        worker_instance.initial_progress_total = len(rows)
        
        self.worker = worker_instance
        
        # 連接進度信號（FilterWorker 僅提供此基本信號，未定義 status_updated / log_emitted）
        worker_instance.progress_updated.connect(self.update_progress)
        
        worker_instance.filter_completed.connect(self.on_filter_completed)
        worker_instance.filter_error.connect(self.on_filter_error)
        
        worker_instance.start()
        
        # 發送任務開始信號
        self.start_task(
            task_name="過濾中...",
            total=len(rows),
            initial_log="開始執行 CSV 資料過濾...",
            prevent_sleep=False
        )

    def on_filter_completed(self, matched_indices, elapsed_time: float) -> None:
        self.context.csv_data.set_filtered_indices(matched_indices)
        self.update_status("完成")
        self.write_log("SUCCESS", f"過濾完成！共匹配 {len(matched_indices) if matched_indices is not None else 0} 筆資料，耗時 {elapsed_time:.2f} 秒。")
        self.finish_task("finished")
        self.worker = None

    def on_filter_error(self, err_msg: str) -> None:
        self.worker = None
        if "使用者已取消" in err_msg or "取消" in err_msg:
            self.update_status("已取消")
            self.write_log("WARNING", "過濾工作已被使用者取消。")
            self.finish_task("cancelled")
        else:
            self.update_status("錯誤")
            self.write_log("ERROR", f"過濾錯誤：{err_msg}")
            QMessageBox.critical(self, "過濾錯誤", err_msg)
            self.finish_task("error")

    def is_task_running(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def cancel_task(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()

    def set_enabled(self, enabled):
        self.txt_filter_start_row.setEnabled(enabled)
        self.txt_filter_end_row.setEnabled(enabled)
        self.btn_add_rule.setEnabled(enabled)
        self.btn_start_filter.setEnabled(enabled)
        self.txt_expression.setEnabled(enabled)
        for r in self.rules:
            r.setEnabled(enabled)

    # ── Interface 實作 ────────────────────────────────────────────────────────
    def get_package_name(self) -> str:
        return "filter_panel"

    def get_uuid(self) -> str:
        return "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"

    def run_main_action(self) -> None:
        self.on_filter_clicked()

    def serialize_config(self) -> dict:
        cfg = self.config
        return {
            "rules": cfg.rules,
            "logic_tree": cfg.logic_tree,
            "expr_text": cfg.expr_text,
            "start_row": cfg.start_row,
            "end_row": cfg.end_row,
        }

    def deserialize_config(self, data: dict) -> None:
        cfg = self.config
        cfg.rules = data.get("rules", [])
        cfg.logic_tree = data.get("logic_tree", {})
        cfg.expr_text = data.get("expr_text", "#1")
        cfg.start_row = data.get("start_row", "1")
        cfg.end_row = data.get("end_row", "")
        self.restore_from_config()

    def _sync_rules_to_config(self) -> None:
        cfg = self.config
        cfg.rules = [r.get_config() for r in self.rules]
        cfg.logic_tree = logic_tree.serialize_tree(self.logic_tree)
        cfg.expr_text = self.txt_expression.toPlainText()
        cfg.start_row = self.txt_filter_start_row.text().strip()
        cfg.end_row = self.txt_filter_end_row.text().strip()
        cfg.dirty = True

    def _apply_config_to_ui(self, config: dict) -> None:
        if not config:
            return

        self.txt_expression.blockSignals(True)
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

        if not self.rules:
            w = RuleWidget(1, self)
            self.rules.append(w)
            self.rule_list_layout.addWidget(w)

        lt_cfg = config.get("logic_tree")
        self.logic_tree = logic_tree.deserialize_tree(lt_cfg)

        expr_text = config.get("expr_text", "")
        self.txt_expression.setPlainText(expr_text)
        self.txt_expression.blockSignals(False)

        self.on_expression_focus_out()

        self.btn_add_rule.setVisible(len(self.rules) < 5)

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


