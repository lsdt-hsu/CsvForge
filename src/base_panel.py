from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt, pyqtSignal

from settings_manager import (
    WindowConfig, MainConfig, IoPanelConfig, DataEditorConfig,
    StatusPanelConfig, TranslatePanelConfig, FilterPanelConfig,
    SidePanelConfig, AiPanelConfig,
)


class AppContext:
    """
    AppContext — 封裝主畫面的動態設定與狀態，提供子面板存取。

    Config 物件存取：
      各面板可透過 xxx_config property 讀取任何一個組態，但每個組態只應被
      一個特定模組寫入（見各 Config dataclass 的 docstring）。

    動態狀態存取：
      source_path、output_path 等執行時動態值仍透過存取器半直接取得
      各編輯框的最新值，而非從 io_panel_config 讀取。
      IoPanelConfig 僅作為 IO Panel 控件的初始預設值來源。
    """

    def __init__(self, main_window):
        self._win = main_window

    # ── Config 物件存取 ───────────────────────────────────────────────────────

    @property
    def window_config(self) -> WindowConfig:
        return self._win._configs["window"]

    @property
    def main_config(self) -> MainConfig:
        return self._win._configs["main"]

    @property
    def io_panel_config(self) -> IoPanelConfig:
        return self._win._configs["io_panel"]

    @property
    def side_panel_config(self) -> SidePanelConfig:
        return self._win._configs["side_panel"]

    @property
    def data_editor_config(self) -> DataEditorConfig:
        return self._win._configs["data_editor_panel"]

    @property
    def status_panel_config(self) -> StatusPanelConfig:
        return self._win._configs["status_panel"]

    @property
    def translate_panel_config(self) -> TranslatePanelConfig:
        return self._win._configs["translate_panel"]

    @property
    def filter_panel_config(self) -> FilterPanelConfig:
        return self._win._configs["filter_panel"]

    @property
    def ai_panel_config(self) -> AiPanelConfig:
        return self._win._configs["ai_panel"]

    # ── 執行時動態狀態存取（半直接存取 Widget 最新值）────────────────────────

    @property
    def source_path(self) -> str:
        return self._win.io_panel.txt_src_path.text().strip()

    @property
    def output_path(self) -> str:
        return self._win.io_panel.txt_out_path.text().strip()

    @property
    def is_first_row_header(self) -> bool:
        if hasattr(self._win, "edit_content_panel"):
            return self._win.edit_content_panel.is_first_row_header()
        return False

    @property
    def is_modified(self) -> bool:
        if hasattr(self._win, "edit_content_panel"):
            return getattr(self._win.edit_content_panel, "is_modified", False)
        return False

    @property
    def is_ui_locked(self) -> bool:
        return getattr(self._win, "_ui_locked", False)

    @property
    def is_data_loaded(self) -> bool:
        if hasattr(self._win, "edit_content_panel"):
            return len(self._win.edit_content_panel.get_all_rows()) > 0
        return False

    @property
    def all_rows(self) -> list:
        if hasattr(self._win, "edit_content_panel"):
            return self._win.edit_content_panel.get_all_rows()
        return []


class BasePanel(QFrame):
    request_lock_ui = pyqtSignal(bool)
    progress_updated = pyqtSignal(int, int)
    status_updated = pyqtSignal(str)
    log_emitted = pyqtSignal(str, str)
    request_start_worker = pyqtSignal(object)

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
