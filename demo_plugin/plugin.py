"""
translation_panel.py — 翻譯面板 (外掛版本)

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
from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QGridLayout, QComboBox, QSlider,
    QPushButton, QWidget, QScrollArea
)
from PyQt6.QtCore import Qt

from common_data.task_status import TaskStatus
from plugin_sdk import BasePluginPanel, PluginContext
from plugin_sdk import theme


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


class PanelClass(BasePluginPanel):

    _UUID = "a9b8c7d6-e5f4-3210-fedc-ba9876543210"
    _N_NON_COL_OPTIONS = 0

    def __init__(self, context: PluginContext, parent=None):
        super().__init__(
            parent=parent,
            title_text="翻譯外掛",
            require_data_loading=True,
            context=context
        )
        self.config = TranslatePanelConfig()
        # 當前 Worker 引用（用於按鈕停止判斷）
        self._worker = None
        
        self.init_ui()

    def _ui_to_stored(self, ui_index: int) -> int:
        return ui_index - self._N_NON_COL_OPTIONS

    def _stored_to_ui(self, stored: int) -> int:
        return stored + self._N_NON_COL_OPTIONS

    def on_csv_data_refreshed(self) -> None:
        if not self.context or not self.context.is_data_loaded:
            return
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
                
            self.restore_columns_from_config()
        finally:
            self.txt_src_col.blockSignals(False)
            self.txt_tgt_col.blockSignals(False)

    def restore_columns_from_config(self) -> None:
        cfg = self.config
        
        src_ui = self._stored_to_ui(cfg.src_col)
        max_src_idx = self.txt_src_col.count() - 1
        safe_src_idx = max(0, min(src_ui, max_src_idx)) if max_src_idx >= 0 else 0
        self.txt_src_col.setCurrentIndex(safe_src_idx)
        
        tgt_ui = self._stored_to_ui(cfg.tgt_col)
        max_tgt_idx = self.txt_tgt_col.count() - 1
        safe_tgt_idx = max(0, min(tgt_ui, max_tgt_idx)) if max_tgt_idx >= 0 else 0
        self.txt_tgt_col.setCurrentIndex(safe_tgt_idx)

    def _on_translation_done(self) -> None:
        self.api.request_silent_save()

    def _on_data_changed(self) -> None:
        if self.context and self.context.csv_data:
            self.context.csv_data.set_modified(True)
            self.context.csv_data.data_changed.emit()

    def init_ui(self) -> None:
        # 建立可捲動容器以符合 UI 佈局規範
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 消除 QScrollArea 預設邊框與背景色
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.viewport().setStyleSheet("background: transparent;")

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(10)

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

        self.lbl_batch_title = QLabel("批次間隔：10 秒")
        theme.applyStandardLabelStyle(self.lbl_batch_title)
        self.slider_batch_interval = QSlider(Qt.Orientation.Horizontal)
        theme.applyStandardSliderStyle(self.slider_batch_interval)
        self.slider_batch_interval.setRange(10, 30)
        self.slider_batch_interval.setValue(10)
        self.slider_batch_interval.valueChanged.connect(self._on_batch_interval_changed)

        self.lbl_single_title = QLabel("單筆間隔：1.0 秒")
        theme.applyStandardLabelStyle(self.lbl_single_title)
        self.slider_single_interval = QSlider(Qt.Orientation.Horizontal)
        theme.applyStandardSliderStyle(self.slider_single_interval)
        self.slider_single_interval.setRange(2, 10)
        self.slider_single_interval.setValue(2)
        self.slider_single_interval.valueChanged.connect(self._on_single_interval_changed)

        self.lbl_batch_size_title = QLabel("批次筆數：18 筆")
        theme.applyStandardLabelStyle(self.lbl_batch_size_title)
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
        grid.addWidget(self.lbl_batch_title, 4, 0)
        grid.addWidget(self.slider_batch_interval, 4, 1)
        grid.addWidget(self.lbl_single_title, 5, 0)
        grid.addWidget(self.slider_single_interval, 5, 1)
        grid.addWidget(self.lbl_batch_size_title, 6, 0)
        grid.addWidget(self.slider_batch_size, 6, 1)

        inner_layout.addLayout(grid)
        inner_layout.addStretch()
        scroll.setWidget(inner)

        self.controls_layout.addWidget(scroll)
        self.controls_layout.addStretch()

        self.btn_start = QPushButton("開始翻譯")
        theme.applyPrimaryButtonStyle(self.btn_start, is_running=False)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self.on_start_clicked)
        self.controls_layout.addWidget(self.btn_start)

        # 連接事件
        self.cb_src_lang.currentIndexChanged.connect(self._on_src_lang_changed)
        self.cb_tgt_lang.currentIndexChanged.connect(self._on_tgt_lang_changed)
        self.txt_src_col.currentIndexChanged.connect(self._on_src_col_changed)
        self.txt_tgt_col.currentIndexChanged.connect(self._on_tgt_col_changed)

    # ── Config 變動事件 Handler ───────────────────────────────────────────────
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
        if idx >= 0:
            self.config.src_lang = self.cb_src_lang.itemData(idx)
            self.config.dirty = True

    def _on_tgt_lang_changed(self, idx: int) -> None:
        if idx >= 0:
            self.config.tgt_lang = self.cb_tgt_lang.itemData(idx)
            self.config.dirty = True

    def _on_src_col_changed(self, idx: int) -> None:
        if idx >= 0:
            self.config.src_col = self._ui_to_stored(idx)
            self.config.dirty = True

    def _on_tgt_col_changed(self, idx: int) -> None:
        if idx >= 0:
            self.config.tgt_col = self._ui_to_stored(idx)
            self.config.dirty = True

    # ── Interface 實作 ────────────────────────────────────────────────────────
    def _internal_get_package_name(self) -> str:
        return "translation2"

    def _internal_get_uuid(self) -> str:
        return self._UUID

    def _internal_serialize_config(self) -> dict:
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

    def _internal_deserialize_config(self, data: dict) -> None:
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
        cfg = self.config

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

    def _internal_set_enabled(self, enabled: bool) -> None:
        super()._internal_set_enabled(enabled)
        self.cb_src_lang.setEnabled(enabled)
        self.cb_tgt_lang.setEnabled(enabled)
        self.slider_batch_interval.setEnabled(enabled)
        self.slider_single_interval.setEnabled(enabled)
        self.slider_batch_size.setEnabled(enabled)
        self.txt_src_col.setEnabled(enabled)
        self.txt_tgt_col.setEnabled(enabled)
        # 按鈕在任務執行中不停用（供使用者點擊停止）
        if self._worker is None:
            self.btn_start.setEnabled(enabled)

    def on_start_clicked(self) -> None:
        """開始/停止按鈕點擊處理 Slot。"""
        if self._worker is not None:
            # 任務執行中：請求取消
            self._worker.cancel()
            self.btn_start.setText("正在停止...")
            self.btn_start.setEnabled(False)
            return
        self._start_translation_task()

    def _start_translation_task(self) -> None:
        """執行前驗證並建立翻譯 Worker。"""
        src_col = self.get_src_col()
        tgt_col = self.get_tgt_col()

        # 執行前驗證：欄位不可相同
        if src_col == tgt_col:
            self.api.write_log("WARNING", "來源欄位與目標欄位不可相同，請重新選擇。")
            self.api.update_status("❌ 參數錯誤：欄位不可相同")
            return

        # 執行前驗證：邊界檢查
        num_cols = self.context.csv_data.num_cols
        if src_col < 0 or src_col >= num_cols:
            self.api.write_log("WARNING", f"來源欄位索引 {src_col} 超出資料範圍（共 {num_cols} 欄）。")
            self.api.update_status("❌ 參數錯誤：欄位索引超出範圍")
            return

        if tgt_col < 0 or tgt_col >= num_cols:
            self.api.write_log("WARNING", f"目標欄位索引 {tgt_col} 超出資料範圍（共 {num_cols} 欄）。")
            self.api.update_status("❌ 參數錯誤：欄位索引超出範圍")
            return

        visible_row_indices = self.context.csv_data.get_visible_indices()
        all_rows = self.context.csv_data.all_rows
        total = len(visible_row_indices)

        from worker import PluginWorker
        self._worker = PluginWorker(
            all_rows=all_rows,
            visible_row_indices=visible_row_indices,
            source_col_idx=src_col,
            target_col_idx=tgt_col,
            source_lang=self.get_src_lang(),
            target_lang=self.get_tgt_lang(),
            batch_interval=self.get_batch_interval(),
            single_interval=self.get_single_interval(),
            batch_size=self.get_batch_size(),
        )

        # 連接業務信號
        self._worker.status_updated.connect(self.api.update_status)
        self._worker.log_emitted.connect(self.api.write_log)
        self._worker.data_changed.connect(self._on_data_changed)
        self._worker.finished.connect(self._on_worker_done)

        # 更新按鈕狀態
        self.btn_start.setText("停止翻譯")
        self.btn_start.setEnabled(True)
        theme.applyPrimaryButtonStyle(self.btn_start, is_running=True)
        self._internal_set_enabled(False)

        # 委託主程式管理 Thread 生命週期
        self.api.run_worker(
            self._worker,
            task_name="翻譯中...",
            total=total,
            initial_log="開始執行 CSV 翻譯...",
            prevent_sleep=True
        )

    def _on_worker_done(self, status: TaskStatus) -> None:
        """Worker 結束時恢復面板 UI 狀態。由 worker.finished 信號觸發。"""
        self.btn_start.setText("開始翻譯")
        self.btn_start.setEnabled(True)
        theme.applyPrimaryButtonStyle(self.btn_start, is_running=False)
        self._internal_set_enabled(True)
        self._worker = None

        # 不論任務執行狀態如何，皆自動存檔已翻譯部分
        self._on_translation_done()
