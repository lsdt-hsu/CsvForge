"""
translation_panel.py — 翻譯面板

設計決策（Config 存取方式）：
  本面板採用「直接操作 Config 物件」的方式（資料相依性），
  而非透過 get_config() / set_config() 序列化/反序列化介面（程式流程相依性）。

  程式流程相依性的問題在於：當儲存時機或初始化順序等程式流程被修改時，
  若橋接方法的呼叫端未同步更新，容易造成設定丟失或順序錯誤等難以追蹤的 Bug，
  且難以被靜態分析工具偵測。

  資料相依性（直接依賴 Config 類別的欄位定義）更易於靜態分析，
  欄位變更時編輯器能直接提示錯誤位置。
"""

from dataclasses import dataclass
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QGridLayout, QComboBox, QSlider, QPushButton, QWidget, QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIntValidator
from plugin_sdk.panel_base import BasePluginPanel
from plugin_sdk.theme import applyStandardLabelStyle, applyStandardComboBoxStyle, applyStandardSliderStyle, applyPrimaryButtonStyle

@dataclass
class TranslatePanelConfig:
    dirty: bool = False
    batch_interval: int = 10
    single_interval: float = 1.0
    batch_size: int = 18
    src_lang: str = "ja"
    tgt_lang: str = "zh-TW"
    src_col: int = 0
    tgt_col: int = 1

