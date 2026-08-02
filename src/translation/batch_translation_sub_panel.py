from dataclasses import dataclass
from PyQt6.QtWidgets import QLabel, QGridLayout, QComboBox, QSlider, QPushButton, QCheckBox
from PyQt6.QtCore import Qt

from plugin_sdk import theme
from edit.base_sub_panel import BaseSubPanel
from translation.csv_translator_worker import CSVTranslatorWorker


@dataclass
class BatchTranslateConfig:
    batch_interval: int = 10
    single_interval: float = 1.0
    batch_size: int = 18
    src_lang: str = "ja"
    tgt_lang: str = "zh-TW"
    src_col: int = 0
    tgt_col: int = 1
    skip_translated: bool = True


class BatchTranslationSubPanel(BaseSubPanel):
    """
    批次翻譯子面板
    承接原 TranslationPanel 之所有批次翻譯介面與 Worker 執行邏輯。
    """

    def __init__(self, api, context, parent=None):
        super().__init__("批次翻譯", api, context, parent)
        self.config = BatchTranslateConfig()
        self._worker = None

        self._setup_ui()

    def _setup_ui(self):
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
        theme.applyStandardLabelStyle(lbl_src_lang)
        self.cb_src_lang = QComboBox()
        theme.applyStandardComboBoxStyle(self.cb_src_lang)
        for code, name in self.langs:
            self.cb_src_lang.addItem(name, code)
        self.cb_src_lang.setCurrentIndex(0)

        lbl_tgt_lang = QLabel("目標語言：")
        theme.applyStandardLabelStyle(lbl_tgt_lang)
        self.cb_tgt_lang = QComboBox()
        theme.applyStandardComboBoxStyle(self.cb_tgt_lang)
        for code, name in self.langs:
            self.cb_tgt_lang.addItem(name, code)
        self.cb_tgt_lang.setCurrentIndex(1)

        lbl_src_col = QLabel("來源欄號：")
        theme.applyStandardLabelStyle(lbl_src_col)
        self.txt_src_col = QComboBox()
        theme.applyStandardComboBoxStyle(self.txt_src_col)

        lbl_tgt_col = QLabel("目標欄號：")
        theme.applyStandardLabelStyle(lbl_tgt_col)
        self.txt_tgt_col = QComboBox()
        theme.applyStandardComboBoxStyle(self.txt_tgt_col)

        self.chk_skip_translated = QCheckBox("略過已翻譯欄位")
        theme.applyStandardCheckBoxStyle(self.chk_skip_translated)
        self.chk_skip_translated.setChecked(True)

        self.lbl_batch_title = QLabel("批次間隔：10 秒")
        theme.applyStandardLabelStyle(self.lbl_batch_title)
        self.lbl_batch_title.setFixedWidth(110)
        self.slider_batch_interval = QSlider(Qt.Orientation.Horizontal)
        theme.applyStandardSliderStyle(self.slider_batch_interval)
        self.slider_batch_interval.setRange(10, 30)
        self.slider_batch_interval.setValue(10)
        self.slider_batch_interval.valueChanged.connect(self._on_batch_interval_changed)

        self.lbl_single_title = QLabel("單筆間隔：1.0 秒")
        theme.applyStandardLabelStyle(self.lbl_single_title)
        self.lbl_single_title.setFixedWidth(110)
        self.slider_single_interval = QSlider(Qt.Orientation.Horizontal)
        theme.applyStandardSliderStyle(self.slider_single_interval)
        self.slider_single_interval.setRange(2, 10)
        self.slider_single_interval.setValue(2)
        self.slider_single_interval.valueChanged.connect(self._on_single_interval_changed)

        self.lbl_batch_size_title = QLabel("批次筆數：18 筆")
        theme.applyStandardLabelStyle(self.lbl_batch_size_title)
        self.lbl_batch_size_title.setFixedWidth(110)
        self.slider_batch_size = QSlider(Qt.Orientation.Horizontal)
        theme.applyStandardSliderStyle(self.slider_batch_size)
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
        grid.addWidget(self.chk_skip_translated, 4, 1)
        grid.addWidget(self.lbl_batch_title, 5, 0)
        grid.addWidget(self.slider_batch_interval, 5, 1)
        grid.addWidget(self.lbl_single_title, 6, 0)
        grid.addWidget(self.slider_single_interval, 6, 1)
        grid.addWidget(self.lbl_batch_size_title, 7, 0)
        grid.addWidget(self.slider_batch_size, 7, 1)

        self.content_layout.addLayout(grid)

        self.btn_start = QPushButton("開始翻譯")
        theme.applyPrimaryButtonStyle(self.btn_start, is_running=False)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self.on_start_clicked)
        self.content_layout.addWidget(self.btn_start)

        # 連接事件
        self.cb_src_lang.currentIndexChanged.connect(self._on_src_lang_changed)
        self.cb_tgt_lang.currentIndexChanged.connect(self._on_tgt_lang_changed)
        self.txt_src_col.currentIndexChanged.connect(self._on_src_col_changed)
        self.txt_tgt_col.currentIndexChanged.connect(self._on_tgt_col_changed)
        self.chk_skip_translated.toggled.connect(self._on_skip_translated_toggled)

    # ── Config 變動事件 Handlers ─────────────────────────────────────────────

    def _on_batch_interval_changed(self, val: int) -> None:
        self.lbl_batch_title.setText(f"批次間隔：{val} 秒")
        self.config.batch_interval = val

    def _on_single_interval_changed(self, val: int) -> None:
        seconds = val * 0.5
        self.lbl_single_title.setText(f"單筆間隔：{seconds:.1f} 秒")
        self.config.single_interval = seconds

    def _on_batch_size_changed(self, val: int) -> None:
        self.lbl_batch_size_title.setText(f"批次筆數：{val} 筆")
        self.config.batch_size = val

    def _on_src_lang_changed(self, idx: int) -> None:
        self.config.src_lang = self.cb_src_lang.currentData()

    def _on_tgt_lang_changed(self, idx: int) -> None:
        self.config.tgt_lang = self.cb_tgt_lang.currentData()

    def _on_src_col_changed(self, idx: int) -> None:
        val = self.txt_src_col.itemData(idx)
        if val is not None:
            self.config.src_col = val

    def _on_tgt_col_changed(self, idx: int) -> None:
        val = self.txt_tgt_col.itemData(idx)
        if val is not None:
            self.config.tgt_col = val

    def _on_skip_translated_toggled(self, checked: bool) -> None:
        self.config.skip_translated = checked

    # ── BaseSubPanel 介面實作 ──────────────────────────────────────────────────

    def get_config(self) -> dict:
        cfg = self.config
        return {
            "batch_interval": cfg.batch_interval,
            "single_interval": cfg.single_interval,
            "batch_size": cfg.batch_size,
            "src_lang": cfg.src_lang,
            "tgt_lang": cfg.tgt_lang,
            "src_col": cfg.src_col,
            "tgt_col": cfg.tgt_col,
            "skip_translated": cfg.skip_translated,
        }

    def restore_config(self, data: dict) -> None:
        if not data:
            return
        cfg = self.config
        cfg.batch_interval = data.get("batch_interval", 10)
        cfg.single_interval = data.get("single_interval", 1.0)
        cfg.batch_size = data.get("batch_size", 18)
        cfg.src_lang = data.get("src_lang", "ja")
        cfg.tgt_lang = data.get("tgt_lang", "zh-TW")
        cfg.src_col = int(data.get("src_col", 0))
        cfg.tgt_col = int(data.get("tgt_col", 1))
        cfg.skip_translated = bool(data.get("skip_translated", True))

        self.slider_batch_interval.blockSignals(True)
        self.slider_single_interval.blockSignals(True)
        self.slider_batch_size.blockSignals(True)
        self.cb_src_lang.blockSignals(True)
        self.cb_tgt_lang.blockSignals(True)
        self.txt_src_col.blockSignals(True)
        self.txt_tgt_col.blockSignals(True)
        self.chk_skip_translated.blockSignals(True)

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

            self.chk_skip_translated.setChecked(cfg.skip_translated)
            self.update_column_dropdowns()
        finally:
            self.slider_batch_interval.blockSignals(False)
            self.slider_single_interval.blockSignals(False)
            self.slider_batch_size.blockSignals(False)
            self.cb_src_lang.blockSignals(False)
            self.cb_tgt_lang.blockSignals(False)
            self.txt_src_col.blockSignals(False)
            self.txt_tgt_col.blockSignals(False)
            self.chk_skip_translated.blockSignals(False)

    def on_data_refreshed(self) -> None:
        self.update_column_dropdowns()

    def update_column_dropdowns(self) -> None:
        if not self.context or not self.context.csv_data:
            return
        csv_data = self.context.csv_data
        limit = max(csv_data.num_cols, self.config.src_col + 1, self.config.tgt_col + 1)

        self.txt_src_col.blockSignals(True)
        self.txt_tgt_col.blockSignals(True)
        try:
            self.txt_src_col.clear()
            self.txt_tgt_col.clear()

            for i in range(limit):
                col_name = csv_data.get_column_header(i)
                self.txt_src_col.addItem(col_name, i)
                self.txt_tgt_col.addItem(col_name, i)

            cfg = self.config
            self.txt_src_col.setCurrentIndex(min(cfg.src_col, self.txt_src_col.count() - 1) if self.txt_src_col.count() > 0 else 0)
            self.txt_tgt_col.setCurrentIndex(min(cfg.tgt_col, self.txt_tgt_col.count() - 1) if self.txt_tgt_col.count() > 0 else 0)
        finally:
            self.txt_src_col.blockSignals(False)
            self.txt_tgt_col.blockSignals(False)

    def set_panel_enabled(self, global_enabled: bool) -> None:
        self.cb_src_lang.setEnabled(global_enabled)
        self.cb_tgt_lang.setEnabled(global_enabled)
        self.slider_batch_interval.setEnabled(global_enabled)
        self.slider_single_interval.setEnabled(global_enabled)
        self.slider_batch_size.setEnabled(global_enabled)
        self.txt_src_col.setEnabled(global_enabled)
        self.txt_tgt_col.setEnabled(global_enabled)
        self.chk_skip_translated.setEnabled(global_enabled)
        if self._worker is None:
            self.btn_start.setEnabled(global_enabled or self._is_working)

    # ── 便捷讀取方法 ─────────────────────────────────────────────────────────

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

    def get_skip_translated(self) -> bool:
        return self.chk_skip_translated.isChecked()

    # ── 任務執行與 Worker 控制 ────────────────────────────────────────────────

    def _on_translation_done(self):
        self.api.request_silent_save()

    def _on_data_changed(self):
        if self.context and self.context.csv_data:
            self.context.csv_data.set_modified(True)
            self.context.csv_data.data_changed.emit()

    def on_start_clicked(self):
        if self._is_working and self._worker is not None:
            self._worker.cancel()
            self.btn_start.setText("正在停止...")
            self.btn_start.setEnabled(False)
            return
        self._start_translation_task()

    def _start_translation_task(self) -> None:
        if not self.context or not self.context.is_data_loaded:
            self.api.write_log("WARNING", "請先載入 CSV 資料")
            self.api.update_status("❌ 參數錯誤：未載入資料")
            return

        src_col = self.get_src_col()
        tgt_col = self.get_tgt_col()

        if src_col == tgt_col:
            self.api.write_log("WARNING", "來源欄位與目標欄位不可相同，請重新選擇。")
            self.api.update_status("❌ 參數錯誤：欄位不可相同")
            return

        visible_row_indices = self.context.csv_data.get_visible_indices()
        all_rows = self.context.csv_data.all_rows
        total = len(visible_row_indices)

        self._worker = CSVTranslatorWorker(
            all_rows=all_rows,
            visible_row_indices=visible_row_indices,
            source_col_idx=src_col,
            target_col_idx=tgt_col,
            source_lang=self.get_src_lang(),
            target_lang=self.get_tgt_lang(),
            batch_interval=self.get_batch_interval(),
            single_interval=self.get_single_interval(),
            batch_size=self.get_batch_size(),
            skip_translated=self.get_skip_translated(),
        )

        self._worker.status_updated.connect(self.api.update_status)
        self._worker.log_emitted.connect(self.api.write_log)
        self._worker.data_changed.connect(self._on_data_changed)
        self._worker.finished.connect(self._on_worker_done)

        self._is_working = True
        self.btn_start.setText("停止翻譯")
        self.btn_start.setEnabled(True)
        theme.applyPrimaryButtonStyle(self.btn_start, is_running=True)
        self.set_panel_enabled(False)

        self.api.run_worker(
            self._worker,
            task_name="翻譯中...",
            total=total,
            initial_log="開始執行 CSV 翻譯...",
            prevent_sleep=True,
        )

    def _on_worker_done(self, status: str) -> None:
        self._is_working = False
        self.btn_start.setText("開始翻譯")
        self.btn_start.setEnabled(True)
        theme.applyPrimaryButtonStyle(self.btn_start, is_running=False)
        self.set_panel_enabled(True)

        if self._worker is not None:
            try:
                self._worker.status_updated.disconnect(self.api.update_status)
            except TypeError:
                pass
            try:
                self._worker.log_emitted.disconnect(self.api.write_log)
            except TypeError:
                pass
            try:
                self._worker.data_changed.disconnect(self._on_data_changed)
            except TypeError:
                pass
            try:
                self._worker.finished.disconnect(self._on_worker_done)
            except TypeError:
                pass

        self._worker = None

        if status in ("finished", "cancelled", "error"):
            self._on_translation_done()
