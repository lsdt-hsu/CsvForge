import os
import re
from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QWidget, QHBoxLayout, QMessageBox, QRadioButton, QTextEdit,
    QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QPainter, QPen, QColor, QTransform, QPixmap, QIcon
from base_panel import BasePanel

from edit import logic_tree

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
        # 垂直佈局結構，固定控制項尺寸以防壓縮
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 頂部：規則標題與手繪刪除按鈕
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_rule_title = QLabel(f"規則 #{self.index}")
        self.lbl_rule_title.setStyleSheet("font-weight: bold; color: #a9b1d6;")
        title_layout.addWidget(self.lbl_rule_title)
        
        title_layout.addStretch()
        
        # 使用手繪的 CircularToggleButton 作為刪除按鈕
        self.btn_delete = CircularToggleButton()
        self.btn_delete.set_minus(True)  # ⊖
        self.btn_delete.setFixedSize(20, 20)
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setStyleSheet("border: none; background: transparent;")
        self.btn_delete.clicked.connect(self.on_delete_clicked)
        # 規則 1 不顯示刪除按鈕
        self.btn_delete.setVisible(self.index > 1)
        title_layout.addWidget(self.btn_delete)
        
        layout.addLayout(title_layout)

        # 1. 比對欄位列 (維持 75px label 寬度)
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

        # 初始化列下拉選單
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

        # 還原欄位選擇
        idx = self.cmb_compare_col.findData(old_col)
        self.cmb_compare_col.setCurrentIndex(idx if idx >= 0 else 0)

        # 更新比對目標的選項
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

