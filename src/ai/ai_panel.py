import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt

from plugin_sdk.panel_base import BasePluginPanel
from plugin_sdk.theme import applyStandardButtonStyle, applyStandardLabelStyle, applyStandardComboBoxStyle
from ai.ai_prompt_widget import AiPromptWidget
from ai.google_ai_widget import GoogleAiWidget
from ai.local_ai_widget import LocalAiWidget
from ai.ai_worker import CSVAIWorker
from ai.ai_config import AiPanelConfig

class AiPanel(BasePluginPanel):
    """
    AiPanel — AI 處理面板。
    
    負責提供 UI 選項、連線測試交互、管理 VRAM 進階設定，
    並於啟動處理時建立 CSVAIWorker 背景線程進行運算。
    """

    def __init__(self, parent=None, context=None):
        # require_data_loading=True 代表必須在載入 CSV 後才展示控制項
        super().__init__(parent, title_text="AI 批次處理", require_data_loading=True, context=context)
        self.config = AiPanelConfig()
        self.worker = None
        
        self.init_ui()
        if self.context and self.context.csv_data:
            self.context.csv_data.data_loaded.connect(self.on_csv_data_refreshed)
            self.context.csv_data.header_state_changed.connect(self.on_csv_data_refreshed)

    def on_csv_data_refreshed(self):
        if self.context and self.context.is_data_loaded:
            if not self.controls_container.isVisible():
                self.show_controls()
            self.update_column_dropdowns(self.context.csv_data.num_cols)
        else:
            self.reset_panel()

    def init_ui(self):
        # 建立 UI 配置
        # 所有控制元件都必須放入 BasePanel 的 self.controls_layout 中
        
        parent_layout = self.controls_layout
        
        self.main_scroll = QScrollArea()
        self.main_scroll.setWidgetResizable(True)
        self.main_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.main_scroll.setStyleSheet("QScrollArea { background-color: transparent; }")
        
        self.main_scroll_content = QWidget()
        self.main_scroll_content.setObjectName("mainScrollContent")
        self.main_scroll_content.setStyleSheet("QWidget#mainScrollContent { background-color: transparent; }")
        
        self.controls_layout = QVBoxLayout(self.main_scroll_content)
        self.controls_layout.setContentsMargins(0, 0, 0, 0)
        self.controls_layout.setSpacing(10)
        
        self.main_scroll.setWidget(self.main_scroll_content)
        parent_layout.addWidget(self.main_scroll)

        # 1. AI 服務選擇
        service_layout = QHBoxLayout()
        lbl_service = QLabel("AI 服務：")
        applyStandardLabelStyle(lbl_service)
        self.cb_service = QComboBox()
        self.cb_service.addItems(["Google AI", "Local AI"])
        applyStandardComboBoxStyle(self.cb_service)
        service_layout.addWidget(lbl_service)
        service_layout.addWidget(self.cb_service)
        self.controls_layout.addLayout(service_layout)

        # 2. Google AI 設定容器
        self.google_widget = GoogleAiWidget()
        self.controls_layout.addWidget(self.google_widget)

        # 3. Local AI 設定容器
        self.local_widget = LocalAiWidget()
        self.controls_layout.addWidget(self.local_widget)

        # 分割線
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("background-color: #3b4261;")
        self.controls_layout.addWidget(sep)

        # 4. 嵌入欄位動態映射與 Prompt 輸入區
        self.prompt_widget = AiPromptWidget()
        self.controls_layout.addWidget(self.prompt_widget)

        self.controls_layout.addStretch()

        # 5. 開始 AI 處理按鈕
        self.btn_start = QPushButton("開始 AI 處理")
        applyStandardButtonStyle(self.btn_start, is_running=False)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.controls_layout.addWidget(self.btn_start)

        # --- 事件信號連接 ---
        self.cb_service.currentIndexChanged.connect(self._on_service_combo_changed)
        self.btn_start.clicked.connect(self.on_start_clicked)

        # 欄位值變更時即時、獨立地同步回 Config 記憶體並標記 dirty
        self.cb_service.currentIndexChanged.connect(self._on_service_changed)
        self.google_widget.field_changed.connect(self._on_google_fields_changed)
        self.local_widget.field_changed.connect(self._on_local_fields_changed)
        self.prompt_widget.cb_target_col.currentIndexChanged.connect(self._on_target_col_changed)
        self.prompt_widget.txt_prompt.textChanged.connect(self._on_prompt_changed)

    # ── UI 互動 Slot ──────────────────────────────────────────────────────────

    def _on_service_combo_changed(self, index):
        """
        當 AI 服務切換時，動態顯示/隱藏相關輸入區，並於切換至 Local AI 時自動發起連線探測。
        """
        is_google = (self.cb_service.currentText() == "Google AI")
        self.google_widget.setVisible(is_google)
        self.local_widget.setVisible(not is_google)
        
        if not is_google:
            self.local_widget.start_connection_test()

    # ── Interface 實作 ────────────────────────────────────────────────────────
    def get_package_name(self) -> str:
        return "ai_panel"

    def get_uuid(self) -> str:
        return "8f521c7d-3047-4929-873b-eb8df0b5c1a7"

    def run_main_action(self) -> None:
        self.on_start_clicked()

    def serialize_config(self) -> dict:
        return self.config.serialize()

    def deserialize_config(self, data: dict) -> None:
        self.config.deserialize(data)
        self.restore_from_config()

    # ── Config 管理 ───────────────────────────────────────────────────────────

    def _mark_dirty(self):
        self.config.dirty = True

    def _on_service_changed(self):
        self.config.ai_service = self.cb_service.currentText()
        self._mark_dirty()
        self._on_service_combo_changed(self.cb_service.currentIndex())

    def _on_google_fields_changed(self):
        self.google_widget.save_to_config(self.config)
        self._mark_dirty()

    def _on_local_fields_changed(self):
        self.local_widget.save_to_config(self.config)
        self._mark_dirty()

    def _on_target_col_changed(self):
        # 只有在已載入資料時，才從選單儲存 target_col。
        # 避免在 clear/addItem 或剛啟動尚未載入資料時，因索引變化而誤將 -1 寫入。
        if self.context and self.context.is_data_loaded:
            self.config.target_col = self.prompt_widget.get_target_col()
            self._mark_dirty()

    def _on_prompt_changed(self):
        self.config.prompt_template = self.prompt_widget.get_prompt()
        self._mark_dirty()

    def restore_from_config(self):
        """
        從自有的 AiPanelConfig 還原元件設定。
        """
        cfg = self.config
        
        self.cb_service.blockSignals(True)
        self.prompt_widget.cb_target_col.blockSignals(True)
        self.prompt_widget.txt_prompt.blockSignals(True)
        
        try:
            # AI 服務種類
            idx = self.cb_service.findText(cfg.ai_service)
            if idx != -1:
                self.cb_service.setCurrentIndex(idx)
            
            # Google AI 部分
            self.google_widget.restore_from_config(cfg)
            
            # Local AI 部分
            self.local_widget.restore_from_config(cfg)
            
            # Prompt widget 部分
            self.prompt_widget.set_prompt(cfg.prompt_template)
            
            num_cols = self.context.csv_data.num_cols if self.context and self.context.csv_data else 0
            self.update_column_dropdowns(num_cols)
            
            # 觸發顯示/隱藏
            self._on_service_combo_changed(self.cb_service.currentIndex())
        finally:
            self.cb_service.blockSignals(False)
            self.prompt_widget.cb_target_col.blockSignals(False)
            self.prompt_widget.txt_prompt.blockSignals(False)

    def update_column_dropdowns(self, num_cols):
        """
        當 CSV 載入成功時，由 MainWindow 呼叫，用以更新 PromptWidget 的可用欄位與目標寫回選單。
        """
        limit = max(num_cols, self.config.target_col + 1)
        self.prompt_widget.cb_target_col.blockSignals(True)
        try:
            self.prompt_widget.update_columns(limit, self.context.csv_data if self.context else None)
            self.prompt_widget.set_target_col(self.config.target_col)
        finally:
            self.prompt_widget.cb_target_col.blockSignals(False)

    def set_enabled(self, enabled):
        """
        當任務執行中，鎖定所有輸入控制項防呆。
        """
        self.cb_service.setEnabled(enabled)
        self.google_widget.set_enabled(enabled)
        self.local_widget.set_enabled(enabled)
        self.prompt_widget.set_enabled(enabled)
        
        if not self.is_running():
            self.btn_start.setEnabled(enabled)
    # ── 背景執行緒控制 ────────────────────────────────────────────────────────

    def is_running(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def on_start_clicked(self):
        """
        開始/停止按鈕點擊處理 Slot。
        """
        if self.is_running():
            self.cancel_task()
            return
            
        self.start_ai_task()

    def start_ai_task(self):
        # 1. 設定即時同步已由各控制項處理，直接讀取當前 config 物件
        cfg = self.config

        # 2. 基本校驗
        if cfg.target_col is None or cfg.target_col < 0:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "參數錯誤", "請選擇輸出欄位！")
            return
        if not cfg.prompt_template:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "參數錯誤", "請輸入 AI 指示詞 (Prompt)！")
            return

        # 3. 獲取當前 CSV headers，點擊開始時才進行欄位正確性檢查
        is_hdr = self.context.csv_data.is_header
        all_rows = self.context.csv_data.all_rows
        if not all_rows:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "資料錯誤", "CSV 資料尚未載入！")
            return

        headers = [self.context.csv_data.get_column_header(i) for i in range(self.context.csv_data.num_cols)]

        # 檢查 3.1: 輸出欄位正確性 (所選欄位索引必須小於當前 CSV 最大欄位數)
        if cfg.target_col >= self.context.csv_data.num_cols:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, 
                "參數錯誤", 
                f"輸出欄號 '{cfg.target_col + 1}' 不存在於目前 CSV 檔案中，請重新選擇！"
            )
            return

        # 檢查 3.2: 檢查 Prompt 中引用的變數欄位是否皆存在
        from ai.ai_utils import extract_referenced_fields
        referenced_fields = extract_referenced_fields(cfg.prompt_template)
        missing_fields = [f for f in referenced_fields if f not in headers]
        if missing_fields:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "參數錯誤",
                f"自訂 Prompt 中引用了不存在於目前 CSV 的欄位：\n"
                f"{', '.join(f'{{{f}}}' for f in missing_fields)}\n\n"
                f"請更正 Prompt 中的變數！"
            )
            return

        if cfg.ai_service == "Google AI" and not cfg.google_api_key:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "參數錯誤", "選擇 Google AI 服務時，API KEY 不能為空！")
            return

        if cfg.ai_service == "Local AI" and not cfg.local_model:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "參數錯誤", "選擇 Local AI 服務時，必須選擇使用的模型！")
            return

        # 4. 取得行索引與資料
        visible_row_indices = self.context.csv_data.get_visible_indices()

        # 4. 實例化 Worker
        self.worker = CSVAIWorker(
            all_rows=all_rows,
            visible_row_indices=visible_row_indices,
            is_header=is_hdr,
            target_col_name=cfg.target_col,
            user_prompt=cfg.prompt_template,
            ai_service=cfg.ai_service.replace(" AI", ""), # 轉成 "Google" 或 "Local"
            google_api_key=cfg.google_api_key,
            google_model=cfg.google_model,
            local_server_url=cfg.local_server_url,
            local_model=cfg.local_model,
            num_ctx=cfg.advanced_num_ctx,
            temperature=cfg.advanced_temperature,
            headers=headers
        )

        # 連接完成與變更信號
        self.worker.finished_successfully.connect(self._on_task_finished)
        self.worker.finished_with_error.connect(self._on_task_error)
        self.worker.data_changed.connect(self._on_data_changed)

        # 請求 MainWindow 啟動 Worker (進行多執行緒控制與鎖定 UI)
        self.request_start_worker.emit(self.worker)
        self._on_task_started()

    def cancel_task(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.btn_start.setText("正在停止...")
            self.btn_start.setEnabled(False)

    def _on_task_started(self):
        self.btn_start.setText("停止 AI 處理")
        self.btn_start.setEnabled(True)
        applyStandardButtonStyle(self.btn_start, is_running=True)
        self.set_enabled(False)

    def _on_task_finished(self):
        self.btn_start.setText("開始 AI 處理")
        self.btn_start.setEnabled(True)
        applyStandardButtonStyle(self.btn_start, is_running=False)
        self.set_enabled(True)
        self.worker = None
        # 自動存檔 (跟 translation 面板行為保持一致)
        self.request_silent_save.emit()

    def _on_task_error(self, err_msg):
        self.btn_start.setText("開始 AI 處理")
        self.btn_start.setEnabled(True)
        applyStandardButtonStyle(self.btn_start, is_running=False)
        self.set_enabled(True)
        self.worker = None

        # 彈出錯誤對話框
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "AI 處理中斷", f"AI 處理過程中發生錯誤：\n{err_msg}")

        # 自動存檔
        self.request_silent_save.emit()

    def _on_data_changed(self):
        # 標記主資料已修改，觸發介面重繪
        if self.context and self.context.csv_data:
            self.context.csv_data.set_modified(True)
            self.context.csv_data.data_changed.emit()
