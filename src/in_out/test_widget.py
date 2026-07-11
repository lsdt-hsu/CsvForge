from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtGui import QIntValidator
from ui_constants import START_BUTTON_MIN_WIDTH

class TestWidget(QWidget):
    def __init__(self, parent=None, start_callback=None):
        super().__init__(parent)
        self.start_callback = start_callback
        self.setObjectName("TestWidget")
        
        # 設定為無框且背景透明
        self.setStyleSheet("#TestWidget { background: transparent; border: none; }")
        
        # 建立 UI 元件
        self.lbl_repeat = QLabel("重複：")
        self.txt_repeat = QLineEdit("1000")
        self.txt_repeat.setValidator(QIntValidator(1, 999999))
        self.txt_repeat.setFixedWidth(60)
        
        self.lbl_repeat_unit = QLabel("次")
        
        self.lbl_delay = QLabel("延遲：")
        self.txt_delay = QLineEdit("2")
        self.txt_delay.setValidator(QIntValidator(1, 999999))
        self.txt_delay.setFixedWidth(40)
        
        self.lbl_delay_unit = QLabel("秒")
        
        self.btn_test = QPushButton("Test")
        self.btn_test.setObjectName("btnTest")
        self.btn_test.setMinimumWidth(START_BUTTON_MIN_WIDTH)
        self.btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test.clicked.connect(self.on_test_clicked)
        
        # 佈局排版
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        layout.addWidget(self.lbl_repeat)
        layout.addWidget(self.txt_repeat)
        layout.addWidget(self.lbl_repeat_unit)
        layout.addSpacing(10)
        layout.addWidget(self.lbl_delay)
        layout.addWidget(self.txt_delay)
        layout.addWidget(self.lbl_delay_unit)
        layout.addSpacing(10)
        layout.addWidget(self.btn_test)
        
        # 計時器與狀態
        self.test_timer = QTimer(self)
        self.test_timer.timeout.connect(self.on_test_timer_timeout)
        self.remaining_repeats = 0
        self.delay_seconds = 2

    def on_test_clicked(self):
        if self.test_timer.isActive():
            self.stop_test()
        else:
            self.start_test()

    def start_test(self):
        # 讀取並防呆設定
        repeat_text = self.txt_repeat.text().strip()
        delay_text = self.txt_delay.text().strip()
        
        repeats = int(repeat_text) if repeat_text else 1000
        self.delay_seconds = int(delay_text) if delay_text else 2
        
        if repeats <= 0:
            repeats = 1000
        if self.delay_seconds <= 0:
            self.delay_seconds = 2
            
        self.remaining_repeats = repeats
        
        # 變更 UI 狀態
        self.txt_repeat.setEnabled(False)
        self.txt_delay.setEnabled(False)
        self.btn_test.setText(f"Stop {self.remaining_repeats}")
        
        # 啟動定時器 (直接設定為 N 秒 timeout)
        self.test_timer.start(self.delay_seconds * 1000)

    def stop_test(self):
        self.test_timer.stop()
        self.txt_repeat.setEnabled(True)
        self.txt_delay.setEnabled(True)
        self.btn_test.setText("Test")

    def on_test_timer_timeout(self):
        # 1. 觸發 callback 以呼叫 btn_start
        if self.start_callback:
            self.start_callback()
            
        # 2. 扣減剩餘次數
        self.remaining_repeats -= 1
        
        # 3. 檢查次數是否歸零
        if self.remaining_repeats <= 0:
            self.stop_test()
        else:
            # 4. 更新按鈕文字
            self.btn_test.setText(f"Stop {self.remaining_repeats}")
