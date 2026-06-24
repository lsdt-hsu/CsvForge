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
from base_panel import BasePanel

from filter import logic_tree

class CircularToggleButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_minus = False # False = Plus (⊕), True = Minus (⊖)
        self.setFixedSize(30, 30)

    def set_minus(self, is_minus):
        if self.is_minus != is_minus:
            self.is_minus = is_minus
            self.update()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        is_hover = self.underMouse()
        is_pressed = self.isDown()
        
        if is_hover or is_pressed:
            fg_color = QColor("#89ddff")
        else:
            fg_color = QColor("#7aa2f7")
            
        rect = self.rect()
        center_x = rect.width() / 2.0
        center_y = rect.height() / 2.0
        
        line_len = 10.0
        pen_width = 2.5
        
        painter.setPen(QPen(fg_color, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        
        # Horizontal line
        painter.drawLine(
            int(center_x - line_len / 2.0), int(center_y),
            int(center_x + line_len / 2.0), int(center_y)
        )
        
        # Vertical line
        if not self.is_minus:
            painter.drawLine(
                int(center_x), int(center_y - line_len / 2.0),
                int(center_x), int(center_y + line_len / 2.0)
            )

class CustomTextEdit(QTextEdit):
    focus_out_signal = pyqtSignal()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.focus_out_signal.emit()

class RuleWidget(QWidget):
    def __init__(self, index, parent_panel):
        super().__init__()
        self.index = index  # 1-indexed integer
        self.parent_panel = parent_panel
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_rule_title = QLabel(f"規則 #{self.index}")
        self.lbl_rule_title.setStyleSheet("font-weight: bold; color: #a9b1d6;")
        title_layout.addWidget(self.lbl_rule_title)
        
        title_layout.addStretch()
        
        self.btn_delete = CircularToggleButton()
        self.btn_delete.set_minus(True)  # ⊖
        self.btn_delete.setFixedSize(20, 20)
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setStyleSheet("border: none; background: transparent;")
        self.btn_delete.clicked.connect(self.on_delete_clicked)
        self.btn_delete.setVisible(self.index > 1)
        title_layout.addWidget(self.btn_delete)
        
        layout.addLayout(title_layout)

        # 1. 比對欄位列
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(10)
        lbl_col = QLabel("比對欄位：")
        lbl_col.setFixedWidth(75)
        self.cmb_compare_col = QComboBox()
        self.cmb_compare_col.addItem("不過濾", "none")
        self.cmb_compare_col.addItem("所有欄位", "all")
        self.cmb_compare_col.addItem("來源-目標欄位", "range")
        self.cmb_compare_col.currentIndexChanged.connect(self.on_col_changed)
        row1.addWidget(lbl_col)
        row1.addWidget(self.cmb_compare_col)
        layout.addLayout(row1)

        # 2. 比對方式列
        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(10)
        lbl_method = QLabel("比對方式：")
        lbl_method.setFixedWidth(75)
        self.cmb_compare_method = QComboBox()
        self.cmb_compare_method.addItems(["完全符合", "包含", "未包含", "正規表達式", "屬於", "不屬於"])
        self.cmb_compare_method.currentIndexChanged.connect(self.on_method_changed)
        row2.addWidget(lbl_method)
        row2.addWidget(self.cmb_compare_method)
        layout.addLayout(row2)

        # 3. 比對目標列
        row3 = QHBoxLayout()
        row3.setContentsMargins(0, 0, 0, 0)
        row3.setSpacing(10)
        lbl_target = QLabel("比對目標：")
        lbl_target.setFixedWidth(75)
        self.cmb_compare_target = QComboBox()
        self.cmb_compare_target.addItem("手動輸入", "manual")
        self.cmb_compare_target.currentIndexChanged.connect(self.on_target_changed)
        row3.addWidget(lbl_target)
        row3.addWidget(self.cmb_compare_target)
        layout.addLayout(row3)

        # 4. 輸入框容器 (內縮 20 像素)
        self.value_container = QWidget()
        value_layout = QHBoxLayout(self.value_container)
        value_layout.setContentsMargins(20, 0, 0, 0)
        value_layout.setSpacing(0)
        self.txt_compare_value = QLineEdit()
        self.txt_compare_value.setPlaceholderText("輸入比對值或正規表達式")
        self.txt_compare_value.textChanged.connect(self.parent_panel.on_rule_content_changed)
        value_layout.addWidget(self.txt_compare_value)
        layout.addWidget(self.value_container)

        # 5. 屬於容器 (內縮 20 像素)
        self.belong_container = QWidget()
        belong_layout = QHBoxLayout(self.belong_container)
        belong_layout.setContentsMargins(20, 0, 0, 0)
        belong_layout.setSpacing(0)
        self.cmb_belong_value = QComboBox()
        self.cmb_belong_value.currentIndexChanged.connect(self.parent_panel.on_rule_content_changed)
        belong_layout.addWidget(self.cmb_belong_value)
        layout.addWidget(self.belong_container)
        
        self.belong_container.setVisible(False)

        if self.parent_panel.num_cols > 0:
            self.update_columns(self.parent_panel.num_cols, self.parent_panel.headers)

    def update_columns(self, num_cols, headers=None):
        self.cmb_compare_col.blockSignals(True)
        self.cmb_compare_target.blockSignals(True)
        
        old_col = self.cmb_compare_col.currentData()
        old_target = self.cmb_compare_target.currentData()

        self.cmb_compare_col.clear()
        self.cmb_compare_col.addItem("不過濾", "none")
        self.cmb_compare_col.addItem("所有欄位", "all")
        self.cmb_compare_col.addItem("來源-目標欄位", "range")
        for i in range(num_cols):
            text = f"{i+1}. {headers[i]}" if headers and i < len(headers) else f"第 {i+1} 欄"
            self.cmb_compare_col.addItem(text, i)

        idx = self.cmb_compare_col.findData(old_col)
        self.cmb_compare_col.setCurrentIndex(idx if idx >= 0 else 0)

        self.update_target_options(num_cols, headers)

        self.cmb_compare_col.blockSignals(False)
        self.cmb_compare_target.blockSignals(False)
        self.update_belong_visibility()

    def update_target_options(self, num_cols, headers=None):
        self.cmb_compare_target.blockSignals(True)
        old_target = self.cmb_compare_target.currentData()
        self.cmb_compare_target.clear()
        method = self.cmb_compare_method.currentText()
        if method in ("屬於", "不屬於"):
            self.cmb_compare_target.addItem("語系", "語系")
            self.cmb_compare_target.addItem("含數字", "含數字")
            self.cmb_compare_target.addItem("純數字", "純數字")
            self.cmb_compare_target.addItem("文數字(無符號)", "文數字(無符號)")
            self.cmb_compare_target.addItem("僅符號", "僅符號")
        else:
            self.cmb_compare_target.addItem("手動輸入", "manual")
            for i in range(num_cols):
                text = f"{i+1}. {headers[i]}" if headers and i < len(headers) else f"第 {i+1} 欄"
                self.cmb_compare_target.addItem(text, i)
        
        idx = self.cmb_compare_target.findData(old_target)
        self.cmb_compare_target.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_compare_target.blockSignals(False)

    def update_belong_visibility(self):
        col_type = self.cmb_compare_col.currentData()
        if col_type is None or col_type == "none":
            self.cmb_compare_method.setEnabled(False)
            self.cmb_compare_target.setEnabled(False)
            self.value_container.setVisible(False)
            self.belong_container.setVisible(False)
            return
        
        self.cmb_compare_method.setEnabled(True)
        self.cmb_compare_target.setEnabled(True)

        method = self.cmb_compare_method.currentText()
        if method in ("屬於", "不屬於"):
            self.value_container.setVisible(False)
            self.belong_container.setVisible(True)
            
            target = self.cmb_compare_target.currentData()
            self.cmb_belong_value.blockSignals(True)
            old_belong = self.cmb_belong_value.currentText()
            self.cmb_belong_value.clear()
            if target == "語系":
                items = ["中文", "繁體中文", "簡體中文", "日文(通用)", "日文(專字)", "韓文", "英文", "拉丁語系", "其他語系"]
            elif target in ("含數字", "純數字"):
                items = ["半形", "全半形", "多國語言"]
            elif target in ("文數字(無符號)", "僅符號"):
                items = ["半形", "全半形"]
            else:
                items = []
            self.cmb_belong_value.addItems(items)
            
            idx = self.cmb_belong_value.findText(old_belong)
            if idx >= 0:
                self.cmb_belong_value.setCurrentIndex(idx)
            self.cmb_belong_value.blockSignals(False)
        else:
            self.belong_container.setVisible(False)
            target = self.cmb_compare_target.currentData()
            if target == "manual":
                self.value_container.setVisible(True)
            else:
                self.value_container.setVisible(False)

    def on_col_changed(self, idx):
        self.update_belong_visibility()
        self.parent_panel.on_rule_content_changed()

    def on_method_changed(self, idx):
        self.update_target_options(self.parent_panel.num_cols, self.parent_panel.headers)
        self.update_belong_visibility()
        self.parent_panel.on_rule_content_changed()

    def on_target_changed(self, idx):
        self.update_belong_visibility()
        self.parent_panel.on_rule_content_changed()

    def on_delete_clicked(self):
        self.parent_panel.delete_rule(self.index)

    def get_config(self):
        method = self.cmb_compare_method.currentText()
        if method in ("屬於", "不屬於"):
            val = self.cmb_belong_value.currentText()
        else:
            val = self.txt_compare_value.text()
        return {
            "compare_col": self.cmb_compare_col.currentData(),
            "compare_method": self.cmb_compare_method.currentText(),
            "compare_target": self.cmb_compare_target.currentData(),
            "compare_value": val,
            "belong_value_idx": self.cmb_belong_value.currentIndex()
        }

    def set_config(self, cfg):
        self.cmb_compare_col.blockSignals(True)
        self.cmb_compare_method.blockSignals(True)
        self.cmb_compare_target.blockSignals(True)
        self.cmb_belong_value.blockSignals(True)

        col = cfg.get("compare_col", "none")
        method = cfg.get("compare_method", "完全符合")
        target = cfg.get("compare_target", "manual")
        val = cfg.get("compare_value", "")
        b_idx = cfg.get("belong_value_idx", 0)

        idx = self.cmb_compare_col.findData(col)
        self.cmb_compare_col.setCurrentIndex(idx if idx >= 0 else 0)

        idx = self.cmb_compare_method.findText(method)
        self.cmb_compare_method.setCurrentIndex(idx if idx >= 0 else 0)

        self.update_target_options(self.parent_panel.num_cols, self.parent_panel.headers)

        idx = self.cmb_compare_target.findData(target)
        self.cmb_compare_target.setCurrentIndex(idx if idx >= 0 else 0)

        self.update_belong_visibility()

        if method in ("屬於", "不屬於"):
            self.cmb_belong_value.setCurrentIndex(b_idx)
        else:
            self.txt_compare_value.setText(val)

        self.cmb_compare_col.blockSignals(False)
        self.cmb_compare_method.blockSignals(False)
        self.cmb_compare_target.blockSignals(False)
        self.cmb_belong_value.blockSignals(False)

class FilterPanel(BasePanel):
    request_filter = pyqtSignal(dict)

    def __init__(self, parent=None, context=None):
        super().__init__(parent, title_text="過濾", require_data_loading=True, context=context)
        self.num_cols = 0
        self.headers = None

        self.rules = []
        self.logic_tree = None
        self.expression_is_valid = True

        self.init_ui()

    def init_ui(self):
        # 行號範圍輸入
        range_widget = QWidget()
        range_layout = QHBoxLayout(range_widget)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(10)

        lbl_start = QLabel("行號：")
        self.txt_filter_start_row = QLineEdit("1")
        self.txt_filter_start_row.setPlaceholderText("1")
        self.txt_filter_start_row.setValidator(QIntValidator(1, 9999999))
        self.txt_filter_start_row.setFixedWidth(80)
        self.txt_filter_start_row.textChanged.connect(self._on_row_range_changed)

        lbl_end = QLabel("~")
        lbl_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_filter_end_row = QLineEdit()
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
        self.btn_start_filter.clicked.connect(self.on_filter_clicked)
        self.controls_layout.addWidget(self.btn_start_filter)

        self.lbl_expr_title = QLabel("當前規則邏輯 (可編輯)：")
        self.lbl_expr_title.setStyleSheet("font-weight: bold; color: #565f89; margin-top: 5px;")
        self.controls_layout.addWidget(self.lbl_expr_title)

        self.txt_expression = CustomTextEdit()
        self.txt_expression.setPlaceholderText("例如: #1 AND (#2 OR #3)")
        self.txt_expression.setFixedHeight(45)
        self.txt_expression.setAcceptRichText(False)
        self.txt_expression.focus_out_signal.connect(self.on_expression_focus_out)
        self.controls_layout.addWidget(self.txt_expression)

        self.reset_panel()

    def _on_row_range_changed(self):
        if self.context:
            cfg = self.context.filter_panel_config
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
        self.headers = None

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
            self.txt_expression.setStyleSheet("")
            self.txt_expression.blockSignals(False)

            self.expression_is_valid = True
            self._sync_rules_to_config()
        except ValueError as e:
            self.txt_expression.setStyleSheet("border: 2px solid #f7768e; border-radius: 4px;")
            self.expression_is_valid = False

    def update_column_dropdowns(self, num_cols, headers=None):
        self.show_controls()

        self.num_cols = num_cols
        self.headers = headers

        for r in self.rules:
            r.update_columns(num_cols, headers)

    def on_filter_clicked(self):
        if not self.check_expression_validity():
            return

        for r in self.rules:
            cfg = r.get_config()
            col = cfg["compare_col"]
            method = cfg["compare_method"]
            target = cfg["compare_target"]
            val = cfg["compare_value"]

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

        filter_config = {
            "rules": [r.get_config() for r in self.rules],
            "logic_tree": logic_tree.serialize_tree(self.logic_tree)
        }

        rows = self.context.all_rows
        if not rows:
            QMessageBox.warning(self, "錯誤", "請先載入 CSV 資料。")
            return

        from io_panel import validate_io_panel_inputs

        is_valid, parsed = validate_io_panel_inputs(
            self,
            self.context,
            require_source_path=False,
            require_output_path=False,
            require_source_col=True,
            require_target_col=True,
        )
        if not is_valid:
            return

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

        src_col = parsed["source_col"]
        tgt_col = parsed["target_col"]

        is_header = self.context.is_first_row_header

        from filter.filter_worker import FilterWorker
        worker_instance = FilterWorker(
            all_rows=rows,
            start_row=start_row_val,
            end_row=end_row_val,
            is_header=is_header,
            src_col=src_col,
            tgt_col=tgt_col,
            filter_config=filter_config,
            parent=self.window()
        )
        
        worker_instance.task_name = "過濾中..."
        worker_instance.initial_progress_total = len(rows)
        
        self.update_status("過濾中...")
        self.write_log("INFO", "開始執行 CSV 資料過濾...")
        
        worker_instance.filter_completed.connect(self.on_filter_completed)
        worker_instance.filter_error.connect(self.on_filter_error)
        
        self.request_start_worker.emit(worker_instance)

    def on_filter_completed(self, matched_indices, elapsed_time: float) -> None:
        self.context._win.edit_content_panel.apply_filter(matched_indices)
        self.update_status("完成")
        self.write_log("SUCCESS", f"過濾完成！共匹配 {len(matched_indices) if matched_indices is not None else 0} 筆資料，耗時 {elapsed_time:.2f} 秒。")

    def on_filter_error(self, err_msg: str) -> None:
        self.update_status("錯誤")
        self.write_log("ERROR", f"過濾錯誤：{err_msg}")
        QMessageBox.critical(self, "過濾錯誤", err_msg)

    def set_enabled(self, enabled):
        self.txt_filter_start_row.setEnabled(enabled)
        self.txt_filter_end_row.setEnabled(enabled)
        self.btn_add_rule.setEnabled(enabled)
        self.btn_start_filter.setEnabled(enabled)
        self.txt_expression.setEnabled(enabled)
        for r in self.rules:
            r.setEnabled(enabled)

    def _sync_rules_to_config(self) -> None:
        if not self.context:
            return
        cfg = self.context.filter_panel_config
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
        if not self.context:
            return
        cfg = self.context.filter_panel_config
        config_dict = {
            "rules": cfg.rules,
            "logic_tree": cfg.logic_tree,
            "expr_text": cfg.expr_text,
            "start_row": cfg.start_row,
            "end_row": cfg.end_row,
        }
        self._apply_config_to_ui(config_dict)

    def show_controls(self):
        super().show_controls()
        self.restore_from_config()
