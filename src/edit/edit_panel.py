import os
from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QWidget, QHBoxLayout, QMessageBox, QRadioButton
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QPainter, QPen, QColor, QTransform, QPixmap, QIcon
from base_panel import BasePanel

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
        # Let QSS render background and borders
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

class EditPanel(BasePanel):
    request_filter = pyqtSignal(dict) # 傳送包含雙規則的 filter_config 字典

    def __init__(self, parent=None):
        super().__init__(parent)
        self.num_cols = 0
        self.headers = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl_sec = QLabel("編輯過濾")
        lbl_sec.setObjectName("sectionHeader")
        layout.addWidget(lbl_sec)

        # 尚未載入資料提示標籤
        self.lbl_no_data = QLabel("尚未載入資料")
        self.lbl_no_data.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_no_data.setStyleSheet("color: #565f89; font-style: italic; margin-top: 5px;")
        layout.addWidget(self.lbl_no_data)

        # 建立一個容器以包裝所有過濾控制項
        self.controls_container = QWidget()
        controls_layout = QVBoxLayout(self.controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        # 1. 比對欄位下拉選單
        self.lbl_compare_col = QLabel("比對欄位：")
        self.lbl_compare_col.setFixedWidth(75)
        self.cmb_compare_col = QComboBox()
        self.cmb_compare_col.addItem("不過濾", "none")
        self.cmb_compare_col.addItem("所有欄位", "all")
        self.cmb_compare_col.addItem("來源-目標欄位", "range")
        self.cmb_compare_col.currentIndexChanged.connect(self.on_compare_col_changed)
        
        row1_layout = QHBoxLayout()
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(10)
        row1_layout.addWidget(self.lbl_compare_col)
        row1_layout.addWidget(self.cmb_compare_col)
        controls_layout.addLayout(row1_layout)

        # 建立一個容器以群組「比對方式」與「比對目標」，便於一併隱藏/顯示
        self.filter_options_widget = QWidget()
        self.filter_options_layout = QVBoxLayout(self.filter_options_widget)
        self.filter_options_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_options_layout.setSpacing(8)

        # 2. 比對方式下拉選單
        self.lbl_compare_method = QLabel("比對方式：")
        self.lbl_compare_method.setFixedWidth(75)
        self.cmb_compare_method = QComboBox()
        self.cmb_compare_method.addItems(["完全符合", "包含", "未包含", "正規表達式", "屬於", "不屬於"])
        self.cmb_compare_method.currentIndexChanged.connect(self.on_compare_method_changed)
        
        row2_layout = QHBoxLayout()
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(10)
        row2_layout.addWidget(self.lbl_compare_method)
        row2_layout.addWidget(self.cmb_compare_method)
        self.filter_options_layout.addLayout(row2_layout)

        # 3. 比對目標下拉選單
        self.lbl_compare_target = QLabel("比對目標：")
        self.lbl_compare_target.setFixedWidth(75)
        self.cmb_compare_target = QComboBox()
        self.cmb_compare_target.addItem("手動輸入", "manual")
        self.cmb_compare_target.currentIndexChanged.connect(self.on_compare_target_changed)
        
        row3_layout = QHBoxLayout()
        row3_layout.setContentsMargins(0, 0, 0, 0)
        row3_layout.setSpacing(10)
        row3_layout.addWidget(self.lbl_compare_target)
        row3_layout.addWidget(self.cmb_compare_target)
        self.filter_options_layout.addLayout(row3_layout)

        # 4. 比對值輸入框 (手動輸入的子項目，採用內縮佈局且無 label)
        self.value_container = QWidget()
        value_layout = QHBoxLayout(self.value_container)
        value_layout.setContentsMargins(20, 0, 0, 0)  # 內縮 20 像素
        value_layout.setSpacing(0)
        self.txt_compare_value = QLineEdit()
        self.txt_compare_value.setPlaceholderText("輸入比對值或正規表達式")
        value_layout.addWidget(self.txt_compare_value)
        self.filter_options_layout.addWidget(self.value_container)

        # 4-2. 屬於子項目下拉選單 (採用內縮佈局且無 label)
        self.belong_container = QWidget()
        belong_layout = QHBoxLayout(self.belong_container)
        belong_layout.setContentsMargins(20, 0, 0, 0)  # 內縮 20 像素
        belong_layout.setSpacing(0)
        self.cmb_belong_value = QComboBox()
        belong_layout.addWidget(self.cmb_belong_value)
        self.filter_options_layout.addWidget(self.belong_container)
        self.belong_container.setVisible(False)

        controls_layout.addWidget(self.filter_options_widget)

        # 5. 切換與邏輯運算元列
        toggle_layout = QHBoxLayout()
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setSpacing(10)

        self.btn_toggle_rule = CircularToggleButton()
        self.btn_toggle_rule.setObjectName("btnToggleRule")
        self.btn_toggle_rule.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_rule.clicked.connect(self.on_toggle_rule_clicked)
        toggle_layout.addWidget(self.btn_toggle_rule, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 上下交換按鈕
        self.btn_swap_rules = QPushButton()
        self.btn_swap_rules.setObjectName("btnSwapRules")
        self.btn_swap_rules.setFixedSize(30, 30)
        self.btn_swap_rules.setCursor(Qt.CursorShape.PointingHandCursor)
        
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        swap_icon_path = os.path.join(root_dir, "assets", "swap.png")
        if os.path.exists(swap_icon_path):
            pixmap = QPixmap(swap_icon_path)
            transform = QTransform().rotate(90)
            rotated_pixmap = pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
            self.btn_swap_rules.setIcon(QIcon(rotated_pixmap))
            self.btn_swap_rules.setIconSize(QSize(20, 20))
            
        self.btn_swap_rules.clicked.connect(self.swap_rules)
        self.btn_swap_rules.setVisible(False) # 預設隱藏，只在雙規則模式下顯示
        toggle_layout.addWidget(self.btn_swap_rules, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 在交換按鈕與單選按鈕之間加入彈性空白，將 AND / OR 單選按鈕推至最右側
        toggle_layout.addStretch()

        self.op_widget = QWidget()
        op_layout = QHBoxLayout(self.op_widget)
        op_layout.setContentsMargins(5, 0, 0, 0)
        op_layout.setSpacing(15)
        op_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.rbtn_and = QRadioButton("AND")
        self.rbtn_and.setChecked(True)
        self.rbtn_and.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.rbtn_or = QRadioButton("OR")
        self.rbtn_or.setCursor(Qt.CursorShape.PointingHandCursor)
        
        op_layout.addWidget(self.rbtn_and)
        op_layout.addWidget(self.rbtn_or)
        toggle_layout.addWidget(self.op_widget, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        controls_layout.addLayout(toggle_layout)

        # 6. 規則二容器與控制項
        self.second_rule_container = QWidget()
        second_rule_layout = QVBoxLayout(self.second_rule_container)
        second_rule_layout.setContentsMargins(0, 0, 0, 0)
        second_rule_layout.setSpacing(8)

        # 比對欄位二下拉選單
        self.lbl_compare_col2 = QLabel("比對欄位：")
        self.lbl_compare_col2.setFixedWidth(75)
        self.cmb_compare_col2 = QComboBox()
        self.cmb_compare_col2.addItem("不過濾", "none")
        self.cmb_compare_col2.addItem("所有欄位", "all")
        self.cmb_compare_col2.addItem("來源-目標欄位", "range")
        self.cmb_compare_col2.currentIndexChanged.connect(self.on_compare_col2_changed)
        
        row1_layout2 = QHBoxLayout()
        row1_layout2.setContentsMargins(0, 0, 0, 0)
        row1_layout2.setSpacing(10)
        row1_layout2.addWidget(self.lbl_compare_col2)
        row1_layout2.addWidget(self.cmb_compare_col2)
        second_rule_layout.addLayout(row1_layout2)

        # 建立一個容器以群組「比對方式二」與「比對目標二」，便於一併隱藏/顯示
        self.filter_options_widget2 = QWidget()
        self.filter_options_layout2 = QVBoxLayout(self.filter_options_widget2)
        self.filter_options_layout2.setContentsMargins(0, 0, 0, 0)
        self.filter_options_layout2.setSpacing(8)

        # 比對方式二下拉選單
        self.lbl_compare_method2 = QLabel("比對方式：")
        self.lbl_compare_method2.setFixedWidth(75)
        self.cmb_compare_method2 = QComboBox()
        self.cmb_compare_method2.addItems(["完全符合", "包含", "未包含", "正規表達式", "屬於", "不屬於"])
        self.cmb_compare_method2.currentIndexChanged.connect(self.on_compare_method2_changed)
        
        row2_layout2 = QHBoxLayout()
        row2_layout2.setContentsMargins(0, 0, 0, 0)
        row2_layout2.setSpacing(10)
        row2_layout2.addWidget(self.lbl_compare_method2)
        row2_layout2.addWidget(self.cmb_compare_method2)
        self.filter_options_layout2.addLayout(row2_layout2)

        # 比對目標二下拉選單
        self.lbl_compare_target2 = QLabel("比對目標：")
        self.lbl_compare_target2.setFixedWidth(75)
        self.cmb_compare_target2 = QComboBox()
        self.cmb_compare_target2.addItem("手動輸入", "manual")
        self.cmb_compare_target2.currentIndexChanged.connect(self.on_compare_target2_changed)
        
        row3_layout2 = QHBoxLayout()
        row3_layout2.setContentsMargins(0, 0, 0, 0)
        row3_layout2.setSpacing(10)
        row3_layout2.addWidget(self.lbl_compare_target2)
        row3_layout2.addWidget(self.cmb_compare_target2)
        self.filter_options_layout2.addLayout(row3_layout2)

        # 比對值二輸入框
        self.value_container2 = QWidget()
        value_layout2 = QHBoxLayout(self.value_container2)
        value_layout2.setContentsMargins(20, 0, 0, 0)  # 內縮 20 像素
        value_layout2.setSpacing(0)
        self.txt_compare_value2 = QLineEdit()
        self.txt_compare_value2.setPlaceholderText("輸入比對值或正規表達式")
        value_layout2.addWidget(self.txt_compare_value2)
        self.filter_options_layout2.addWidget(self.value_container2)

        # 屬於子項目二下拉選單 (採用內縮佈局且無 label)
        self.belong_container2 = QWidget()
        belong_layout2 = QHBoxLayout(self.belong_container2)
        belong_layout2.setContentsMargins(20, 0, 0, 0)  # 內縮 20 像素
        belong_layout2.setSpacing(0)
        self.cmb_belong_value2 = QComboBox()
        belong_layout2.addWidget(self.cmb_belong_value2)
        self.filter_options_layout2.addWidget(self.belong_container2)
        self.belong_container2.setVisible(False)

        second_rule_layout.addWidget(self.filter_options_widget2)
        controls_layout.addWidget(self.second_rule_container)

        # 開始過濾按鈕
        self.btn_start_filter = QPushButton("開始過濾")
        self.btn_start_filter.clicked.connect(self.on_filter_clicked)
        controls_layout.addWidget(self.btn_start_filter)

        layout.addWidget(self.controls_container)
        layout.addStretch()

        # 初始化控制項顯示狀態：未載入資料狀態
        self.lbl_no_data.setVisible(True)
        self.controls_container.setVisible(False)
        
        # 預設為單規則狀態
        self.is_dual = False
        self.set_dual_state(False)
        
        self.on_compare_col_changed(0)
        self.on_compare_col2_changed(0)
    def on_compare_col_changed(self, idx):
        # 取得目前比對欄位的值
        col_type = self.cmb_compare_col.currentData()
        if col_type is None or col_type == "none":
            # 隱藏所有選項目標與輸入框
            self.filter_options_widget.setVisible(False)
        else:
            self.filter_options_widget.setVisible(True)
            # 根據比對目標決定輸入框與屬於選單是否顯示
            self.update_belong_visibility(self.cmb_compare_method, self.cmb_compare_target, self.value_container, self.belong_container, self.cmb_belong_value)

    def reset_panel(self):
        self.lbl_no_data.setVisible(True)
        self.controls_container.setVisible(False)

        # 暫時阻擋訊號以避免頻繁觸發畫面重繪
        self.cmb_compare_col.blockSignals(True)
        self.cmb_compare_target.blockSignals(True)
        self.cmb_compare_col2.blockSignals(True)
        self.cmb_compare_target2.blockSignals(True)
        self.cmb_compare_method.blockSignals(True)
        self.cmb_compare_method2.blockSignals(True)
        self.cmb_belong_value.blockSignals(True)
        self.cmb_belong_value2.blockSignals(True)
        
        self.cmb_compare_col.clear()
        self.cmb_compare_col.addItem("不過濾", "none")
        self.cmb_compare_col.addItem("所有欄位", "all")
        self.cmb_compare_col.addItem("來源-目標欄位", "range")
        self.cmb_compare_col.setCurrentIndex(0)
        
        self.cmb_compare_target.clear()
        self.cmb_compare_target.addItem("手動輸入", "manual")
        self.cmb_compare_target.setCurrentIndex(0)

        self.cmb_compare_col2.clear()
        self.cmb_compare_col2.addItem("不過濾", "none")
        self.cmb_compare_col2.addItem("所有欄位", "all")
        self.cmb_compare_col2.addItem("來源-目標欄位", "range")
        self.cmb_compare_col2.setCurrentIndex(0)
        
        self.cmb_compare_target2.clear()
        self.cmb_compare_target2.addItem("手動輸入", "manual")
        self.cmb_compare_target2.setCurrentIndex(0)

        self.cmb_compare_method.setCurrentIndex(0)
        self.cmb_compare_method2.setCurrentIndex(0)
        
        self.cmb_belong_value.clear()
        self.cmb_belong_value2.clear()
        
        self.txt_compare_value.clear()
        self.txt_compare_value2.clear()
        
        self.cmb_compare_col.blockSignals(False)
        self.cmb_compare_target.blockSignals(False)
        self.cmb_compare_col2.blockSignals(False)
        self.cmb_compare_target2.blockSignals(False)
        self.cmb_compare_method.blockSignals(False)
        self.cmb_compare_method2.blockSignals(False)
        self.cmb_belong_value.blockSignals(False)
        self.cmb_belong_value2.blockSignals(False)
        
        # 預設回歸單規則狀態
        self.set_dual_state(False)
        self.rbtn_and.setChecked(True)
        
        # 手動觸發一次以隱藏所有子項目
        self.on_compare_col_changed(0)
        self.on_compare_col2_changed(0)

    def on_compare_target_changed(self, idx):
        self.update_belong_visibility(self.cmb_compare_method, self.cmb_compare_target, self.value_container, self.belong_container, self.cmb_belong_value)

    def on_compare_col2_changed(self, idx):
        col_type = self.cmb_compare_col2.currentData()
        if col_type is None or col_type == "none":
            self.filter_options_widget2.setVisible(False)
        else:
            self.filter_options_widget2.setVisible(True)
            self.update_belong_visibility(self.cmb_compare_method2, self.cmb_compare_target2, self.value_container2, self.belong_container2, self.cmb_belong_value2)

    def on_compare_target2_changed(self, idx):
        self.update_belong_visibility(self.cmb_compare_method2, self.cmb_compare_target2, self.value_container2, self.belong_container2, self.cmb_belong_value2)

    def on_toggle_rule_clicked(self):
        self.set_dual_state(not self.is_dual)

    def set_dual_state(self, is_dual):
        self.is_dual = is_dual
        if is_dual:
            self.btn_toggle_rule.set_minus(True)
            self.btn_swap_rules.setVisible(True)
            self.op_widget.setVisible(True)
            self.second_rule_container.setVisible(True)
            self.on_compare_col2_changed(self.cmb_compare_col2.currentIndex())
        else:
            self.btn_toggle_rule.set_minus(False)
            self.btn_swap_rules.setVisible(False)
            self.op_widget.setVisible(False)
            self.second_rule_container.setVisible(False)

    def update_column_dropdowns(self, num_cols, headers=None):
        self.lbl_no_data.setVisible(False)
        self.controls_container.setVisible(True)

        self.num_cols = num_cols
        self.headers = headers

        # 記下目前選取的狀態，以便重整時儘量保留
        old_col_idx = self.cmb_compare_col.currentIndex()
        old_method_idx = self.cmb_compare_method.currentIndex()
        old_target_idx = self.cmb_compare_target.currentIndex()
        old_belong_idx = self.cmb_belong_value.currentIndex()
        
        old_col2_idx = self.cmb_compare_col2.currentIndex()
        old_method2_idx = self.cmb_compare_method2.currentIndex()
        old_target2_idx = self.cmb_compare_target2.currentIndex()
        old_belong2_idx = self.cmb_belong_value2.currentIndex()

        # 暫時阻擋訊號
        self.cmb_compare_col.blockSignals(True)
        self.cmb_compare_method.blockSignals(True)
        self.cmb_compare_target.blockSignals(True)
        self.cmb_belong_value.blockSignals(True)
        self.cmb_compare_col2.blockSignals(True)
        self.cmb_compare_method2.blockSignals(True)
        self.cmb_compare_target2.blockSignals(True)
        self.cmb_belong_value2.blockSignals(True)

        # 1. 重整比對欄位一
        self.cmb_compare_col.clear()
        self.cmb_compare_col.addItem("不過濾", "none")
        self.cmb_compare_col.addItem("所有欄位", "all")
        self.cmb_compare_col.addItem("來源-目標欄位", "range")
        for i in range(num_cols):
            text = f"{i+1}. {headers[i]}" if headers and i < len(headers) else f"第 {i+1} 欄"
            self.cmb_compare_col.addItem(text, i)  # userData contains 0-based index

        # 2. 重整比對欄位二
        self.cmb_compare_col2.clear()
        self.cmb_compare_col2.addItem("不過濾", "none")
        self.cmb_compare_col2.addItem("所有欄位", "all")
        self.cmb_compare_col2.addItem("來源-目標欄位", "range")
        for i in range(num_cols):
            text = f"{i+1}. {headers[i]}" if headers and i < len(headers) else f"第 {i+1} 欄"
            self.cmb_compare_col2.addItem(text, i)  # userData contains 0-based index

        # 還原比對方式
        if old_method_idx < self.cmb_compare_method.count():
            self.cmb_compare_method.setCurrentIndex(old_method_idx)
        else:
            self.cmb_compare_method.setCurrentIndex(0)
            
        if old_method2_idx < self.cmb_compare_method2.count():
            self.cmb_compare_method2.setCurrentIndex(old_method2_idx)
        else:
            self.cmb_compare_method2.setCurrentIndex(0)

        # 更新比對目標的選項（依據目前比對方式）
        self.update_target_options(self.cmb_compare_method, self.cmb_compare_target, num_cols, headers)
        self.update_target_options(self.cmb_compare_method2, self.cmb_compare_target2, num_cols, headers)

        # 還原比對目標的選擇
        if old_target_idx < self.cmb_compare_target.count():
            self.cmb_compare_target.setCurrentIndex(old_target_idx)
        else:
            self.cmb_compare_target.setCurrentIndex(0)
            
        if old_target2_idx < self.cmb_compare_target2.count():
            self.cmb_compare_target2.setCurrentIndex(old_target2_idx)
        else:
            self.cmb_compare_target2.setCurrentIndex(0)

        # 更新屬於下拉選單的選項與顯示狀態
        self.update_belong_visibility(self.cmb_compare_method, self.cmb_compare_target, self.value_container, self.belong_container, self.cmb_belong_value)
        self.update_belong_visibility(self.cmb_compare_method2, self.cmb_compare_target2, self.value_container2, self.belong_container2, self.cmb_belong_value2)

        # 還原屬於子選項選擇
        if old_belong_idx < self.cmb_belong_value.count():
            self.cmb_belong_value.setCurrentIndex(old_belong_idx)
        if old_belong2_idx < self.cmb_belong_value2.count():
            self.cmb_belong_value2.setCurrentIndex(old_belong2_idx)

        # 還原比對欄位選擇
        if old_col_idx < self.cmb_compare_col.count():
            self.cmb_compare_col.setCurrentIndex(old_col_idx)
        else:
            self.cmb_compare_col.setCurrentIndex(0)
            
        if old_col2_idx < self.cmb_compare_col2.count():
            self.cmb_compare_col2.setCurrentIndex(old_col2_idx)
        else:
            self.cmb_compare_col2.setCurrentIndex(0)

        # 解除訊號阻擋
        self.cmb_compare_col.blockSignals(False)
        self.cmb_compare_method.blockSignals(False)
        self.cmb_compare_target.blockSignals(False)
        self.cmb_belong_value.blockSignals(False)
        self.cmb_compare_col2.blockSignals(False)
        self.cmb_compare_method2.blockSignals(False)
        self.cmb_compare_target2.blockSignals(False)
        self.cmb_belong_value2.blockSignals(False)
        
        # 手動觸發 visibility 的更新
        self.on_compare_col_changed(self.cmb_compare_col.currentIndex())
        self.on_compare_col2_changed(self.cmb_compare_col2.currentIndex())

    def on_filter_clicked(self):
        compare_col = self.cmb_compare_col.currentData()
        compare_method = self.cmb_compare_method.currentText()
        compare_target = self.cmb_compare_target.currentData()
        
        if compare_method in ("屬於", "不屬於"):
            compare_value = self.cmb_belong_value.currentText()
        else:
            compare_value = self.txt_compare_value.text()

        # 驗證規則一
        if compare_col != "none":
            if compare_method not in ("屬於", "不屬於"):
                if compare_target == "manual":
                    if compare_method == "正規表達式":
                        import re
                        try:
                            re.compile(compare_value)
                        except re.error as e:
                            QMessageBox.warning(self, "錯誤", f"規則一正規表達式語法錯誤: {e}")
                            return
                else:
                    if compare_col == compare_target:
                        QMessageBox.warning(self, "錯誤", "規則一：欄位比對必須選擇不同的欄位。")
                        return

        # 取得與驗證規則二
        compare_col2 = "none"
        compare_method2 = "完全符合"
        compare_target2 = "manual"
        compare_value2 = ""

        if self.is_dual:
            compare_col2 = self.cmb_compare_col2.currentData()
            compare_method2 = self.cmb_compare_method2.currentText()
            compare_target2 = self.cmb_compare_target2.currentData()
            
            if compare_method2 in ("屬於", "不屬於"):
                compare_value2 = self.cmb_belong_value2.currentText()
            else:
                compare_value2 = self.txt_compare_value2.text()

            if compare_col2 != "none":
                if compare_method2 not in ("屬於", "不屬於"):
                    if compare_target2 == "manual":
                        if compare_method2 == "正規表達式":
                            import re
                            try:
                                re.compile(compare_value2)
                            except re.error as e:
                                QMessageBox.warning(self, "錯誤", f"規則二正規表達式語法錯誤: {e}")
                                return
                    else:
                        if compare_col2 == compare_target2:
                            QMessageBox.warning(self, "錯誤", "規則二：欄位比對必須選擇不同的欄位。")
                            return

        filter_config = {
            "is_dual": self.is_dual,
            "op": "AND" if self.rbtn_and.isChecked() else "OR",
            "rule1": {
                "compare_col": compare_col,
                "compare_method": compare_method,
                "compare_target": compare_target,
                "compare_value": compare_value
            },
            "rule2": {
                "compare_col": compare_col2,
                "compare_method": compare_method2,
                "compare_target": compare_target2,
                "compare_value": compare_value2
            }
        }
        self.request_filter.emit(filter_config)

    def set_enabled(self, enabled):
        self.cmb_compare_col.setEnabled(enabled)
        self.cmb_compare_method.setEnabled(enabled)
        self.cmb_compare_target.setEnabled(enabled)
        self.txt_compare_value.setEnabled(enabled)
        self.cmb_compare_col2.setEnabled(enabled)
        self.cmb_compare_method2.setEnabled(enabled)
        self.cmb_compare_target2.setEnabled(enabled)
        self.txt_compare_value2.setEnabled(enabled)
        self.btn_toggle_rule.setEnabled(enabled)
        self.btn_swap_rules.setEnabled(enabled)
        self.rbtn_and.setEnabled(enabled)
        self.rbtn_or.setEnabled(enabled)
        self.btn_start_filter.setEnabled(enabled)

    def swap_rules(self):
        # 暫時阻擋訊號以避免頻繁觸發 UI 重繪與顯示隱藏邏輯
        self.cmb_compare_col.blockSignals(True)
        self.cmb_compare_method.blockSignals(True)
        self.cmb_compare_target.blockSignals(True)
        self.cmb_belong_value.blockSignals(True)
        self.cmb_compare_col2.blockSignals(True)
        self.cmb_compare_method2.blockSignals(True)
        self.cmb_compare_target2.blockSignals(True)
        self.cmb_belong_value2.blockSignals(True)
        
        # 讀取規則一的值
        col1 = self.cmb_compare_col.currentIndex()
        method1 = self.cmb_compare_method.currentIndex()
        method1_text = self.cmb_compare_method.currentText()
        target1 = self.cmb_compare_target.currentIndex()
        val1 = self.txt_compare_value.text()
        belong1_idx = self.cmb_belong_value.currentIndex()
        
        # 讀取規則二的值
        col2 = self.cmb_compare_col2.currentIndex()
        method2 = self.cmb_compare_method2.currentIndex()
        method2_text = self.cmb_compare_method2.currentText()
        target2 = self.cmb_compare_target2.currentIndex()
        val2 = self.txt_compare_value2.text()
        belong2_idx = self.cmb_belong_value2.currentIndex()
        
        # 將規則一設定為規則二的值
        self.cmb_compare_col.setCurrentIndex(col2)
        self.cmb_compare_method.setCurrentIndex(method2)
        self.update_target_options(self.cmb_compare_method, self.cmb_compare_target, self.num_cols, self.headers)
        self.cmb_compare_target.setCurrentIndex(target2)
        self.update_belong_visibility(self.cmb_compare_method, self.cmb_compare_target, self.value_container, self.belong_container, self.cmb_belong_value)
        if method2_text in ("屬於", "不屬於"):
            self.cmb_belong_value.setCurrentIndex(belong2_idx)
        else:
            self.txt_compare_value.setText(val2)
        
        # 將規則二設定為規則一的值
        self.cmb_compare_col2.setCurrentIndex(col1)
        self.cmb_compare_method2.setCurrentIndex(method1)
        self.update_target_options(self.cmb_compare_method2, self.cmb_compare_target2, self.num_cols, self.headers)
        self.cmb_compare_target2.setCurrentIndex(target1)
        self.update_belong_visibility(self.cmb_compare_method2, self.cmb_compare_target2, self.value_container2, self.belong_container2, self.cmb_belong_value2)
        if method1_text in ("屬於", "不屬於"):
            self.cmb_belong_value2.setCurrentIndex(belong1_idx)
        else:
            self.txt_compare_value2.setText(val1)
        
        # 解除訊號阻擋
        self.cmb_compare_col.blockSignals(False)
        self.cmb_compare_method.blockSignals(False)
        self.cmb_compare_target.blockSignals(False)
        self.cmb_belong_value.blockSignals(False)
        self.cmb_compare_col2.blockSignals(False)
        self.cmb_compare_method2.blockSignals(False)
        self.cmb_compare_target2.blockSignals(False)
        self.cmb_belong_value2.blockSignals(False)
        
        # 手動觸發一次顯示/隱藏更新
        self.on_compare_col_changed(self.cmb_compare_col.currentIndex())
        self.on_compare_col2_changed(self.cmb_compare_col2.currentIndex())

    def get_config(self) -> dict:
        return {
            "is_dual": self.is_dual,
            "op": "AND" if self.rbtn_and.isChecked() else "OR",
            "rule1": {
                "compare_col": self.cmb_compare_col.currentIndex(),
                "compare_method": self.cmb_compare_method.currentIndex(),
                "compare_target": self.cmb_compare_target.currentIndex(),
                "compare_value": self.cmb_belong_value.currentText() if self.cmb_compare_method.currentText() in ("屬於", "不屬於") else self.txt_compare_value.text(),
                "belong_value_idx": self.cmb_belong_value.currentIndex()
            },
            "rule2": {
                "compare_col": self.cmb_compare_col2.currentIndex(),
                "compare_method": self.cmb_compare_method2.currentIndex(),
                "compare_target": self.cmb_compare_target2.currentIndex(),
                "compare_value": self.cmb_belong_value2.currentText() if self.cmb_compare_method2.currentText() in ("屬於", "不屬於") else self.txt_compare_value2.text(),
                "belong_value_idx": self.cmb_belong_value2.currentIndex()
            }
        }

    def set_config(self, config: dict):
        if not config:
            return
        
        is_dual = config.get("is_dual", False)
        self.set_dual_state(is_dual)

        op = config.get("op", "AND")
        if op == "AND":
            self.rbtn_and.setChecked(True)
        else:
            self.rbtn_or.setChecked(True)

        # 暫時阻擋訊號
        self.cmb_compare_col.blockSignals(True)
        self.cmb_compare_method.blockSignals(True)
        self.cmb_compare_target.blockSignals(True)
        self.cmb_belong_value.blockSignals(True)
        self.cmb_compare_col2.blockSignals(True)
        self.cmb_compare_method2.blockSignals(True)
        self.cmb_compare_target2.blockSignals(True)
        self.cmb_belong_value2.blockSignals(True)

        rule1 = config.get("rule1", {})
        if "compare_col" in rule1:
            self.cmb_compare_col.setCurrentIndex(rule1["compare_col"])
        if "compare_method" in rule1:
            self.cmb_compare_method.setCurrentIndex(rule1["compare_method"])
        
        # 依據恢復的比對方式更新比對目標的下拉選單選項
        self.update_target_options(self.cmb_compare_method, self.cmb_compare_target, self.num_cols, self.headers)
        
        if "compare_target" in rule1:
            self.cmb_compare_target.setCurrentIndex(rule1["compare_target"])
            
        # 更新屬於下拉選單的選項與顯示狀態
        self.update_belong_visibility(self.cmb_compare_method, self.cmb_compare_target, self.value_container, self.belong_container, self.cmb_belong_value)
        
        if self.cmb_compare_method.currentText() in ("屬於", "不屬於"):
            if "belong_value_idx" in rule1:
                self.cmb_belong_value.setCurrentIndex(rule1["belong_value_idx"])
        else:
            if "compare_value" in rule1:
                self.txt_compare_value.setText(rule1["compare_value"])

        rule2 = config.get("rule2", {})
        if "compare_col" in rule2:
            self.cmb_compare_col2.setCurrentIndex(rule2["compare_col"])
        if "compare_method" in rule2:
            self.cmb_compare_method2.setCurrentIndex(rule2["compare_method"])
            
        self.update_target_options(self.cmb_compare_method2, self.cmb_compare_target2, self.num_cols, self.headers)
            
        if "compare_target" in rule2:
            self.cmb_compare_target2.setCurrentIndex(rule2["compare_target"])
            
        self.update_belong_visibility(self.cmb_compare_method2, self.cmb_compare_target2, self.value_container2, self.belong_container2, self.cmb_belong_value2)
        
        if self.cmb_compare_method2.currentText() in ("屬於", "不屬於"):
            if "belong_value_idx" in rule2:
                self.cmb_belong_value2.setCurrentIndex(rule2["belong_value_idx"])
        else:
            if "compare_value" in rule2:
                self.txt_compare_value2.setText(rule2["compare_value"])

        # 解除訊號阻擋
        self.cmb_compare_col.blockSignals(False)
        self.cmb_compare_method.blockSignals(False)
        self.cmb_compare_target.blockSignals(False)
        self.cmb_belong_value.blockSignals(False)
        self.cmb_compare_col2.blockSignals(False)
        self.cmb_compare_method2.blockSignals(False)
        self.cmb_compare_target2.blockSignals(False)
        self.cmb_belong_value2.blockSignals(False)
        
        # 手動觸發一次顯示/隱藏更新
        self.on_compare_col_changed(self.cmb_compare_col.currentIndex())
        self.on_compare_col2_changed(self.cmb_compare_col2.currentIndex())

    def get_start_button_text(self, state: str) -> str:
        if state == "critical":
            return "停止載入"
        elif state == "disabled":
            return "正在停止..."
        return "載入"

    def handle_start_button_click(self, main_window, state: str):
        if state == "critical":
            main_window.cancel_task()
        else:
            main_window.start_task()

    # ----------------- 新增輔助方法 -----------------
    def on_compare_method_changed(self, idx):
        self.update_target_options(self.cmb_compare_method, self.cmb_compare_target, self.num_cols, self.headers)
        self.update_belong_visibility(self.cmb_compare_method, self.cmb_compare_target, self.value_container, self.belong_container, self.cmb_belong_value)

    def on_compare_method2_changed(self, idx):
        self.update_target_options(self.cmb_compare_method2, self.cmb_compare_target2, self.num_cols, self.headers)
        self.update_belong_visibility(self.cmb_compare_method2, self.cmb_compare_target2, self.value_container2, self.belong_container2, self.cmb_belong_value2)

    def update_target_options(self, cmb_method, cmb_target, num_cols, headers=None):
        cmb_target.blockSignals(True)
        cmb_target.clear()
        method = cmb_method.currentText()
        if method in ("屬於", "不屬於"):
            cmb_target.addItem("語系", "語系")
            cmb_target.addItem("含數字", "含數字")
            cmb_target.addItem("純數字", "純數字")
            cmb_target.addItem("文數字(無符號)", "文數字(無符號)")
            cmb_target.addItem("僅符號", "僅符號")
        else:
            cmb_target.addItem("手動輸入", "manual")
            for i in range(num_cols):
                text = f"{i+1}. {headers[i]}" if headers and i < len(headers) else f"第 {i+1} 欄"
                cmb_target.addItem(text, i)
        cmb_target.blockSignals(False)

    def update_belong_visibility(self, cmb_method, cmb_target, value_container, belong_container, cmb_belong):
        method = cmb_method.currentText()
        if method in ("屬於", "不屬於"):
            value_container.setVisible(False)
            belong_container.setVisible(True)
            
            target = cmb_target.currentData()
            cmb_belong.blockSignals(True)
            cmb_belong.clear()
            if target == "語系":
                cmb_belong.addItems(["中文", "繁體中文", "簡體中文", "日文(通用)", "日文(專字)", "韓文", "英文", "拉丁語系", "其他語系"])
            elif target in ("含數字", "純數字"):
                cmb_belong.addItems(["半形", "全半形", "多國語言"])
            elif target in ("文數字(無符號)", "僅符號"):
                cmb_belong.addItems(["半形", "全半形"])
            cmb_belong.blockSignals(False)
        else:
            belong_container.setVisible(False)
            target = cmb_target.currentData()
            if target == "manual":
                value_container.setVisible(True)
            else:
                value_container.setVisible(False)