class EditPanel(BasePanel):
    request_filter = pyqtSignal(dict)

    def __init__(self, parent=None, context=None):
        super().__init__(parent, title_text="編輯過濾", require_data_loading=True, context=context)
        self.num_cols = 0
        self.headers = None
        
        # 多規則狀態維護
        self.rules = []
        self.logic_tree = None
        self.expression_is_valid = True
        
        self.init_ui()

    def init_ui(self):
        # 1. 建立 QScrollArea 以支援規則列表與新增按鈕在超出高度時滾動，絕不壓縮 UI
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # 捲動區內部的實體 Widget
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(self.scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(12)

        # 規則列表容器
        self.rule_list_widget = QWidget()
        self.rule_list_layout = QVBoxLayout(self.rule_list_widget)
        self.rule_list_layout.setContentsMargins(0, 0, 0, 0)
        self.rule_list_layout.setSpacing(12)
        scroll_layout.addWidget(self.rule_list_widget)

        # 新增規則按鈕容器
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

        # 增加 QScrollArea 內部的最下方彈性拉伸，防止 Widget 被強行均分拉伸高度
        scroll_layout.addStretch(1)

        # 設定滾動區的 widget
        self.scroll_area.setWidget(self.scroll_content)
        
        # 將 QScrollArea 加到控制項佈局中，設定 stretch=1 使其佔滿剩餘可用空間
        self.controls_layout.addWidget(self.scroll_area, stretch=1)

        # 2. 開始過濾按鈕 (固定於下方，不隨滾動區捲動)
        self.btn_start_filter = QPushButton("開始過濾")
        self.btn_start_filter.clicked.connect(self.on_filter_clicked)
        self.controls_layout.addWidget(self.btn_start_filter)

        # 3. 當前規則邏輯編輯框 (固定於下方，不隨滾動區捲動)
        self.lbl_expr_title = QLabel("當前規則邏輯 (可編輯)：")
        self.lbl_expr_title.setStyleSheet("font-weight: bold; color: #565f89; margin-top: 5px;")
        self.controls_layout.addWidget(self.lbl_expr_title)

        self.txt_expression = CustomTextEdit()
        self.txt_expression.setPlaceholderText("例如: #1 AND (#2 OR #3)")
        self.txt_expression.setFixedHeight(45)
        self.txt_expression.setAcceptRichText(False)
        self.txt_expression.focus_out_signal.connect(self.on_expression_focus_out)
        self.controls_layout.addWidget(self.txt_expression)

        # 初始化第一條規則與邏輯樹
        self.reset_panel()

    def clear_layout(self, layout):
        """清空 Layout 內的所有子控制項與彈性拉伸。"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def reset_panel(self):
        super().reset_panel()
        self.num_cols = 0
        self.headers = None

        # 清空規則佈局
        self.clear_layout(self.rule_list_layout)
        self.rules.clear()

        # 初始化單一葉子節點邏輯樹
        self.logic_tree = logic_tree.LogicNode("LEAF", leaf_idx=1)
        self.expression_is_valid = True
        self.txt_expression.setStyleSheet("")

        # 建立第一個規則 Widget
        w = RuleWidget(1, self)
        self.rules.append(w)
        self.rule_list_layout.addWidget(w)

        self.btn_add_rule.setVisible(True)
        self.txt_expression.setPlainText("#1")

    def check_expression_validity(self):
        if not self.expression_is_valid:
            QMessageBox.warning(self, "錯誤", "當前規則邏輯表達式不合法，請先修正紅框內的表達式。")
            return False
        return True

    def on_rule_content_changed(self):
        pass

    def add_rule(self):
        if not self.check_expression_validity():
            return
        if len(self.rules) >= 5:
            return

        new_idx = len(self.rules) + 1
        
        # 呼叫樹維護演算法
        self.logic_tree = logic_tree.add_rule_node(self.logic_tree, new_idx)
        
        # 建立新規則 UI Widget
        w = RuleWidget(new_idx, self)
        self.rules.append(w)
        
        # 直接加入到規則佈局中
        self.rule_list_layout.addWidget(w)

        # 控制新增按鈕顯示
        if len(self.rules) >= 5:
            self.btn_add_rule.setVisible(False)

        # 自動生成與格式化新表達式字串並填入
        new_expr = logic_tree.to_string(self.logic_tree)
        self.txt_expression.blockSignals(True)
        self.txt_expression.setPlainText(new_expr)
        self.txt_expression.setStyleSheet("")
        self.txt_expression.blockSignals(False)
        self.expression_is_valid = True

    def delete_rule(self, del_idx):
        if not self.check_expression_validity():
            return
        if len(self.rules) <= 1:
            return

        # 呼叫樹刪除演算法
        self.logic_tree = logic_tree.remove_rule_node(self.logic_tree, del_idx)

        # 移除並銷毀對應規則 UI Widget
        w_to_del = self.rules[del_idx - 1]
        self.rule_list_layout.removeWidget(w_to_del)
        w_to_del.deleteLater()
        self.rules.pop(del_idx - 1)

        # 重整剩餘 Widget 的序號標籤與刪除按鈕可見性
        for i, w in enumerate(self.rules):
            w.index = i + 1
            w.lbl_rule_title.setText(f"規則 #{w.index}")
            w.btn_delete.setVisible(w.index > 1)

        # 控制新增按鈕顯示
        if len(self.rules) < 5:
            self.btn_add_rule.setVisible(True)

        # 更新與重繪表達式字串
        new_expr = logic_tree.to_string(self.logic_tree)
        self.txt_expression.blockSignals(True)
        self.txt_expression.setPlainText(new_expr)
        self.txt_expression.setStyleSheet("")
        self.txt_expression.blockSignals(False)
        self.expression_is_valid = True

    def on_expression_focus_out(self):
        expr = self.txt_expression.toPlainText().strip()
        
        # 若為空字串，自動填入全部 AND 運算式
        if not expr:
            expr = " AND ".join(f"#{i}" for i in range(1, len(self.rules) + 1))
            self.txt_expression.setPlainText(expr)

        try:
            # 方案 B 左結合與語意驗證解析
            tree = logic_tree.parse_expression(expr, len(self.rules))
            self.logic_tree = tree
            
            # 將解析後的 AST 重新格式化成字串並回填
            formatted_expr = logic_tree.to_string(tree)
            self.txt_expression.blockSignals(True)
            self.txt_expression.setPlainText(formatted_expr)
            self.txt_expression.setStyleSheet("")
            self.txt_expression.blockSignals(False)
            
            self.expression_is_valid = True
        except ValueError as e:
            # 解析失敗，外框變紅
            self.txt_expression.setStyleSheet("border: 2px solid #f7768e; border-radius: 4px;")
            self.expression_is_valid = False

    def update_column_dropdowns(self, num_cols, headers=None):
        self.show_controls()

        self.num_cols = num_cols
        self.headers = headers

        for r in self.rules:
            r.update_columns(num_cols, headers)

    def on_filter_clicked(self):
        # 1. 驗證編輯框是否合法
        if not self.check_expression_validity():
            return

        # 2. 逐一檢查與驗證規則參數合法性
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
                        # 欄位與欄位比對，比對欄位不可與比對目標相同
                        if col == target:
                            QMessageBox.warning(self, "錯誤", f"規則 #{r.index}：欄位比對不可選擇相同的欄位。")
                            return

        # 3. 組裝發射過濾參數
        filter_config = {
            "rules": [r.get_config() for r in self.rules],
            "logic_tree": logic_tree.serialize_tree(self.logic_tree)
        }
        self.request_filter.emit(filter_config)

    def set_enabled(self, enabled):
        self.btn_add_rule.setEnabled(enabled)
        self.btn_start_filter.setEnabled(enabled)
        self.txt_expression.setEnabled(enabled)
        for r in self.rules:
            r.setEnabled(enabled)

    def get_config(self) -> dict:
        return {
            "rules": [r.get_config() for r in self.rules],
            "logic_tree": logic_tree.serialize_tree(self.logic_tree),
            "expr_text": self.txt_expression.toPlainText()
        }

    def set_config(self, config: dict):
        if not config:
            return

        self.txt_expression.blockSignals(True)

        # 清除現有規則 Widget
        self.clear_layout(self.rule_list_layout)
        self.rules.clear()

        # 重新建立 rules
        rules_cfg = config.get("rules", [])
        for i, r_cfg in enumerate(rules_cfg):
            w = RuleWidget(i + 1, self)
            self.rules.append(w)
            self.rule_list_layout.addWidget(w)
            w.set_config(r_cfg)

        # 還原邏輯樹
        lt_cfg = config.get("logic_tree")
        self.logic_tree = logic_tree.deserialize_tree(lt_cfg)

        # 還原表達式文字
        expr_text = config.get("expr_text", "")
        self.txt_expression.setPlainText(expr_text)
        self.txt_expression.blockSignals(False)

        # 觸發一次焦點離開驗證以確立合法性
        self.on_expression_focus_out()

        # 新增按鈕可見性控制
        self.btn_add_rule.setVisible(len(self.rules) < 5)
