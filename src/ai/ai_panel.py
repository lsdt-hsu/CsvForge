import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QPushButton, QFormLayout, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIntValidator, QDoubleValidator

from base_panel import BasePanel
from ai.ai_prompt_widget import AiPromptWidget
from ai.ai_worker import CSVAIWorker
from ai.ai_client import check_ollama_models


class ConnectionTester(QThread):
    """
    ConnectionTester — 非同步測試 Ollama 連線並拉取模型列表。
    """
    success = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            models = check_ollama_models(self.url)
            self.success.emit(models)
        except Exception as e:
            self.failed.emit(str(e))


class AiPanel(BasePanel):
    """
    AiPanel — AI 處理面板。
    
    負責提供 UI 選項、連線測試交互、管理 VRAM 進階保護設定，
    並於啟動處理時建立 CSVAIWorker 背景線程進行運算。

    設計決策（Config 存取方式）：
      本面板採用「直接操作 Config 物件」的方式（資料相依性）。
      當任何 UI 控制項變更時，會透過 _on_field_changed 立即呼叫 save_to_config() 
      更新記憶體中的 Config 物件，並設定 dirty 旗標。
      主程式（MainWindow / SettingsMixin）會控制何時呼叫 SettingsManager.save() 寫入 settings.json。
      這樣設計可確保在任何時刻（如載入新 CSV 等呼叫 restore_from_config 時）記憶體中的 Config 都是最新狀態，
      以避免使用者修改的 UI 設定因還原被舊值覆蓋。
    """
    request_silent_save = pyqtSignal()

    def __init__(self, parent=None, context=None):
        # require_data_loading=True 代表必須在載入 CSV 後才展示控制項
        super().__init__(parent, title_text="AI 批次處理", require_data_loading=True, context=context)
        self.worker = None
        self.tester = None
        
        # 記錄是否已進行過連線測試
        self._has_checked_ai_conn = False
        # 記錄上一次執行連線測試時的後端設定，以避免重複探測
        self._last_checked_service = None
        self._last_checked_url = None
        
        self.init_ui()
        if self.context and self.context.csv_data:
            self.context.csv_data.data_loaded.connect(self.on_csv_data_refreshed)
            self.context.csv_data.header_state_changed.connect(self.on_csv_data_refreshed)

    def on_csv_data_refreshed(self):
        if self.context and self.context.csv_data:
            csv_data = self.context.csv_data
            if csv_data.all_rows:
                if not self.controls_container.isVisible():
                    self.show_controls()
                self.update_column_dropdowns(csv_data.num_cols, csv_data.headers)
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
        lbl_service = QLabel("AI 服務服務：")
        lbl_service.setStyleSheet("color: #c0caf5;")
        self.cb_service = QComboBox()
        self.cb_service.addItems(["Google AI", "Local AI"])
        service_layout.addWidget(lbl_service)
        service_layout.addWidget(self.cb_service)
        self.controls_layout.addLayout(service_layout)

        # 2. Google AI 設定容器
        self.google_widget = QWidget()
        google_layout = QFormLayout(self.google_widget)
        google_layout.setContentsMargins(0, 0, 0, 0)
        google_layout.setSpacing(8)

        lbl_api_key = QLabel("API KEY：")
        lbl_api_key.setStyleSheet("color: #a9b1d6;")
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_api_key.setPlaceholderText("請輸入 Gemini API KEY")
        self.txt_api_key.setStyleSheet("background-color: #1a1b26; color: #c0caf5; border: 1px solid #3b4261; padding: 4px; border-radius: 4px;")
        google_layout.addRow(lbl_api_key, self.txt_api_key)

        lbl_google_model = QLabel("使用模型：")
        lbl_google_model.setStyleSheet("color: #a9b1d6;")
        self.cb_google_model = QComboBox()
        self.cb_google_model.setEditable(True)
        self.cb_google_model.addItems(["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash"])
        self.cb_google_model.setStyleSheet("background-color: #1a1b26; color: #c0caf5; border: 1px solid #3b4261; padding: 4px; border-radius: 4px;")
        google_layout.addRow(lbl_google_model, self.cb_google_model)

        self.controls_layout.addWidget(self.google_widget)

        # 3. Local AI 設定容器
        self.local_widget = QWidget()
        local_layout = QFormLayout(self.local_widget)
        local_layout.setContentsMargins(0, 0, 0, 0)
        local_layout.setSpacing(8)

        lbl_backend = QLabel("後端選擇：")
        lbl_backend.setStyleSheet("color: #a9b1d6;")
        self.cb_local_backend = QComboBox()
        self.cb_local_backend.addItems(["Ollama"])
        self.cb_local_backend.setStyleSheet("background-color: #1a1b26; color: #c0caf5; border: 1px solid #3b4261; padding: 4px; border-radius: 4px;")
        local_layout.addRow(lbl_backend, self.cb_local_backend)

        lbl_url = QLabel("伺服器網址：")
        lbl_url.setStyleSheet("color: #a9b1d6;")
        self.txt_local_url = QLineEdit("http://localhost:11434")
        self.txt_local_url.setStyleSheet("background-color: #1a1b26; color: #c0caf5; border: 1px solid #3b4261; padding: 4px; border-radius: 4px;")
        local_layout.addRow(lbl_url, self.txt_local_url)

        # 連線狀態與測試按鈕
        conn_layout = QHBoxLayout()
        conn_layout.setSpacing(10)
        
        self.btn_test_conn = QPushButton("測試連線")
        self.btn_test_conn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test_conn.setStyleSheet("""
            QPushButton {
                background-color: #3b4261;
                color: #c0caf5;
                border: 1px solid #565f89;
                border-radius: 4px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #565f89;
            }
        """)
        
        # 連線圓點指示燈
        self.lbl_status_dot = QLabel()
        self.lbl_status_dot.setFixedSize(12, 12)
        # 預設為灰色指示燈 (未連線)
        self.lbl_status_dot.setStyleSheet("background-color: #565f89; border-radius: 6px;")
        
        self.lbl_conn_status = QLabel("尚未測試")
        self.lbl_conn_status.setStyleSheet("color: #565f89; font-size: 11px;")
        
        conn_layout.addWidget(self.btn_test_conn)
        conn_layout.addWidget(self.lbl_status_dot)
        conn_layout.addWidget(self.lbl_conn_status)
        conn_layout.addStretch()
        local_layout.addRow("", conn_layout)

        lbl_local_model = QLabel("使用模型：")
        lbl_local_model.setStyleSheet("color: #a9b1d6;")
        self.cb_local_model = QComboBox()
        self.cb_local_model.setStyleSheet("background-color: #1a1b26; color: #c0caf5; border: 1px solid #3b4261; padding: 4px; border-radius: 4px;")
        self.cb_local_model.setPlaceholderText("請點擊測試連線拉取模型")
        local_layout.addRow(lbl_local_model, self.cb_local_model)

        self.controls_layout.addWidget(self.local_widget)

        # 4. 可收合進階設定區塊 (保護 VRAM)
        self.btn_advanced_toggle = QPushButton("▶ 進階設定 (VRAM 防護)")
        self.btn_advanced_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_advanced_toggle.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #bb9af3;
                text-align: left;
                border: none;
                font-weight: bold;
                padding: 4px 0px;
            }
            QPushButton:hover {
                color: #ff9e64;
            }
        """)
        self.controls_layout.addWidget(self.btn_advanced_toggle)

        self.advanced_widget = QWidget()
        advanced_layout = QFormLayout(self.advanced_widget)
        advanced_layout.setContentsMargins(10, 0, 10, 0)
        advanced_layout.setSpacing(6)

        # Context Length (防過大爆 VRAM)
        lbl_ctx = QLabel("最大 Context 長度：")
        lbl_ctx.setStyleSheet("color: #a9b1d6;")
        self.txt_ctx = QLineEdit("4096")
        self.txt_ctx.setValidator(QIntValidator(128, 65536))
        self.txt_ctx.setStyleSheet("background-color: #1a1b26; color: #c0caf5; border: 1px solid #3b4261; padding: 4px; border-radius: 4px;")
        advanced_layout.addRow(lbl_ctx, self.txt_ctx)

        # 創意發散度 (底層對應 LLM temperature，控制隨機性與多樣性)
        lbl_temp = QLabel("創意發散度：")
        lbl_temp.setStyleSheet("color: #a9b1d6;")
        self.txt_temp = QLineEdit("0.7")
        self.txt_temp.setValidator(QDoubleValidator(0.0, 2.0, 2))
        self.txt_temp.setStyleSheet("background-color: #1a1b26; color: #c0caf5; border: 1px solid #3b4261; padding: 4px; border-radius: 4px;")
        advanced_layout.addRow(lbl_temp, self.txt_temp)

        self.advanced_widget.setVisible(False)  # 預設折疊隱藏
        self.controls_layout.addWidget(self.advanced_widget)

        # 分割線
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("background-color: #3b4261;")
        self.controls_layout.addWidget(sep)

        # 5. 嵌入欄位動態映射與 Prompt 輸入區
        self.prompt_widget = AiPromptWidget()
        self.controls_layout.addWidget(self.prompt_widget)

        self.controls_layout.addStretch()

        # 6. 開始 AI 處理按鈕
        self.btn_start = QPushButton("開始 AI 處理")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.controls_layout.addWidget(self.btn_start)

        # --- 事件信號連接 ---
        self.cb_service.currentIndexChanged.connect(self._on_service_combo_changed)
        self.btn_test_conn.clicked.connect(lambda: self.start_connection_test(force=True))
        self.btn_advanced_toggle.clicked.connect(self.toggle_advanced)
        self.btn_start.clicked.connect(self.on_start_clicked)

        # 欄位值變更時自動同步回 Config 記憶體並標記 dirty
        self.cb_service.currentIndexChanged.connect(self._on_field_changed)
        self.txt_api_key.textChanged.connect(self._on_field_changed)
        self.cb_google_model.currentIndexChanged.connect(self._on_field_changed)
        self.cb_google_model.lineEdit().textChanged.connect(self._on_field_changed)
        self.cb_local_backend.currentIndexChanged.connect(self._on_field_changed)
        self.txt_local_url.textChanged.connect(self._on_field_changed)
        self.cb_local_model.currentIndexChanged.connect(self._on_field_changed)
        self.txt_ctx.textChanged.connect(self._on_field_changed)
        self.txt_temp.textChanged.connect(self._on_field_changed)
        self.prompt_widget.cb_target_col.currentIndexChanged.connect(self._on_field_changed)
        self.prompt_widget.txt_prompt.textChanged.connect(self._on_field_changed)

        # 當伺服器網址文字框按 Enter 或編輯完成時，也非同步探測一下
        self.txt_local_url.editingFinished.connect(self.start_connection_test)

    # ── UI 互動 Slot ──────────────────────────────────────────────────────────

    def _on_service_combo_changed(self, index):
        """
        當 AI 服務切換時，動態顯示/隱藏相關輸入區，並於切換至 Local AI 時自動發起連線探測。
        """
        is_google = (self.cb_service.currentText() == "Google AI")
        self.google_widget.setVisible(is_google)
        self.local_widget.setVisible(not is_google)
        
        if not is_google:
            self.start_connection_test()

    def toggle_advanced(self):
        """
        摺疊與收合進階設定區
        """
        visible = not self.advanced_widget.isVisible()
        self.advanced_widget.setVisible(visible)
        self.btn_advanced_toggle.setText("▼ 進階設定 (VRAM 防護)" if visible else "▶ 進階設定 (VRAM 防護)")

    def start_connection_test(self, force=False):
        """
        非同步探測 Local AI (Ollama) Port 是否可用。

        【連線測試防重複機制】：
        若 force=False 且已執行過檢查 (_has_checked_ai_conn == True)，
        僅在當前 AI 服務或網址與上一次檢查不同（即後端變更）時，才發起測試。
        若 force=True（如手動點擊「測試連線」），則強制發起測試。
        """
        if self.cb_service.currentText() == "Google AI":
            return

        # 避免重複測試
        if self.tester and self.tester.isRunning():
            return

        url = self.txt_local_url.text().strip()
        service = self.cb_service.currentText()

        # 判斷是否略過連線測試
        if not force and self._has_checked_ai_conn:
            if service == self._last_checked_service and url == self._last_checked_url:
                return

        if not url:
            self._update_conn_ui(state="failed", msg="網址不能為空")
            return

        self._update_conn_ui(state="connecting")

        # 記錄本次發起測試的後端設定資訊
        self._has_checked_ai_conn = True
        self._last_checked_service = service
        self._last_checked_url = url

        self.tester = ConnectionTester(url)
        self.tester.success.connect(self._on_test_success)
        self.tester.failed.connect(self._on_test_failed)
        self.tester.start()

    def _on_test_success(self, models):
        self._update_conn_ui(state="success")
        # 載入模型到下拉選單
        self.cb_local_model.blockSignals(True)
        current_sel = self.cb_local_model.currentText()
        self.cb_local_model.clear()
        if models:
            self.cb_local_model.addItems(models)
            if current_sel in models:
                self.cb_local_model.setCurrentText(current_sel)
            else:
                self.cb_local_model.setCurrentIndex(0)
        else:
            self.cb_local_model.setPlaceholderText("連線成功但無本機模型")
        self.cb_local_model.blockSignals(False)
        self._mark_dirty()

    def _on_test_failed(self, error_msg):
        # 限制長度避免爆 UI
        err_brief = error_msg[:60] + "..." if len(error_msg) > 60 else error_msg
        self._update_conn_ui(state="failed", msg=err_brief)
        self.cb_local_model.blockSignals(True)
        self.cb_local_model.clear()
        self.cb_local_model.setPlaceholderText("連線失敗")
        self.cb_local_model.blockSignals(False)

    def _update_conn_ui(self, state, msg=""):
        if state == "connecting":
            self.lbl_status_dot.setStyleSheet("background-color: #e0af68; border-radius: 6px;") # 黃燈
            self.lbl_conn_status.setText("連線探測中...")
            self.lbl_conn_status.setStyleSheet("color: #e0af68; font-size: 11px;")
        elif state == "success":
            self.lbl_status_dot.setStyleSheet("background-color: #9ece6a; border-radius: 6px;") # 綠燈
            self.lbl_conn_status.setText("連線成功")
            self.lbl_conn_status.setStyleSheet("color: #9ece6a; font-size: 11px;")
        elif state == "failed":
            self.lbl_status_dot.setStyleSheet("background-color: #f7768e; border-radius: 6px;") # 紅燈
            self.lbl_conn_status.setText(f"失敗: {msg}")
            self.lbl_conn_status.setStyleSheet("color: #f7768e; font-size: 11px;")

    # ── Config 管理 ───────────────────────────────────────────────────────────

    def _mark_dirty(self):
        if self.context:
            cfg = self.context.ai_panel_config
            cfg.dirty = True

    def _on_field_changed(self):
        """
        欄位值變更時的 Slot 函式。

        【設計決策（設定即時同步）】：
        當 UI 控制項變更時，立即呼叫 save_to_config() 將最新值寫入記憶體組態（ai_panel_config），
        並標記 dirty。這可確保記憶體資料即時更新，避免在其他操作（如載入 CSV）
        觸發 restore_from_config() 時，因記憶體仍保留舊資料而被舊設定覆蓋。
        主程式會統一控制硬碟存檔（settings.json）的寫入時機。
        """
        self.save_to_config()
        self._mark_dirty()

    def restore_from_config(self):
        """
        從 AppContext 的 AiPanelConfig 還原元件設定。
        """
        if not self.context:
            return
        
        cfg = self.context.ai_panel_config
        
        # 阻擋所有子控制項的變更訊號，防止在還原過程中因觸發值變更而執行 _on_field_changed()
        # 進而導致以未還原完成的 UI 狀態覆寫記憶體 Config
        self.cb_service.blockSignals(True)
        self.txt_api_key.blockSignals(True)
        self.cb_google_model.blockSignals(True)
        if self.cb_google_model.lineEdit():
            self.cb_google_model.lineEdit().blockSignals(True)
        self.cb_local_backend.blockSignals(True)
        self.txt_local_url.blockSignals(True)
        self.cb_local_model.blockSignals(True)
        self.txt_ctx.blockSignals(True)
        self.txt_temp.blockSignals(True)
        self.prompt_widget.cb_target_col.blockSignals(True)
        self.prompt_widget.txt_prompt.blockSignals(True)
        
        try:
            # AI 服務種類
            idx = self.cb_service.findText(cfg.ai_service)
            if idx != -1:
                self.cb_service.setCurrentIndex(idx)
            
            # Google AI 部分
            self.txt_api_key.setText(cfg.google_api_key)
            self.cb_google_model.setCurrentText(cfg.google_model)
            
            # Local AI 部分
            idx = self.cb_local_backend.findText(cfg.local_backend)
            if idx != -1:
                self.cb_local_backend.setCurrentIndex(idx)
            self.txt_local_url.setText(cfg.local_server_url)
            
            # 填回可能之前存的模型名稱
            if cfg.local_model:
                self.cb_local_model.setCurrentText(cfg.local_model)
                
            # 進階設定部分
            self.txt_ctx.setText(str(cfg.advanced_num_ctx))
            self.txt_temp.setText(str(cfg.advanced_temperature))
            
            # Prompt widget 部分
            self.prompt_widget.set_target_col(cfg.target_col)
            self.prompt_widget.set_prompt(cfg.prompt_template)
            
            # 觸發顯示/隱藏
            self._on_service_combo_changed(self.cb_service.currentIndex())
        finally:
            self.cb_service.blockSignals(False)
            self.txt_api_key.blockSignals(False)
            self.cb_google_model.blockSignals(False)
            if self.cb_google_model.lineEdit():
                self.cb_google_model.lineEdit().blockSignals(False)
            self.cb_local_backend.blockSignals(False)
            self.txt_local_url.blockSignals(False)
            self.cb_local_model.blockSignals(False)
            self.txt_ctx.blockSignals(False)
            self.txt_temp.blockSignals(False)
            self.prompt_widget.cb_target_col.blockSignals(False)
            self.prompt_widget.txt_prompt.blockSignals(False)

    def save_to_config(self):
        """
        將目前 UI 設定存回 AppContext 暫存，等待寫入 settings.json。
        """
        if not self.context:
            return
        cfg = self.context.ai_panel_config
        
        cfg.ai_service = self.cb_service.currentText()
        cfg.google_api_key = self.txt_api_key.text()
        cfg.google_model = self.cb_google_model.currentText()
        
        cfg.local_backend = self.cb_local_backend.currentText()
        cfg.local_server_url = self.txt_local_url.text().strip()
        cfg.local_model = self.cb_local_model.currentText()
        
        # 進階
        try:
            cfg.advanced_num_ctx = int(self.txt_ctx.text())
        except ValueError:
            cfg.advanced_num_ctx = 4096
            
        try:
            cfg.advanced_temperature = float(self.txt_temp.text())
        except ValueError:
            cfg.advanced_temperature = 0.7
            
        cfg.target_col = self.prompt_widget.get_target_col()
        cfg.prompt_template = self.prompt_widget.get_prompt()

    def show_controls(self):
        super().show_controls()
        self.restore_from_config()

    def update_column_dropdowns(self, num_cols, headers):
        """
        當 CSV 載入成功時，由 MainWindow 呼叫，用以更新 PromptWidget 的可用欄位與目標寫回選單。
        """
        self.prompt_widget.update_headers(headers)

    def set_enabled(self, enabled):
        """
        當任務執行中，鎖定所有輸入控制項防呆。
        """
        self.cb_service.setEnabled(enabled)
        self.txt_api_key.setEnabled(enabled)
        self.cb_google_model.setEnabled(enabled)
        self.cb_local_backend.setEnabled(enabled)
        self.txt_local_url.setEnabled(enabled)
        self.cb_local_model.setEnabled(enabled)
        self.btn_test_conn.setEnabled(enabled)
        self.txt_ctx.setEnabled(enabled)
        self.txt_temp.setEnabled(enabled)
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
        # 1. 儲存設定至 config 以取得最新欄位
        self.save_to_config()
        cfg = self.context.ai_panel_config

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

        if is_hdr:
            headers = [str(cell).strip() for cell in all_rows[0]]
        else:
            headers = [str(i + 1) for i in range(len(all_rows[0]))]

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
            temperature=cfg.advanced_temperature
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
            style_disabled = "background-color: #24283b; color: #565f89;"
            self.btn_start.setText("正在停止...")
            self.btn_start.setEnabled(False)
            self.btn_start.setStyleSheet(style_disabled)

    def _on_task_started(self):
        style_critical = "background-color: #f7768e; color: #1a1b26;"
        self.btn_start.setText("停止 AI 處理")
        self.btn_start.setEnabled(True)
        self.btn_start.setStyleSheet(style_critical)
        self.set_enabled(False)

    def _on_task_finished(self):
        self.btn_start.setText("開始 AI 處理")
        self.btn_start.setEnabled(True)
        self.btn_start.setStyleSheet("")
        self.set_enabled(True)
        self.worker = None
        # 自動存檔 (跟 translation 面板行為保持一致)
        self.request_silent_save.emit()

    def _on_task_error(self, err_msg):
        self.btn_start.setText("開始 AI 處理")
        self.btn_start.setEnabled(True)
        self.btn_start.setStyleSheet("")
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
