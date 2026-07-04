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
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QGridLayout, QComboBox, QSlider, QPushButton, QWidget, QLineEdit, QMessageBox
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
        # 當前 Worker 引用（用於按鈕停止判斷）
        self._worker = None
        
        self.init_ui()

    def on_csv_data_refreshed(self):
        if self.context and self.context.is_data_loaded:
            if not self.controls_container.isVisible():
                self.show_controls()
            self.update_column_dropdowns()
        else:
            self.hide_controls()

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
        """翻譯完成後自動静默存檔。"""
        self.api.request_silent_save()

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
    def _internal_get_package_name(self) -> str:
        return "translate_panel"

    def _internal_get_uuid(self) -> str:
        return "c7a10787-8df1-4340-974a-4e6f47721867"

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

    def on_start_clicked(self):
        """開始/停止按鈕點擊處理 Slot。"""
        if self._worker is not None:
            # 任務執行中：請求取消
            self._worker.cancel()
            self.btn_start.setText("正在停止...")
            self.btn_start.setEnabled(False)
            return
        self._start_translation_task()

    def _start_translation_task(self) -> None:
        """執行前驗證並建立譯總 Worker。"""
        cfg = self.config
        src_col = self.get_src_col()
        tgt_col = self.get_tgt_col()

        # 執行前驗證
        if src_col == tgt_col:
            self.api.write_log("WARNING", "來源欄位與目標欄位不可相同，請重新選擇。")
            self.api.update_status("❌ 參數錯誤：欄位不可相同")
            return

        visible_row_indices = self.context.csv_data.get_visible_indices()
        all_rows = self.context.csv_data.all_rows
        total = len(visible_row_indices)

        from translation.csv_translator_worker import CSVTranslatorWorker
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
        )

        # 連接業務信號（面板自身處理的部分）
        self._worker.status_updated.connect(self.api.update_status)
        self._worker.log_emitted.connect(self.api.write_log)
        self._worker.data_changed.connect(self._on_data_changed)
        # 連接完成信號：面板負責更新按鈕狀態與存檔
        self._worker.finished.connect(self._on_worker_done)

        # 更新按鈕狀態
        self.btn_start.setText("停止翻譯")
        self.btn_start.setEnabled(True)
        applyPrimaryButtonStyle(self.btn_start, is_running=True)
        self._internal_set_enabled(False)

        # 委託主程式管理 Thread 生命週期（含 ThrottledProgress、GC、finish_task）
        self.api.run_worker(
            self._worker,
            task_name="翻譯中...",
            total=total,
            initial_log="開始執行 CSV 翻譯...",
            prevent_sleep=True
        )

    def _on_worker_done(self, status: str) -> None:
        """Worker 結束時恢復面板 UI 狀態。由 worker.finished 信號觸發。"""
        self.btn_start.setText("開始翻譯")
        self.btn_start.setEnabled(True)
        applyPrimaryButtonStyle(self.btn_start, is_running=False)
        self._internal_set_enabled(True)
        self._worker = None

        if status == "finished":
            self._on_translation_done()
