from PyQt6.QtWidgets import QVBoxLayout, QLabel, QGridLayout, QComboBox, QSlider, QPushButton, QWidget
from PyQt6.QtCore import Qt
from base_panel import BasePanel

class TranslationPanel(BasePanel):
    def __init__(self, parent=None):
        super().__init__(parent, title_text="翻譯", require_data_loading=True)
        self.init_ui()

    def init_ui(self):
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

        self.lbl_single_title = QLabel("單筆間隔：1.0 秒")
        self.slider_single_interval = QSlider(Qt.Orientation.Horizontal)
        self.slider_single_interval.setRange(2, 10)
        self.slider_single_interval.setValue(2)
        self.slider_single_interval.valueChanged.connect(self.update_single_label)

        self.lbl_batch_size_title = QLabel("批次筆數：18 筆")
        self.slider_batch_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_batch_size.setRange(10, 20)
        self.slider_batch_size.setValue(18)
        self.slider_batch_size.valueChanged.connect(self.update_batch_size_label)

        grid.addWidget(lbl_src_lang, 0, 0)
        grid.addWidget(self.cb_src_lang, 0, 1)
        grid.addWidget(lbl_tgt_lang, 1, 0)
        grid.addWidget(self.cb_tgt_lang, 1, 1)
        grid.addWidget(self.lbl_batch_title, 2, 0)
        grid.addWidget(self.slider_batch_interval, 2, 1)
        grid.addWidget(self.lbl_single_title, 3, 0)
        grid.addWidget(self.slider_single_interval, 3, 1)
        grid.addWidget(self.lbl_batch_size_title, 4, 0)
        grid.addWidget(self.slider_batch_size, 4, 1)

        self.controls_layout.addLayout(grid)
        self.controls_layout.addStretch()

        self.btn_start = QPushButton("開始翻譯")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.controls_layout.addWidget(self.btn_start)

    def update_batch_label(self, val):
        self.lbl_batch_title.setText(f"批次間隔：{val} 秒")

    def update_single_label(self, val):
        self.lbl_single_title.setText(f"單筆間隔：{val * 0.5:.1f} 秒")

    def update_batch_size_label(self, val):
        self.lbl_batch_size_title.setText(f"批次筆數：{val} 筆")

    def get_src_lang(self):
        return self.cb_src_lang.currentData()

    def get_tgt_lang(self):
        return self.cb_tgt_lang.currentData()

    def get_batch_interval(self):
        return self.slider_batch_interval.value()

    def get_single_interval(self):
        return self.slider_single_interval.value() * 0.5

    def get_batch_size(self):
        return self.slider_batch_size.value()

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
            self.slider_single_interval.setValue(int(float(val) * 2))
        except (ValueError, TypeError):
            self.slider_single_interval.setValue(2)

    def set_batch_size(self, val):
        try:
            self.slider_batch_size.setValue(int(val))
        except ValueError:
            self.slider_batch_size.setValue(18)

    def set_enabled(self, enabled):
        self.cb_src_lang.setEnabled(enabled)
        self.cb_tgt_lang.setEnabled(enabled)
        self.slider_batch_interval.setEnabled(enabled)
        self.slider_single_interval.setEnabled(enabled)
        self.slider_batch_size.setEnabled(enabled)

    def get_config(self) -> dict:
        return {
            "batch_interval": self.get_batch_interval(),
            "single_interval": self.get_single_interval(),
            "batch_size": self.get_batch_size(),
            "src_lang": self.get_src_lang(),
            "tgt_lang": self.get_tgt_lang()
        }

    def set_config(self, config: dict):
        if not config:
            return
        if "batch_interval" in config:
            self.set_batch_interval(config["batch_interval"])
        if "single_interval" in config:
            self.set_single_interval(config["single_interval"])
        if "batch_size" in config:
            self.set_batch_size(config["batch_size"])
        if "src_lang" in config:
            self.set_src_lang(config["src_lang"])
        if "tgt_lang" in config:
            self.set_tgt_lang(config["tgt_lang"])
