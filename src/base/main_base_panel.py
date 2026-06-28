# src/base/main_base_panel.py
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from common_data.csv_data import CsvData

from common_data.app_context import AppContext


class BasePanel(QFrame):
    # ── 統一 Interface 通訊信號 ──
    request_lock_ui = pyqtSignal(bool)
    progress_updated = pyqtSignal(int, int)
    status_updated = pyqtSignal(str)
    log_emitted = pyqtSignal(str, str)
    request_start_worker = pyqtSignal(object)
    request_silent_save = pyqtSignal()  # 統一的靜默存檔請求

    def __init__(self, parent=None, title_text="", require_data_loading=True, context: AppContext = None):
        super().__init__(parent)
        self.context = context
        self.setObjectName("grpFrame")
        self.require_data_loading = require_data_loading
        
        # 1. 建立主要垂直佈局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(8)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 2. 建立標題
        if title_text:
            self.lbl_title = QLabel(title_text)
            self.lbl_title.setObjectName("sectionHeader")
            self.main_layout.addWidget(self.lbl_title)
            
        if self.require_data_loading:
            # 3. 建立「尚未載入資料」提示
            self.lbl_no_data = QLabel("尚未載入資料")
            self.lbl_no_data.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.lbl_no_data.setStyleSheet("color: #565f89; font-style: italic; margin-top: 5px;")
            self.main_layout.addWidget(self.lbl_no_data)
            
            # 4. 建立供子類別使用的控制項容器與佈局
            self.controls_container = QWidget()
            self.controls_layout = QVBoxLayout(self.controls_container)
            self.controls_layout.setContentsMargins(0, 0, 0, 0)
            self.controls_layout.setSpacing(10)
            self.main_layout.addWidget(self.controls_container, stretch=1)
            
            # 5. 建立動態佔位 Spacer
            self.empty_spacer = QWidget()
            self.main_layout.addWidget(self.empty_spacer, stretch=1)
            
            # 直接設定初始可見性，避免呼叫尚未初始化完成的子類別重置方法
            self.lbl_no_data.setVisible(True)
            self.controls_container.setVisible(False)
            self.empty_spacer.setVisible(True)
        else:
            self.controls_layout = self.main_layout

        # 訂閱全域資料載入信號以自動調整載入/未載入狀態 (解耦設計)
        if self.context and self.context.csv_data:
            self.context.csv_data.data_loaded.connect(self._on_global_data_loaded)

    def _on_global_data_loaded(self) -> None:
        """全域資料載入/解除載入信號的自動響應槽函數"""
        if self.require_data_loading:
            if self.context.is_data_loaded:
                self.show_controls()
            else:
                self.reset_panel()

    # ── 所有 Package 必須實作的 Interface 方法 ──
    def get_uuid(self) -> str:
        """回傳此面板的唯一識別 UUID 字串"""
        raise NotImplementedError("Subclasses must implement get_uuid")

    def get_icon(self) -> QIcon:
        """動態生成一個帶有包名縮寫的無邊框、透明背景 QIcon"""
        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 繪製文字
        name = self.get_package_name()
        short_name = name[:2].upper() if name else "PL"
        
        font = QFont("Arial")
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, short_name)
        painter.end()
        
        icon = QIcon()
        icon.addPixmap(pixmap)
        return icon

    def get_package_name(self) -> str:
        """回傳此 Package 在設定檔中對應的識別名稱 (例如 'translate')"""
        raise NotImplementedError("Subclasses must implement get_package_name")

    def run_main_action(self) -> None:
        """執行該面板的主要功能，例如開始翻譯、開始過濾"""
        pass

    def serialize_config(self) -> dict:
        """將此面板當前設定狀態序列化為 dict"""
        raise NotImplementedError("Subclasses must implement serialize_config")

    def deserialize_config(self, data: dict) -> None:
        """接受設定檔資料 dict，並套用/還原面板設定"""
        raise NotImplementedError("Subclasses must implement deserialize_config")

    # ── 共通輔助方法 ──
    def show_controls(self):
        if self.require_data_loading:
            self.lbl_no_data.setVisible(False)
            self.controls_container.setVisible(True)
            self.empty_spacer.setVisible(False)
        
    def reset_panel(self):
        if self.require_data_loading:
            self.lbl_no_data.setVisible(True)
            self.controls_container.setVisible(False)
            self.empty_spacer.setVisible(True)

    def lock_ui(self, lock: bool):
        self.request_lock_ui.emit(lock)

    def update_progress(self, current: int, total: int):
        self.progress_updated.emit(current, total)

    def update_status(self, status: str):
        self.status_updated.emit(status)

    def write_log(self, level: str, message: str):
        self.log_emitted.emit(level, message)
