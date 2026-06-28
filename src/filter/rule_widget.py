from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QWidget, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor
from plugin_sdk.theme import applyStandardLabelStyle, applyStandardComboBoxStyle, applyStandardLineEditStyle

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
        applyStandardLabelStyle(self.lbl_rule_title)
        self.lbl_rule_title.setStyleSheet(self.lbl_rule_title.styleSheet() + " font-weight: bold;")
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
        applyStandardLabelStyle(lbl_col)
        lbl_col.setFixedWidth(75)
        self.cmb_compare_col = QComboBox()
        applyStandardComboBoxStyle(self.cmb_compare_col)
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
        applyStandardLabelStyle(lbl_range_start)
        lbl_range_start.setFixedWidth(55)
        self.cmb_range_start = QComboBox()
        applyStandardComboBoxStyle(self.cmb_range_start)
        self.cmb_range_start.currentIndexChanged.connect(self.parent_panel.on_rule_content_changed)
        row_start.addWidget(lbl_range_start)
        row_start.addWidget(self.cmb_range_start, stretch=1)
        range_cols_layout.addLayout(row_start)
        
        # 第二排：到欄位
        row_end = QHBoxLayout()
        row_end.setContentsMargins(0, 0, 0, 0)
        row_end.setSpacing(10)
        lbl_range_end = QLabel("到欄位：")
        applyStandardLabelStyle(lbl_range_end)
        lbl_range_end.setFixedWidth(55)
        self.cmb_range_end = QComboBox()
        applyStandardComboBoxStyle(self.cmb_range_end)
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
        applyStandardLabelStyle(lbl_method)
        lbl_method.setFixedWidth(75)
        self.cmb_compare_method = QComboBox()
        applyStandardComboBoxStyle(self.cmb_compare_method)
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
        applyStandardLabelStyle(lbl_target)
        lbl_target.setFixedWidth(75)
        self.cmb_compare_target = QComboBox()
        applyStandardComboBoxStyle(self.cmb_compare_target)
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
        applyStandardLineEditStyle(self.txt_compare_value)
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
        applyStandardComboBoxStyle(self.cmb_belong_value)
        self.cmb_belong_value.currentIndexChanged.connect(self.parent_panel.on_rule_content_changed)
        belong_layout.addWidget(self.cmb_belong_value)
        layout.addWidget(self.belong_container)
        
        self.belong_container.setVisible(False)

        if self.parent_panel.num_cols > 0:
            self.update_columns(self.parent_panel.num_cols)

    def update_columns(self, num_cols, active_cols=None):
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
        if active_cols is None:
            active_cols = []
            if isinstance(old_col, int):
                active_cols.append(old_col)
            if isinstance(old_start, int):
                active_cols.append(old_start)
            if isinstance(old_end, int):
                active_cols.append(old_end)
            if isinstance(old_target, int):
                active_cols.append(old_target)
            
        max_active_col = max(active_cols) if active_cols else -1
        limit = max(num_cols, max_active_col + 1)

        csv_data = self.parent_panel.context.csv_data if (self.parent_panel and self.parent_panel.context) else None

        if csv_data:
            for i in range(limit):
                text = csv_data.get_column_header(i)
                self.cmb_compare_col.addItem(text, i)
                self.cmb_range_start.addItem(text, i)
                self.cmb_range_end.addItem(text, i)

        idx = self.cmb_compare_col.findData(old_col)
        self.cmb_compare_col.setCurrentIndex(idx if idx >= 0 else 0)

        # 回復 cmb_range_start 的舊值，預設為第一欄 (index 0)
        self.cmb_range_start.setCurrentIndex(old_start if isinstance(old_start, int) and 0 <= old_start < self.cmb_range_start.count() else 0)

        # 回復 cmb_range_end 的舊值，預設為最後一欄 (index num_cols - 1)
        self.cmb_range_end.setCurrentIndex(old_end if isinstance(old_end, int) and 0 <= old_end < self.cmb_range_end.count() else (num_cols - 1 if num_cols > 0 else 0))

        self.update_target_options(num_cols, active_cols)

        self.cmb_compare_col.blockSignals(False)
        self.cmb_compare_target.blockSignals(False)
        self.cmb_range_start.blockSignals(False)
        self.cmb_range_end.blockSignals(False)
        self.update_belong_visibility()

    def update_target_options(self, num_cols, active_cols=None):
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
            if active_cols is None:
                active_target_cols = []
                if isinstance(old_target, int):
                    active_target_cols.append(old_target)
                max_active_target = max(active_target_cols) if active_target_cols else -1
            else:
                max_active_target = max(active_cols) if active_cols else -1
                
            limit = max(num_cols, max_active_target + 1)
            
            csv_data = self.parent_panel.context.csv_data if (self.parent_panel and self.parent_panel.context) else None
            if csv_data:
                for i in range(limit):
                    text = csv_data.get_column_header(i)
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
        self.update_target_options(self.parent_panel.num_cols)
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
            
        col = self.cmb_compare_col.currentData()
        if col == "none":
            col = -1
        elif col == "all":
            col = -2
        elif col == "range":
            col = -3
            
        target = self.cmb_compare_target.currentData()
        if target == "manual":
            target = -1
            
        return {
            "compare_col": col,
            "compare_method": self.cmb_compare_method.currentText(),
            "compare_target": target,
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

        col = cfg.get("compare_col", -1)
        method = cfg.get("compare_method", "完全符合")
        target = cfg.get("compare_target", -1)
        val = cfg.get("compare_value", "")
        b_idx = cfg.get("belong_value_idx", 0)
        range_start = cfg.get("range_start", 0)
        range_end = cfg.get("range_end", 0)

        # 1. 處理 compare_col 的對應與驗證
        if col == "none":
            col = -1
        elif col == "all":
            col = -2
        elif col == "range":
            col = -3
            
        if not isinstance(col, int):
            col = 0
        elif col < 0 and col not in (-1, -2, -3):
            col = 0
            
        ui_col = col
        if col == -1:
            ui_col = "none"
        elif col == -2:
            ui_col = "all"
        elif col == -3:
            ui_col = "range"

        # 2. 處理 compare_target 的對應與驗證
        if target == "manual":
            target = -1
            
        if not isinstance(target, int):
            target = 0
        elif target < 0 and target != -1:
            target = 0
            
        ui_target = target
        if target == -1:
            ui_target = "manual"

        # 3. 處理 range_start 的驗證
        if not isinstance(range_start, int) or range_start < 0:
            range_start = 0

        # 4. 處理 range_end 的驗證
        if not isinstance(range_end, int) or range_end < 0:
            range_end = 0

        # 預先依照 config 中的值更新下拉選單選項，以防 configured columns 超出 num_cols
        active_cols = []
        for v in (col, target, range_start, range_end):
            if isinstance(v, int) and v >= 0:
                active_cols.append(v)
        self.update_columns(self.parent_panel.num_cols, active_cols)

        idx = self.cmb_compare_col.findData(ui_col)
        self.cmb_compare_col.setCurrentIndex(idx if idx >= 0 else 0)

        idx = self.cmb_compare_method.findText(method)
        self.cmb_compare_method.setCurrentIndex(idx if idx >= 0 else 0)

        idx = self.cmb_compare_target.findData(ui_target)
        self.cmb_compare_target.setCurrentIndex(idx if idx >= 0 else 0)

        # 回復 cmb_range_start 的選擇
        self.cmb_range_start.setCurrentIndex(range_start if 0 <= range_start < self.cmb_range_start.count() else 0)

        # 回復 cmb_range_end 的選擇
        self.cmb_range_end.setCurrentIndex(range_end if 0 <= range_end < self.cmb_range_end.count() else 0)

        self.update_belong_visibility()

        if method in ("屬於", "不屬於"):
            if 0 <= b_idx < self.cmb_belong_value.count():
                self.cmb_belong_value.setCurrentIndex(b_idx)
        else:
            self.txt_compare_value.setText(val)

        self.cmb_compare_col.blockSignals(False)
        self.cmb_compare_method.blockSignals(False)
        self.cmb_compare_target.blockSignals(False)
        self.cmb_belong_value.blockSignals(False)
        self.cmb_range_start.blockSignals(False)
        self.cmb_range_end.blockSignals(False)
