from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt, pyqtSignal

class AppContext:
    """
    AppContext — 封裝主畫面的動態設定與狀態，提供子面板唯讀存取。
    """
    def __init__(self, main_window):
        self._win = main_window

    @property
    def source_path(self) -> str:
        return self._win.txt_src_path.text().strip()

    @property
    def output_path(self) -> str:
        return self._win.txt_out_path.text().strip()

    @property
    def start_row(self) -> str:
        return self._win.txt_start_row.text().strip()

    @property
    def end_row(self) -> str:
        return self._win.txt_end_row.text().strip()

    @property
    def source_col(self) -> str:
        return self._win.txt_src_col.text().strip()

    @property
    def target_col(self) -> str:
        return self._win.txt_tgt_col.text().strip()

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

    def get_config(self) -> dict:
        return {}

    def set_config(self, config: dict):
        pass

    def lock_ui(self, lock: bool):
        self.request_lock_ui.emit(lock)

    def update_progress(self, current: int, total: int):
        self.progress_updated.emit(current, total)

    def update_status(self, status: str):
        self.status_updated.emit(status)

    def write_log(self, level: str, message: str):
        self.log_emitted.emit(level, message)
