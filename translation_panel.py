from PyQt6.QtWidgets import QVBoxLayout, QLabel, QGridLayout, QComboBox, QSlider
from PyQt6.QtCore import Qt
from base_panel import BasePanel

class TranslationPanel(BasePanel):
    def __init__(self, parent=None):
        super().__init__(parent)
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

        # 批次與單筆間隔時間 (QSlider 改版)
        self.lbl_batch_title = QLabel("批次間隔：10 秒")
        self.slider_batch_interval = QSlider(Qt.Orientation.Horizontal)
        self.slider_batch_interval.setRange(10, 30)
        self.slider_batch_interval.setValue(10)
        self.slider_batch_interval.valueChanged.connect(self.update_batch_label)

        self.lbl_single_title = QLabel("單筆間隔：1 秒")
        self.slider_single_interval = QSlider(Qt.Orientation.Horizontal)
        self.slider_single_interval.setRange(1, 5)
        self.slider_single_interval.setValue(1)
        self.slider_single_interval.valueChanged.connect(self.update_single_label)

        grid.addWidget(lbl_src_lang, 0, 0)
        grid.addWidget(self.cb_src_lang, 0, 1)
        grid.addWidget(lbl_tgt_lang, 1, 0)
        grid.addWidget(self.cb_tgt_lang, 1, 1)
        grid.addWidget(self.lbl_batch_title, 2, 0)
        grid.addWidget(self.slider_batch_interval, 2, 1)
        grid.addWidget(self.lbl_single_title, 3, 0)
        grid.addWidget(self.slider_single_interval, 3, 1)

        layout.addLayout(grid)
        layout.addStretch()

    def update_batch_label(self, val):
        self.lbl_batch_title.setText(f"批次間隔：{val} 秒")

    def update_single_label(self, val):
        self.lbl_single_title.setText(f"單筆間隔：{val} 秒")

    def get_src_lang(self):
        return self.cb_src_lang.currentData()

    def get_tgt_lang(self):
        return self.cb_tgt_lang.currentData()

    def get_batch_interval(self):
        return self.slider_batch_interval.value()

    def get_single_interval(self):
        return self.slider_single_interval.value()

    def set_src_lang(self, code):
        idx = self.cb_src_lang.findData(code)
        if idx != -1:
            self.cb_src_lang.setCurrentIndex(idx)

    def set_tgt_lang(self, code):
        idx = self.cb_tgt_lang.findData(code)
        if idx != -1:
            self.cb_tgt_lang.setCurrentIndex(idx)

    def set_batch_interval(self, val):
        try:
            self.slider_batch_interval.setValue(int(val))
        except ValueError:
            self.slider_batch_interval.setValue(10)

    def set_single_interval(self, val):
        try:
            self.slider_single_interval.setValue(int(val))
        except ValueError:
            self.slider_single_interval.setValue(1)

    def set_enabled(self, enabled):
        self.cb_src_lang.setEnabled(enabled)
        self.cb_tgt_lang.setEnabled(enabled)
        self.slider_batch_interval.setEnabled(enabled)
        self.slider_single_interval.setEnabled(enabled)

    def validate_additional_inputs(self, ui_instance):
        try:
            src_col = int(ui_instance.txt_src_col.text())
            tgt_col = int(ui_instance.txt_tgt_col.text())
            if src_col < 1 or tgt_col < 1:
                raise ValueError()
        except ValueError:
            return False, "來源列號與目標列號必須是大於或等於 1 的正整數"
        return True, ""
