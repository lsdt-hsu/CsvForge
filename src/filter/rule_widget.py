from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QWidget, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor

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
        self.cmb_compare_col.addItem("欄位範圍", "range")
        self.cmb_compare_col.currentIndexChanged.connect(self.on_col_changed)
        row1.addWidget(lbl_col)
        row1.addWidget(self.cmb_compare_col)
        layout.addLayout(row1)

        # 欄位範圍的「從欄位」與「到欄位」容器 (上下兩排)
        self.range_cols_container = QWidget()
        range_cols_layout = QVBoxLayout(self.range_cols_container)
        range_cols_layout.setContentsMargins(20, 0, 0, 0)
        range_cols_layout.setSpacing(6)
        
        # 第一排：從欄位
        row_start = QHBoxLayout()
        row_start.setContentsMargins(0, 0, 0, 0)
        row_start.setSpacing(10)
        lbl_range_start = QLabel("從欄位：")
        lbl_range_start.setFixedWidth(55)
        self.cmb_range_start = QComboBox()
        self.cmb_range_start.currentIndexChanged.connect(self.parent_panel.on_rule_content_changed)
        row_start.addWidget(lbl_range_start)
        row_start.addWidget(self.cmb_range_start, stretch=1)
        range_cols_layout.addLayout(row_start)
        
        # 第二排：到欄位
        row_end = QHBoxLayout()
        row_end.setContentsMargins(0, 0, 0, 0)
        row_end.setSpacing(10)
        lbl_range_end = QLabel("到欄位：")
        lbl_range_end.setFixedWidth(55)
        self.cmb_range_end = QComboBox()
        self.cmb_range_end.currentIndexChanged.connect(self.parent_panel.on_rule_content_changed)
        row_end.addWidget(lbl_range_end)
        row_end.addWidget(self.cmb_range_end, stretch=1)
        range_cols_layout.addLayout(row_end)
        
        layout.addWidget(self.range_cols_container)
        self.range_cols_container.setVisible(False)

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
        self.cmb_range_start.blockSignals(True)
        self.cmb_range_end.blockSignals(True)
        
        old_col = self.cmb_compare_col.currentData()
        old_target = self.cmb_compare_target.currentData()
        old_start = self.cmb_range_start.currentData()
        old_end = self.cmb_range_end.currentData()

        self.cmb_compare_col.clear()
        self.cmb_compare_col.addItem("不過濾", "none")
        self.cmb_compare_col.addItem("所有欄位", "all")
        self.cmb_compare_col.addItem("欄位範圍", "range")
        
        self.cmb_range_start.clear()
        self.cmb_range_end.clear()

        # 找出當前已選取的所有整數欄位 index，並計算 max_active_col
        active_cols = []
        if isinstance(old_col, int):
            active_cols.append(old_col)
        if isinstance(old_start, int):
            active_cols.append(old_start)
        if isinstance(old_end, int):
            active_cols.append(old_end)
            
        max_active_col = max(active_cols) if active_cols else -1
        limit = max(num_cols, max_active_col + 1)

        csv_data = self.parent_panel.context.csv_data if self.parent_panel.context else None

        for i in range(limit):
            text = csv_data.get_column_header(i) if csv_data else f"第 {i+1} 欄"
            self.cmb_compare_col.addItem(text, i)
            self.cmb_range_start.addItem(text, i)
            self.cmb_range_end.addItem(text, i)

        idx = self.cmb_compare_col.findData(old_col)
        self.cmb_compare_col.setCurrentIndex(idx if idx >= 0 else 0)

        # 回復 cmb_range_start 的舊值，預設為第一欄 (index 0)
        idx_start = self.cmb_range_start.findData(old_start)
        self.cmb_range_start.setCurrentIndex(idx_start if idx_start >= 0 else 0)

        # 回復 cmb_range_end 的舊值，預設為最後一欄 (index num_cols - 1)
        idx_end = self.cmb_range_end.findData(old_end)
        self.cmb_range_end.setCurrentIndex(idx_end if idx_end >= 0 else (num_cols - 1 if num_cols > 0 else 0))

        self.update_target_options(num_cols, headers)

        self.cmb_compare_col.blockSignals(False)
        self.cmb_compare_target.blockSignals(False)
        self.cmb_range_start.blockSignals(False)
        self.cmb_range_end.blockSignals(False)
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
            
            # 找出當前已選取的整數目標欄位，以做越界防護
            active_target_cols = []
            if isinstance(old_target, int):
                active_target_cols.append(old_target)
                
            max_active_target = max(active_target_cols) if active_target_cols else -1
            limit = max(num_cols, max_active_target + 1)
            
            csv_data = self.parent_panel.context.csv_data if self.parent_panel.context else None
            for i in range(limit):
                text = csv_data.get_column_header(i) if csv_data else f"第 {i+1} 欄"
                self.cmb_compare_target.addItem(text, i)
        
        idx = self.cmb_compare_target.findData(old_target)
        self.cmb_compare_target.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_compare_target.blockSignals(False)

    def update_belong_visibility(self):
        col_type = self.cmb_compare_col.currentData()
        
        # 控制範圍容器的顯示
        if col_type == "range":
            self.range_cols_container.setVisible(True)
        else:
            self.range_cols_container.setVisible(False)

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
            "belong_value_idx": self.cmb_belong_value.currentIndex(),
            "range_start": self.cmb_range_start.currentData(),
            "range_end": self.cmb_range_end.currentData()
        }

    def set_config(self, cfg):
        self.cmb_compare_col.blockSignals(True)
        self.cmb_compare_method.blockSignals(True)
        self.cmb_compare_target.blockSignals(True)
        self.cmb_belong_value.blockSignals(True)
        self.cmb_range_start.blockSignals(True)
        self.cmb_range_end.blockSignals(True)

        col = cfg.get("compare_col", "none")
        method = cfg.get("compare_method", "完全符合")
        target = cfg.get("compare_target", "manual")
        val = cfg.get("compare_value", "")
        b_idx = cfg.get("belong_value_idx", 0)
        range_start = cfg.get("range_start")
        range_end = cfg.get("range_end")

        idx = self.cmb_compare_col.findData(col)
        if idx < 0 and isinstance(col, int):
            self.cmb_compare_col.addItem(f"欄位{col+1}", col)
            idx = self.cmb_compare_col.findData(col)
        self.cmb_compare_col.setCurrentIndex(idx if idx >= 0 else 0)

        idx = self.cmb_compare_method.findText(method)
        self.cmb_compare_method.setCurrentIndex(idx if idx >= 0 else 0)

        self.update_target_options(self.parent_panel.num_cols, self.parent_panel.headers)

        idx = self.cmb_compare_target.findData(target)
        if idx < 0 and isinstance(target, int) and method not in ("屬於", "不屬於"):
            self.cmb_compare_target.addItem(f"欄位{target+1}", target)
            idx = self.cmb_compare_target.findData(target)
        self.cmb_compare_target.setCurrentIndex(idx if idx >= 0 else 0)

        # 回復 cmb_range_start 的選擇
        if range_start is not None:
            idx_start = self.cmb_range_start.findData(range_start)
            if idx_start < 0 and isinstance(range_start, int):
                self.cmb_range_start.addItem(f"欄位{range_start+1}", range_start)
                idx_start = self.cmb_range_start.findData(range_start)
            self.cmb_range_start.setCurrentIndex(idx_start if idx_start >= 0 else 0)
        else:
            self.cmb_range_start.setCurrentIndex(0)

        # 回復 cmb_range_end 的選擇
        if range_end is not None:
            idx_end = self.cmb_range_end.findData(range_end)
            if idx_end < 0 and isinstance(range_end, int):
                self.cmb_range_end.addItem(f"欄位{range_end+1}", range_end)
                idx_end = self.cmb_range_end.findData(range_end)
            self.cmb_range_end.setCurrentIndex(idx_end if idx_end >= 0 else 0)
        else:
            num_cols = self.parent_panel.num_cols
            self.cmb_range_end.setCurrentIndex(num_cols - 1 if num_cols > 0 else 0)

        self.update_belong_visibility()

        if method in ("屬於", "不屬於"):
            self.cmb_belong_value.setCurrentIndex(b_idx)
        else:
            self.txt_compare_value.setText(val)

        self.cmb_compare_col.blockSignals(False)
        self.cmb_compare_method.blockSignals(False)
        self.cmb_compare_target.blockSignals(False)
        self.cmb_belong_value.blockSignals(False)
        self.cmb_range_start.blockSignals(False)
        self.cmb_range_end.blockSignals(False)
