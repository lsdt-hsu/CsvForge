from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QPushButton, QFormLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIntValidator, QDoubleValidator

from ai.ai_client import check_ollama_models
from plugin_sdk.theme import (
    applyStandardLabelStyle, applyStandardLineEditStyle, 
    applyStandardComboBoxStyle, applyStandardButtonStyle
)


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


class LocalAiWidget(QWidget):
    """
    LocalAiWidget — Local AI 控制區模組。
    
    管理後端選擇、伺服器網址、測試連線與本機模型選擇，
    且併入了進階設定（VRAM 防護、創意發散度）。
    在各數值變更時發出 field_changed 信號。
    """
    field_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tester = None
        self._has_checked_ai_conn = False
        self._last_checked_backend = None
        self._last_checked_url = None
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # 1. 表單佈局：後端、網址、測試按鈕、模型
        form_widget = QWidget()
        local_layout = QFormLayout(form_widget)
        local_layout.setContentsMargins(0, 0, 0, 0)
        local_layout.setSpacing(8)

        lbl_backend = QLabel("後端選擇：")
        applyStandardLabelStyle(lbl_backend)
        self.cb_local_backend = QComboBox()
        applyStandardComboBoxStyle(self.cb_local_backend)
        local_layout.addRow(lbl_backend, self.cb_local_backend)

        lbl_url = QLabel("伺服器網址：")
        applyStandardLabelStyle(lbl_url)
        self.txt_local_url = QLineEdit("http://localhost:11434")
        applyStandardLineEditStyle(self.txt_local_url)
        local_layout.addRow(lbl_url, self.txt_local_url)

        # 連線狀態與測試按鈕
        conn_layout = QHBoxLayout()
        conn_layout.setSpacing(10)
        
        self.btn_test_conn = QPushButton("測試連線")
        self.btn_test_conn.setCursor(Qt.CursorShape.PointingHandCursor)
        applyStandardButtonStyle(self.btn_test_conn)
        
        # 連線圓點指示燈
        self.lbl_status_dot = QLabel()
        self.lbl_status_dot.setFixedSize(12, 12)
        # 預設為灰色指示燈 (未連線)
        self.lbl_status_dot.setStyleSheet("background-color: #565f89; border-radius: 6px;")
        
        self.lbl_conn_status = QLabel("尚未測試")
        applyStandardLabelStyle(self.lbl_conn_status)
        self.lbl_conn_status.setStyleSheet(self.lbl_conn_status.styleSheet() + " font-size: 11px;")
        
        conn_layout.addWidget(self.btn_test_conn)
        conn_layout.addWidget(self.lbl_status_dot)
        conn_layout.addWidget(self.lbl_conn_status)
        conn_layout.addStretch()
        local_layout.addRow("", conn_layout)

        lbl_local_model = QLabel("使用模型：")
        applyStandardLabelStyle(lbl_local_model)
        self.cb_local_model = QComboBox()
        applyStandardComboBoxStyle(self.cb_local_model)
        self.cb_local_model.setPlaceholderText("請點擊測試連線拉取模型")
        local_layout.addRow(lbl_local_model, self.cb_local_model)

        main_layout.addWidget(form_widget)

        # 2. 進階設定按鈕
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
        main_layout.addWidget(self.btn_advanced_toggle)

        # 3. 進階設定容器
        self.advanced_widget = QWidget()
        advanced_layout = QFormLayout(self.advanced_widget)
        advanced_layout.setContentsMargins(10, 0, 10, 0)
        advanced_layout.setSpacing(6)

        # Context Length (防過大爆 VRAM)
        lbl_ctx = QLabel("最大 Context 長度：")
        applyStandardLabelStyle(lbl_ctx)
        self.txt_ctx = QLineEdit("4096")
        self.txt_ctx.setValidator(QIntValidator(128, 65536))
        applyStandardLineEditStyle(self.txt_ctx)
        advanced_layout.addRow(lbl_ctx, self.txt_ctx)

        # 創意發散度
        lbl_temp = QLabel("創意發散度：")
        applyStandardLabelStyle(lbl_temp)
        self.txt_temp = QLineEdit("0.7")
        self.txt_temp.setValidator(QDoubleValidator(0.0, 2.0, 2))
        applyStandardLineEditStyle(self.txt_temp)
        advanced_layout.addRow(lbl_temp, self.txt_temp)

        self.advanced_widget.setVisible(False)  # 預設折疊隱藏
        main_layout.addWidget(self.advanced_widget)

        # --- 事件信號連接 ---
        self.btn_test_conn.clicked.connect(lambda: self.start_connection_test(force=True))
        self.btn_advanced_toggle.clicked.connect(self.toggle_advanced)

        # 當伺服器網址文字框按 Enter 或編輯完成時，也非同步探測一下
        self.txt_local_url.editingFinished.connect(self.start_connection_test)

        # 監聽數值變更信號，向外轉發為 field_changed
        self.cb_local_backend.currentIndexChanged.connect(self.field_changed)
        self.txt_local_url.textChanged.connect(self.field_changed)
        self.cb_local_model.currentIndexChanged.connect(self.field_changed)
        self.txt_ctx.textChanged.connect(self.field_changed)
        self.txt_temp.textChanged.connect(self.field_changed)

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
        """
        if self.tester and self.tester.isRunning():
            return

        url = self.txt_local_url.text().strip()
        backend = self.cb_local_backend.currentText()

        # 判斷是否略過連線測試
        if not force and self._has_checked_ai_conn:
            if backend == self._last_checked_backend and url == self._last_checked_url:
                return

        if not url:
            self._update_conn_ui(state="failed", msg="網址不能為空")
            return

        self._update_conn_ui(state="connecting")

        # 記錄本次發起測試的後端設定資訊
        self._has_checked_ai_conn = True
        self._last_checked_backend = backend
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
        self._update_conn_ui(state="success")
        # 觸發更新
        self.field_changed.emit()

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
            self.lbl_status_dot.setStyleSheet("background-color: #e0af68; border-radius: 6px;")  # 黃燈
            self.lbl_conn_status.setText("連線探測中...")
            self.lbl_conn_status.setStyleSheet("color: #e0af68; font-size: 11px;")
        elif state == "success":
            self.lbl_status_dot.setStyleSheet("background-color: #9ece6a; border-radius: 6px;")  # 綠燈
            self.lbl_conn_status.setText("連線成功")
            self.lbl_conn_status.setStyleSheet("color: #9ece6a; font-size: 11px;")
        elif state == "failed":
            self.lbl_status_dot.setStyleSheet("background-color: #f7768e; border-radius: 6px;")  # 紅燈
            self.lbl_conn_status.setText(f"失敗: {msg}")
            self.lbl_conn_status.setStyleSheet("color: #f7768e; font-size: 11px;")

    def set_enabled(self, enabled):
        self.cb_local_backend.setEnabled(enabled)
        self.txt_local_url.setEnabled(enabled)
        self.cb_local_model.setEnabled(enabled)
        self.btn_test_conn.setEnabled(enabled)
        self.txt_ctx.setEnabled(enabled)
        self.txt_temp.setEnabled(enabled)

    def restore_from_config(self, cfg):
        self.cb_local_backend.blockSignals(True)
        self.txt_local_url.blockSignals(True)
        self.cb_local_model.blockSignals(True)
        self.txt_ctx.blockSignals(True)
        self.txt_temp.blockSignals(True)
        try:
            idx = self.cb_local_backend.findText(cfg.local_backend)
            if idx != -1:
                self.cb_local_backend.setCurrentIndex(idx)
            self.txt_local_url.setText(cfg.local_server_url)
            if cfg.local_model:
                self.cb_local_model.setCurrentText(cfg.local_model)
            self.txt_ctx.setText(str(cfg.advanced_num_ctx))
            self.txt_temp.setText(str(cfg.advanced_temperature))
        finally:
            self.cb_local_backend.blockSignals(False)
            self.txt_local_url.blockSignals(False)
            self.cb_local_model.blockSignals(False)
            self.txt_ctx.blockSignals(False)
            self.txt_temp.blockSignals(False)

    def save_to_config(self, cfg):
        cfg.local_backend = self.cb_local_backend.currentText()
        cfg.local_server_url = self.txt_local_url.text().strip()
        cfg.local_model = self.cb_local_model.currentText()
        try:
            cfg.advanced_num_ctx = int(self.txt_ctx.text())
        except ValueError:
            cfg.advanced_num_ctx = 4096
            
        try:
            cfg.advanced_temperature = float(self.txt_temp.text())
        except ValueError:
            cfg.advanced_temperature = 0.7
