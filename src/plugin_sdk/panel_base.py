# src/plugin_sdk/panel_base.py
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from plugin_sdk.context import PluginContext
from plugin_sdk.theme import applyTitleLabel, applyHintLabel


class BasePluginPanel(QFrame):
    """
    外掛面板實體層 ── QFrame 的實體載體，負責 UI 骨架與私有信號宣告。

    [服務對象] PyQt 底層框架、UI 佈局系統。
               直接被 plugin_sdk 內部（PluginAPI, PluginHostAdapter）引用，
               不對主程式或外掛開發者直接暴露。

    [職責範圍] 作為 QFrame 的實體載體，負責：
               - 宣告所有私有非同步信號（供 LeftPanel 代理串接）
               - 持有 PluginContext 提供資料存取
               - 建立基礎 UI 骨架（標題、提示、controls_container）
               - 自動實例化 self.api（PluginAPI）供子類別使用
               - 宣告所有 _internal_ 生命週期方法，等待 PluginHostAdapter 轉發

    [存取禁令] 嚴禁主程式（LeftPanel, MainWindow, UiStateMixin 等）
               或外掛子類別直接呼叫此類別的任何 _internal_ 控制方法或私有信號。
               - 主程式應透過 PluginHostAdapter 進行所有控制操作。
               - 外掛子類別應透過 self.api（PluginAPI）進行所有對外通訊。
    """

    # ── 統一 Interface 通訊信號 (私有封裝) ──
    # 【專屬授權規定】：LeftPanel 是全系統唯一被授權存取並串接這些私有信號的代理者。
    # 主程式的其他模組（例如 MainWindow、UiStateMixin、WorkerMixin）嚴禁直接觸碰這些以單底線開頭的私有信號。
    # 外掛子類別嚴禁直接呼叫這些私有信號的 emit() 方法，必須統一使用 self.api 提供的公開 Wrapper 方法。
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

        # 實例化外掛對講機，供子類別透過 self.api 對外通訊。
        # 【設計說明】：self.api 必須在信號宣告與 context 訂閱之後才建立，
        # 因為 PluginAPI 以 weakref.proxy 持有 self，確保信號已就緒。
        from plugin_sdk.plugin_api import PluginAPI
        self.api = PluginAPI(self)

        # 註：初始資料狀態同步改由 PluginHostAdapter.initialize() 觸發，
        # 防止子類別初始化未完成時崩潰。

    # ── 受保護的生命週期鉤子（子類別可 override）────────────────────────────

    def on_csv_data_refreshed(self) -> None:
        """全域資料載入或標頭狀態變更時，由基底類別自動觸發。子類別可複寫此方法以更新 UI 數據。"""
        pass

    # ── 受保護的 UI 輔助方法（子類別可呼叫）────────────────────────────────

    def show_controls(self):
        if self.require_data_loading:
            self.lbl_no_data.setVisible(False)
            self.controls_container.setVisible(True)
            self.empty_spacer.setVisible(False)

    def hide_controls(self):
        if self.require_data_loading:
            self.lbl_no_data.setVisible(True)
            self.controls_container.setVisible(False)
            self.empty_spacer.setVisible(True)

    # ── 真正私有方法（不對任何外部暴露）────────────────────────────────────

    def _on_global_data_loaded(self) -> None:
        """全域資料載入/解除載入信號的自動響應槽函數"""
        if self.require_data_loading:
            if self.context and self.context.is_data_loaded:
                self.show_controls()
            else:
                self.hide_controls()

    # ── _internal_ 生命週期方法（僅供 PluginHostAdapter 轉發呼叫）─────────
    # 【存取禁令】：下列方法不得由主程式的任何模組直接呼叫，
    # 亦不得由外掛子類別直接呼叫。應統一透過 PluginHostAdapter 存取。

    def _internal_initialize(self) -> None:
        """
        SDK 標準生命週期方法。由 PluginHostAdapter.initialize() 轉發呼叫，
        在面板加入 StackedWidget 後觸發一次，進行初始狀態同步。
        """
        self._on_global_data_loaded()
        if self.context and self.context.is_data_loaded:
            self.on_csv_data_refreshed()

    def _internal_get_uuid(self) -> str:
        """
        回傳此面板的唯一識別 UUID 字串。
        子類別必須覆寫此方法（override）。
        """
        raise NotImplementedError("Subclasses must implement _internal_get_uuid")

    def _internal_get_icon(self) -> QIcon:
        """動態生成一個帶有包名縮寫的無邊框、透明背景 QIcon（預設實作）。"""
        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        name = self._internal_get_package_name()
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

    def _internal_get_package_name(self) -> str:
        """
        回傳此 Package 在設定檔中對應的識別名稱（例如 'translate'）。
        子類別必須覆寫此方法（override）。
        """
        raise NotImplementedError("Subclasses must implement _internal_get_package_name")

    def _internal_serialize_config(self) -> dict:
        """
        將此面板當前設定狀態序列化為 dict。
        子類別必須覆寫此方法（override）。
        """
        raise NotImplementedError("Subclasses must implement _internal_serialize_config")

    def _internal_deserialize_config(self, data: dict) -> None:
        """
        接受設定檔資料 dict，並套用/還原面板設定。
        子類別必須覆寫此方法（override）。
        """
        raise NotImplementedError("Subclasses must implement _internal_deserialize_config")

    def _internal_set_enabled(self, enabled: bool) -> None:
        """
        標準的 SDK 生命週期方法，用以配合 UI 鎖定/解鎖狀態。
        子類別可複寫此方法以自訂內部元件的啟用/停用邏輯，
        但必須呼叫 super()._internal_set_enabled(enabled)。
        預設實作不停用整個面板本身，以避免子控制項被強制停用。
        """
        pass

    def _internal_is_task_running(self) -> bool:
        """
        外部防呆介面：查詢該面板背景任務是否仍在運行。
        預設回傳 False。具有背景 Worker 的子類別必須覆寫此方法。
        """
        return False

    def _internal_cancel_task(self) -> None:
        """
        外部防呆介面：供 PluginHostAdapter 在主程式取消背景任務時呼叫。
        預設實作寫入 WARNING 日誌，以提示使用者此外掛尚未支援取消功能，
        避免使用者誤以為程式當機。
        具有背景 Worker 的子類別必須覆寫此方法以呼叫 Worker 進行取消。
        """
        self.api.write_log("WARNING", "此外掛尚未實作取消功能，無法中斷任務。")
