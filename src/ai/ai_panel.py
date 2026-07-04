import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QFrame, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt

from plugin_sdk.panel_base import BasePluginPanel
from plugin_sdk.theme import applyStandardLabelStyle, applyStandardComboBoxStyle, applyPrimaryButtonStyle
from ai.ai_prompt_widget import AiPromptWidget
from ai.google_ai_widget import GoogleAiWidget
from ai.local_ai_widget import LocalAiWidget
from ai.ai_worker import CSVAIWorker
from ai.ai_config import AiPanelConfig

class AiPanel(BasePluginPanel):
    """
    AiPanel — AI 處理面板。
    
    負責提供 UI 選項、連線測試交互、管理 VRAM 進階設定，
    並於啟動處理時建立 CSVAIWorker，委託主程式統一管理 QThread 生命週期。
    """

    def __init__(self, parent=None, context=None):
        # require_data_loading=True 代表必須在載入 CSV 後才展示控制項
        super().__init__(parent, title_text="AI 批次處理", require_data_loading=True, context=context)
        self.config = AiPanelConfig()
        self._worker = None  # 當前 Worker 引用（用於按鈕停止判斷）
        
        self.init_ui()

    def on_csv_data_refreshed(self):
        if self.context and self.context.is_data_loaded:
            if not self.controls_container.isVisible():
                self.show_controls()
            self.update_column_dropdowns(self.context.csv_data.num_cols)
        else:
            self.hide_controls()

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
        applyPrimaryButtonStyle(self.btn_start, is_running=False)
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
    def _internal_get_package_name(self) -> str:
        return "ai_panel"

    def _internal_get_uuid(self) -> str:
        return "8f521c7d-3047-4929-873b-eb8df0b5c1a7"

    def _internal_serialize_config(self) -> dict:
        return self.config.serialize()

    def _internal_deserialize_config(self, data: dict) -> None:
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
        if self.context and self.context.is_data_loaded:
            self.config.target_col = self.prompt_widget.get_target_col()
            self._mark_dirty()

    def _on_prompt_changed(self):
        self.config.prompt_template = self.prompt_widget.get_prompt()
        self._mark_dirty()

    def restore_from_config(self):
        """從自有的 AiPanelConfig 還原元件設定。"""
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
        """當 CSV 載入成功時，更新 PromptWidget 的可用欄位與目標寫回選單。"""
        limit = max(num_cols, self.config.target_col + 1)
        self.prompt_widget.cb_target_col.blockSignals(True)
        try:
            self.prompt_widget.update_columns(limit, self.context.csv_data if self.context else None)
            self.prompt_widget.set_target_col(self.config.target_col)
        finally:
            self.prompt_widget.cb_target_col.blockSignals(False)

    def _internal_set_enabled(self, enabled: bool) -> None:
        """當任務執行中，鎖定所有輸入控制項防呆。"""
        self.cb_service.setEnabled(enabled)
        self.google_widget.set_enabled(enabled)
        self.local_widget.set_enabled(enabled)
        self.prompt_widget.set_enabled(enabled)
        if self._worker is None:
            self.btn_start.setEnabled(enabled)

    # ── 任務控制 ──────────────────────────────────────────────────────────────

    def on_start_clicked(self):
        """開始/停止按鈕點擊處理 Slot。"""
        if self._worker is not None:
            # 任務執行中：請求取消（由主程式透過 Adapter 直接呼叫 worker.cancel()）
            self._worker.cancel()
            self.btn_start.setText("正在停止...")
            self.btn_start.setEnabled(False)
            return

        self._start_ai_task()

    def _start_ai_task(self):
        """執行前驗證並啟動 AI 處理任務。"""
        cfg = self.config

        # 基本校驗
        if cfg.target_col is None or cfg.target_col < 0:
            QMessageBox.warning(self, "參數錯誤", "請選擇輸出欄位！")
            return
        if not cfg.prompt_template:
            QMessageBox.warning(self, "參數錯誤", "請輸入 AI 指示詞 (Prompt)！")
            return

        is_hdr = self.context.csv_data.is_header
        all_rows = self.context.csv_data.all_rows
        if not all_rows:
            QMessageBox.warning(self, "資料錯誤", "CSV 資料尚未載入！")
            return

        headers = [self.context.csv_data.get_column_header(i) for i in range(self.context.csv_data.num_cols)]

        if cfg.target_col >= self.context.csv_data.num_cols:
            QMessageBox.warning(
                self, "參數錯誤",
                f"輸出欄號 '{cfg.target_col + 1}' 不存在於目前 CSV 檔案中，請重新選擇！"
            )
            return

        from ai.ai_utils import extract_referenced_fields
        referenced_fields = extract_referenced_fields(cfg.prompt_template)
        missing_fields = [f for f in referenced_fields if f not in headers]
        if missing_fields:
            QMessageBox.warning(
                self, "參數錯誤",
                f"自訂 Prompt 中引用了不存在於目前 CSV 的欄位：\n"
                f"{', '.join(f'{{{f}}}' for f in missing_fields)}\n\n"
                f"請更正 Prompt 中的變數！"
            )
            return

        if cfg.ai_service == "Google AI" and not cfg.google_api_key:
            QMessageBox.warning(self, "參數錯誤", "選擇 Google AI 服務時，API KEY 不能為空！")
            return

        if cfg.ai_service == "Local AI" and not cfg.local_model:
            QMessageBox.warning(self, "參數錯誤", "選擇 Local AI 服務時，必須選擇使用的模型！")
            return

        visible_row_indices = self.context.csv_data.get_visible_indices()
        total = len(visible_row_indices)

        # 建立 Worker
        self._worker = CSVAIWorker(
            all_rows=all_rows,
            visible_row_indices=visible_row_indices,
            is_header=is_hdr,
            target_col_name=cfg.target_col,
            user_prompt=cfg.prompt_template,
            ai_service=cfg.ai_service.replace(" AI", ""),
            google_api_key=cfg.google_api_key,
            google_model=cfg.google_model,
            local_server_url=cfg.local_server_url,
            local_model=cfg.local_model,
            num_ctx=cfg.advanced_num_ctx,
            temperature=cfg.advanced_temperature,
            headers=headers
        )

        # 連接業務信號（面板自身處理的部分）
        self._worker.status_updated.connect(self.api.update_status)
        self._worker.log_emitted.connect(self.api.write_log)
        self._worker.data_changed.connect(self._on_data_changed)
        # 連接完成信號：面板負責更新按鈕狀態
        self._worker.finished.connect(self._on_worker_done)

        # 更新按鈕狀態
        self.btn_start.setText("停止 AI 處理")
        self.btn_start.setEnabled(True)
        applyPrimaryButtonStyle(self.btn_start, is_running=True)
        self._internal_set_enabled(False)

        # 委託主程式管理 Thread 生命週期（含 ThrottledProgress、GC、finish_task）
        self.api.run_worker(
            self._worker,
            task_name="AI 處理中...",
            total=total,
            initial_log="開始執行 CSV AI 處理...",
            prevent_sleep=True
        )

    def _on_worker_done(self, status: str) -> None:
        """Worker 結束時恢復面板 UI 狀態。由 worker.finished 信號觸發。"""
        # 恢復按鈕狀態
        self.btn_start.setText("開始 AI 處理")
        self.btn_start.setEnabled(True)
        applyPrimaryButtonStyle(self.btn_start, is_running=False)
        self._internal_set_enabled(True)

        # 讀取錯誤訊息（Worker 尚未被 deleteLater，此時引用仍有效）
        if status == "error" and self._worker is not None:
            err_msg = getattr(self._worker, "_last_error", "未知錯誤")
            if err_msg:
                QMessageBox.critical(self, "AI 處理中斷", f"AI 處理過程中發生錯誤：\n{err_msg}")

        # 清除本地 Worker 引用（Adapter 端的 GC 清單另行管理）
        self._worker = None

        # 自動存檔
        self.api.request_silent_save()

    def _on_data_changed(self):
        """標記主資料已修改，觸發介面重繪。"""
        if self.context and self.context.csv_data:
            self.context.csv_data.set_modified(True)
            self.context.csv_data.data_changed.emit()
