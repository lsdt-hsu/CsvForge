# src/plugin_sdk/panel_base.py
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from plugin_sdk.context import PluginContext
from plugin_sdk.theme import applyTitleLabel, applyHintLabel


class BasePluginPanel(QFrame):
    # ── 統一 Interface 通訊信號 (私有封裝) ──
    # 【專屬授權規定】：LeftPanel 是全系統唯一被授權存取並串接這些私有信號的代理者。
    # 主程式的其他模組（例如 MainWindow、UiStateMixin、WorkerMixin）嚴禁直接觸碰這些以單底線開頭的私有信號。
    # 外掛子類別嚴禁直接呼叫這些私有信號的 emit() 方法，必須統一使用基底類別提供的公開 Wrapper 方法。
    _request_lock_ui = pyqtSignal(bool)
    _progress_updated = pyqtSignal(int, int)
    _status_updated = pyqtSignal(str)
    _log_emitted = pyqtSignal(str, str)
    _request_silent_save = pyqtSignal()
    _task_started = pyqtSignal(str, int, str, bool)
    _task_finished = pyqtSignal(str)

    def __init__(self, parent=None, title_text="", require_data_loading=True, context: PluginContext = None):
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
            applyTitleLabel(self.lbl_title)
            self.main_layout.addWidget(self.lbl_title)
            
        if self.require_data_loading:
            # 3. 建立「尚未載入資料」提示
            self.lbl_no_data = QLabel("尚未載入資料")
            self.lbl_no_data.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            applyHintLabel(self.lbl_no_data)
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
            self.context.csv_data.data_loaded.connect(self.on_csv_data_refreshed)
            self.context.csv_data.header_state_changed.connect(self.on_csv_data_refreshed)

        # 註：初始資料狀態同步改由 LeftPanel 在面板建構完畢後統一呼叫 initialize_panel() 觸發，防止子類別初始化未完成崩潰

    def initialize_panel(self) -> None:
        """
        SDK 標準生命週期方法。由 LeftPanel 在面板初始化完畢後呼叫，以進行初始狀態同步。
        """
        self._on_global_data_loaded()
        if self.context and self.context.is_data_loaded:
            self.on_csv_data_refreshed()

    def _on_global_data_loaded(self) -> None:
        """全域資料載入/解除載入信號的自動響應槽函數"""
        if self.require_data_loading:
            if self.context and self.context.is_data_loaded:
                self.show_controls()
            else:
                self.reset_panel()

    def on_csv_data_refreshed(self) -> None:
        """全域資料載入或標頭狀態變更時，由基底類別自動觸發。子類別可複寫此方法以更新 UI 數據。"""
        pass

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

    # ── 共通輔助與生命週期 Wrapper 方法 ──
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
        """
        請求主程式鎖定或解鎖 UI。
        【重要限制】：此方法僅限於「無背景 Worker，但需要在主線程進行短暫阻塞操作」的輕量任務使用。
        若已呼叫 start_task()，則嚴禁重複呼叫 lock_ui(True)，因為 start_task 內部已隱含全域 UI 鎖定。
        """
        self._request_lock_ui.emit(lock)

    def update_progress(self, current: int, total: int):
        self._progress_updated.emit(current, total)

    def update_status(self, status: str):
        self._status_updated.emit(status)

    def write_log(self, level: str, message: str):
        self._log_emitted.emit(level, message)

    def start_task(self, task_name: str, total: int = 0, initial_log: str = "", prevent_sleep: bool = False):
        """
        通知主程式背景任務開始。
        此公開 Wrapper 會觸發內部的私有信號 _task_started。
        """
        self._task_started.emit(task_name, total, initial_log, prevent_sleep)

    def finish_task(self, status: str):
        """
        通知主程式背景任務結束。
        此公開 Wrapper 會觸發內部的私有信號 _task_finished。
        """
        self._task_finished.emit(status)

    def request_silent_save_action(self):
        """
        向主程式發起靜默存檔請求。
        此公開 Wrapper 會觸發內部的私有信號 _request_silent_save。
        """
        self._request_silent_save.emit()

    def set_enabled(self, enabled: bool) -> None:
        """
        標準的 SDK 生命週期方法，用以配合 UI 鎖定/解鎖狀態。
        子類別可複寫此方法以自訂內部元件的啟用/停用邏輯，但必須調用 super().set_enabled(enabled)。
        """
        # 不要停用整個面板本身以避免子控制項（如開始/停止按鈕）被強制停用
        pass

    def is_task_running(self) -> bool:
        """
        外部防呆介面：查詢該面板背景任務是否仍在運行。
        預設回傳 False。具有背景 Worker 的子類別必須複寫此方法。
        """
        return False

    def cancel_task(self) -> None:
        """
        外部防呆介面：供主程式在取消背景任務時呼叫。
        預設實作無行為 (pass)。具有背景 Worker 的子類別必須複寫此方法以呼叫 Worker 進行取消。
        """
        pass

