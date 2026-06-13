from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGridLayout, QComboBox, QLineEdit
from PyQt6.QtGui import QIntValidator

class TranslationPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("grpFrame")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        lbl_sec = QLabel("翻譯設定")
        lbl_sec.setObjectName("sectionHeader")
        layout.addWidget(lbl_sec)

        grid = QGridLayout()
        grid.setSpacing(10)

        self.langs = [
            ("en", "en (英文)"),
            ("zh-TW", "zh-TW (繁中)"),
            ("zh-CN", "zh-CN (簡中)"),
            ("ja", "ja (日文)"),
            ("ko", "ko (韓文)"),
        ]

        lbl_src_lang = QLabel("來源語言：")
        self.cb_src_lang = QComboBox()
        for code, name in self.langs:
            self.cb_src_lang.addItem(name, code)
        self.cb_src_lang.setCurrentIndex(0) # 預設英文

        lbl_tgt_lang = QLabel("目標語言：")
        self.cb_tgt_lang = QComboBox()
        for code, name in self.langs:
            self.cb_tgt_lang.addItem(name, code)
        self.cb_tgt_lang.setCurrentIndex(1) # 預設繁中

        # 批次與單筆間隔時間
        lbl_batch_interval = QLabel("批次間隔(秒)：")
        self.txt_batch_interval = QLineEdit("10")
        self.txt_batch_interval.setValidator(QIntValidator(10, 30))

        lbl_single_interval = QLabel("單筆間隔(秒)：")
        self.txt_single_interval = QLineEdit("1")
        self.txt_single_interval.setValidator(QIntValidator(1, 5))

        grid.addWidget(lbl_src_lang, 0, 0)
        grid.addWidget(self.cb_src_lang, 0, 1)
        grid.addWidget(lbl_tgt_lang, 1, 0)
        grid.addWidget(self.cb_tgt_lang, 1, 1)
        grid.addWidget(lbl_batch_interval, 2, 0)
        grid.addWidget(self.txt_batch_interval, 2, 1)
        grid.addWidget(lbl_single_interval, 3, 0)
        grid.addWidget(self.txt_single_interval, 3, 1)

        layout.addLayout(grid)

    def get_src_lang(self):
        return self.cb_src_lang.currentData()

    def get_tgt_lang(self):
        return self.cb_tgt_lang.currentData()

    def get_batch_interval(self):
        try:
            return int(self.txt_batch_interval.text())
        except ValueError:
            return 10

    def get_single_interval(self):
        try:
            return int(self.txt_single_interval.text())
        except ValueError:
            return 1

    def set_src_lang(self, code):
        idx = self.cb_src_lang.findData(code)
        if idx != -1:
            self.cb_src_lang.setCurrentIndex(idx)

    def set_tgt_lang(self, code):
        idx = self.cb_tgt_lang.findData(code)
        if idx != -1:
            self.cb_tgt_lang.setCurrentIndex(idx)

    def set_batch_interval(self, val):
        self.txt_batch_interval.setText(str(val))

    def set_single_interval(self, val):
        self.txt_single_interval.setText(str(val))

    def set_enabled(self, enabled):
        self.cb_src_lang.setEnabled(enabled)
        self.cb_tgt_lang.setEnabled(enabled)
        self.txt_batch_interval.setEnabled(enabled)
        self.txt_single_interval.setEnabled(enabled)