class TranslationPanel(BasePluginPanel):

    def __init__(self, parent=None, context=None):
        super().__init__(parent, title_text="翻譯", require_data_loading=True, context=context)
        self.config = TranslatePanelConfig()
        
        from translation.csv_translator import CSVTranslator
        self.translator = CSVTranslator(parent=self, context=context)
        self.translator.started.connect(self.on_translator_started)
        self.translator.finished.connect(self.on_translator_finished)
        self.translator.cancelled.connect(self.on_translator_cancelled)
        self.translator.translation_done.connect(self._on_translation_done)
        self.translator.data_changed.connect(self._on_data_changed)
        
        self.init_ui()

    def on_csv_data_refreshed(self):
        if self.context and self.context.is_data_loaded:
            if not self.controls_container.isVisible():
                self.show_controls()
            self.update_column_dropdowns()
        else:
            self.reset_panel()

    def update_column_dropdowns(self):
        if not self.context or not self.context.csv_data:
            return
        csv_data = self.context.csv_data
        limit = max(csv_data.num_cols, self.config.src_col + 1, self.config.tgt_col + 1)
        
        self.txt_src_col.blockSignals(True)
        self.txt_tgt_col.blockSignals(True)
        
        self.txt_src_col.clear()
        self.txt_tgt_col.clear()
        
        for i in range(limit):
            col_name = csv_data.get_column_header(i)
            self.txt_src_col.addItem(col_name, i)
            self.txt_tgt_col.addItem(col_name, i)
            
        self.restore_columns_from_config()
        
        self.txt_src_col.blockSignals(False)
        self.txt_tgt_col.blockSignals(False)

    def restore_columns_from_config(self):
        cfg = self.config
        self.txt_src_col.setCurrentIndex(cfg.src_col)
        self.txt_tgt_col.setCurrentIndex(cfg.tgt_col)


    def _on_translation_done(self):
        self.request_silent_save_action()

    def _on_data_changed(self):
        if self.context and self.context.csv_data:
            self.context.csv_data.set_modified(True)
            self.context.csv_data.data_changed.emit()


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
        applyStandardLabelStyle(lbl_src_lang)
        self.cb_src_lang = QComboBox()
        applyStandardComboBoxStyle(self.cb_src_lang)
        for code, name in self.langs:
            self.cb_src_lang.addItem(name, code)
        self.cb_src_lang.setCurrentIndex(0)

        lbl_tgt_lang = QLabel("目標語言：")
        applyStandardLabelStyle(lbl_tgt_lang)
        self.cb_tgt_lang = QComboBox()
        applyStandardComboBoxStyle(self.cb_tgt_lang)
        for code, name in self.langs:
            self.cb_tgt_lang.addItem(name, code)
        self.cb_tgt_lang.setCurrentIndex(1)

        lbl_src_col = QLabel("來源欄號：")
        applyStandardLabelStyle(lbl_src_col)
        self.txt_src_col = QComboBox()
        applyStandardComboBoxStyle(self.txt_src_col)

        lbl_tgt_col = QLabel("目標欄號：")
        applyStandardLabelStyle(lbl_tgt_col)
        self.txt_tgt_col = QComboBox()
        applyStandardComboBoxStyle(self.txt_tgt_col)

        self.lbl_batch_title = QLabel("批次間隔：10 秒")
        applyStandardLabelStyle(self.lbl_batch_title)
        self.slider_batch_interval = QSlider(Qt.Orientation.Horizontal)
        applyStandardSliderStyle(self.slider_batch_interval)
        self.slider_batch_interval.setRange(10, 30)
        self.slider_batch_interval.setValue(10)
        self.slider_batch_interval.valueChanged.connect(self._on_batch_interval_changed)

        self.lbl_single_title = QLabel("單筆間隔：1.0 秒")
        applyStandardLabelStyle(self.lbl_single_title)
        self.slider_single_interval = QSlider(Qt.Orientation.Horizontal)
        applyStandardSliderStyle(self.slider_single_interval)
        self.slider_single_interval.setRange(2, 10)
        self.slider_single_interval.setValue(2)
        self.slider_single_interval.valueChanged.connect(self._on_single_interval_changed)

        self.lbl_batch_size_title = QLabel("批次筆數：18 筆")
        applyStandardLabelStyle(self.lbl_batch_size_title)
        self.slider_batch_size = QSlider(Qt.Orientation.Horizontal)
        applyStandardSliderStyle(self.slider_batch_size)
        self.slider_batch_size.setRange(10, 20)
        self.slider_batch_size.setValue(18)
        self.slider_batch_size.valueChanged.connect(self._on_batch_size_changed)

        grid.addWidget(lbl_src_lang, 0, 0)
        grid.addWidget(self.cb_src_lang, 0, 1)
        grid.addWidget(lbl_tgt_lang, 1, 0)
        grid.addWidget(self.cb_tgt_lang, 1, 1)
        grid.addWidget(lbl_src_col, 2, 0)
        grid.addWidget(self.txt_src_col, 2, 1)
        grid.addWidget(lbl_tgt_col, 3, 0)
        grid.addWidget(self.txt_tgt_col, 3, 1)
        grid.addWidget(self.lbl_batch_title, 4, 0)
        grid.addWidget(self.slider_batch_interval, 4, 1)
        grid.addWidget(self.lbl_single_title, 5, 0)
        grid.addWidget(self.slider_single_interval, 5, 1)
        grid.addWidget(self.lbl_batch_size_title, 6, 0)
        grid.addWidget(self.slider_batch_size, 6, 1)

        self.controls_layout.addLayout(grid)
        self.controls_layout.addStretch()

        self.btn_start = QPushButton("開始翻譯")
        applyPrimaryButtonStyle(self.btn_start, is_running=False)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self.on_start_clicked)
        self.controls_layout.addWidget(self.btn_start)

        # 連接事件
        self.cb_src_lang.currentIndexChanged.connect(self._on_src_lang_changed)
        self.cb_tgt_lang.currentIndexChanged.connect(self._on_tgt_lang_changed)
        self.txt_src_col.currentIndexChanged.connect(self._on_src_col_changed)
        self.txt_tgt_col.currentIndexChanged.connect(self._on_tgt_col_changed)

    # ── Config 變動事件 Handler ───────────────────────────────────────────────
    # 各控件變動時直接寫入 TranslatePanelConfig，設定 dirty flag。
    # 見模組頂部說明：此為「資料相依性」設計，取代 get_config/set_config 橋接。

    def _on_batch_interval_changed(self, val: int) -> None:
        self.lbl_batch_title.setText(f"批次間隔：{val} 秒")
        self.config.batch_interval = val
        self.config.dirty = True

    def _on_single_interval_changed(self, val: int) -> None:
        seconds = val * 0.5
        self.lbl_single_title.setText(f"單筆間隔：{seconds:.1f} 秒")
        self.config.single_interval = seconds
        self.config.dirty = True

    def _on_batch_size_changed(self, val: int) -> None:
        self.lbl_batch_size_title.setText(f"批次筆數：{val} 筆")
        self.config.batch_size = val
        self.config.dirty = True

    def _on_src_lang_changed(self, idx: int) -> None:
        self.config.src_lang = self.cb_src_lang.currentData()
        self.config.dirty = True

    def _on_tgt_lang_changed(self, idx: int) -> None:
        self.config.tgt_lang = self.cb_tgt_lang.currentData()
        self.config.dirty = True

    def _on_src_col_changed(self, idx: int) -> None:
        val = self.txt_src_col.itemData(idx)
        if val is not None:
            self.config.src_col = val
            self.config.dirty = True

    def _on_tgt_col_changed(self, idx: int) -> None:
        val = self.txt_tgt_col.itemData(idx)
        if val is not None:
            self.config.tgt_col = val
            self.config.dirty = True

    # ── Interface 實作 ────────────────────────────────────────────────────────
    def get_package_name(self) -> str:
        return "translate_panel"

    def get_uuid(self) -> str:
        return "c7a10787-8df1-4340-974a-4e6f47721867"

    def run_main_action(self) -> None:
        self.on_start_clicked()

    def serialize_config(self) -> dict:
        cfg = self.config
        return {
            "batch_interval": cfg.batch_interval,
            "single_interval": cfg.single_interval,
            "batch_size": cfg.batch_size,
            "src_lang": cfg.src_lang,
            "tgt_lang": cfg.tgt_lang,
            "src_col": cfg.src_col,
            "tgt_col": cfg.tgt_col,
        }

    def deserialize_config(self, data: dict) -> None:
        cfg = self.config
        cfg.batch_interval = data.get("batch_interval", 10)
        cfg.single_interval = data.get("single_interval", 1.0)
        cfg.batch_size = data.get("batch_size", 18)
        cfg.src_lang = data.get("src_lang", "ja")
        cfg.tgt_lang = data.get("tgt_lang", "zh-TW")
        cfg.src_col = int(data.get("src_col", 0))
        cfg.tgt_col = int(data.get("tgt_col", 1))
        self.restore_from_config()

    # ── Config 還原 ───────────────────────────────────────────────────────────

    def restore_from_config(self) -> None:
        """
        從自帶的 TranslatePanelConfig 還原面板設定。
        在 show_controls() 首次被呼叫後執行（即首次載入 CSV 後），確保只還原一次。
        """
        cfg = self.config

        # blockSignals 避免還原過程觸發 _on_xxx_changed 誤設 dirty flag
        self.slider_batch_interval.blockSignals(True)
        self.slider_single_interval.blockSignals(True)
        self.slider_batch_size.blockSignals(True)
        self.cb_src_lang.blockSignals(True)
        self.cb_tgt_lang.blockSignals(True)
        self.txt_src_col.blockSignals(True)
        self.txt_tgt_col.blockSignals(True)

        try:
            self.slider_batch_interval.setValue(int(cfg.batch_interval))
            self.lbl_batch_title.setText(f"批次間隔：{int(cfg.batch_interval)} 秒")

            slider_val = max(2, min(10, int(round(cfg.single_interval / 0.5))))
            self.slider_single_interval.setValue(slider_val)
            self.lbl_single_title.setText(f"單筆間隔：{cfg.single_interval:.1f} 秒")

            self.slider_batch_size.setValue(int(cfg.batch_size))
            self.lbl_batch_size_title.setText(f"批次筆數：{int(cfg.batch_size)} 筆")

            idx = self.cb_src_lang.findData(cfg.src_lang)
            if idx != -1:
                self.cb_src_lang.setCurrentIndex(idx)

            idx = self.cb_tgt_lang.findData(cfg.tgt_lang)
            if idx != -1:
                self.cb_tgt_lang.setCurrentIndex(idx)

            self.update_column_dropdowns()
        finally:
            self.slider_batch_interval.blockSignals(False)
            self.slider_single_interval.blockSignals(False)
            self.slider_batch_size.blockSignals(False)
            self.cb_src_lang.blockSignals(False)
            self.cb_tgt_lang.blockSignals(False)
            self.txt_src_col.blockSignals(False)
            self.txt_tgt_col.blockSignals(False)

    # ── 便捷讀取方法（供 start_translation_task 使用）────────────────────────

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

    def get_src_col(self) -> int:
        return self.txt_src_col.currentData() if self.txt_src_col.currentData() is not None else 0

    def get_tgt_col(self) -> int:
        return self.txt_tgt_col.currentData() if self.txt_tgt_col.currentData() is not None else 1

    def set_enabled(self, enabled):
        super().set_enabled(enabled)
        self.cb_src_lang.setEnabled(enabled)
        self.cb_tgt_lang.setEnabled(enabled)
        self.slider_batch_interval.setEnabled(enabled)
        self.slider_single_interval.setEnabled(enabled)
        self.slider_batch_size.setEnabled(enabled)
        self.txt_src_col.setEnabled(enabled)
        self.txt_tgt_col.setEnabled(enabled)
        if not self.translator.is_running():
            self.btn_start.setEnabled(enabled)

    def on_start_clicked(self):
        if self.translator.is_running():
            self.translator.cancel_task()
        else:
            self.translator.start_translation_task(
                src_lang=self.get_src_lang(),
                tgt_lang=self.get_tgt_lang(),
                batch_interval=self.get_batch_interval(),
                single_interval=self.get_single_interval(),
                batch_size=self.get_batch_size(),
                src_col=self.get_src_col(),
                tgt_col=self.get_tgt_col()
            )

    def on_translator_started(self):
        self.btn_start.setText("停止翻譯")
        self.btn_start.setEnabled(True)
        applyPrimaryButtonStyle(self.btn_start, is_running=True)
        self.set_enabled(False)
        
        # 通知主程式任務開始
        total = len(self.context.csv_data.get_visible_indices()) if self.context and self.context.csv_data else 0
        self.start_task(
            task_name="翻譯中...",
            total=total,
            initial_log="開始執行 CSV 翻譯...",
            prevent_sleep=True
        )

    def on_translator_finished(self):
        self.btn_start.setText("開始翻譯")
        self.btn_start.setEnabled(True)
        applyPrimaryButtonStyle(self.btn_start, is_running=False)
        self.set_enabled(True)
        
        # 根據 translator 狀態發送結束信號
        status = "error" if self.translator._has_error else "finished"
        self.finish_task(status)

    def on_translator_cancelled(self):
        self.btn_start.setText("開始翻譯")
        self.btn_start.setEnabled(True)
        applyPrimaryButtonStyle(self.btn_start, is_running=False)
        self.set_enabled(True)
        
        self.finish_task("cancelled")

    def is_task_running(self) -> bool:
        return self.translator.is_running()

    def cancel_task(self) -> None:
        if self.translator.is_running():
            self.translator.cancel_task()

