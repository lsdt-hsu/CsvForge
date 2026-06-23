import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIntValidator, QIcon

from base_panel import BasePanel
from ui_constants import (
    INPUT_START_ROW_MAX_WIDTH,
    INPUT_END_ROW_MAX_WIDTH,
    INPUT_COL_MAX_WIDTH,
    START_BUTTON_MIN_WIDTH,
    SWAP_ICON_SIZE,
)
from settings_manager import IoPanelConfig
from .io_panel_validator import validate_paths_not_equal


class IoPanel(BasePanel):
    source_file_changed = pyqtSignal(str)

    def __init__(self, parent=None, context=None):
        super().__init__(parent, title_text="", require_data_loading=False, context=context)
        self.setObjectName("rightFrame")
        self._ui_enabled_state = True

        from .csv_loader import CSVLoader
        self.loader = CSVLoader(parent=parent, context=context)
        self.loader.started.connect(self.on_loader_started)
        self.loader.finished.connect(self.on_loader_finished)
        self.loader.cancelled.connect(self.on_loader_cancelled)

        self.init_ui()

    def init_ui(self):
        layout = self.controls_layout
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(10)

        # 標題與展開/收合列
        title_row_widget = QWidget()
        title_row_widget.setObjectName("titleRowWidget")
        title_layout = QHBoxLayout(title_row_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(10)

        self.btn_toggle_files = QPushButton("▲")
        self.btn_toggle_files.setObjectName("btnToggleFiles")
        self.btn_toggle_files.setFixedSize(20, 20)
        self.btn_toggle_files.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_files.clicked.connect(self.toggle_files_panel)
        title_layout.addWidget(self.btn_toggle_files, alignment=Qt.AlignmentFlag.AlignVCenter)

        lbl_files_sec = QLabel("輸入與輸出")
        lbl_files_sec.setObjectName("sectionHeader")
        title_layout.addWidget(lbl_files_sec, alignment=Qt.AlignmentFlag.AlignVCenter)

        title_layout.addStretch()
        layout.addWidget(title_row_widget)

        # 內容容器
        self.files_content_widget = QWidget()
        self.files_content_widget.setObjectName("filesContentWidget")
        files_content_layout = QVBoxLayout(self.files_content_widget)
        files_content_layout.setContentsMargins(0, 0, 0, 0)
        files_content_layout.setSpacing(10)

        # 第一列：來源與輸出路徑
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(15)

        # 來源
        src_layout = QHBoxLayout()
        lbl_src = QLabel("來源 CSV：")
        self.txt_src_path = QLineEdit()
        self.txt_src_path.setPlaceholderText("選擇來源 CSV...")
        self.txt_src_path.textChanged.connect(self._on_text_changed)
        self.btn_src_browse = QPushButton("瀏覽...")
        self.btn_src_browse.setObjectName("btnBrowse")
        self.btn_src_browse.clicked.connect(self.browse_source_file)
        src_layout.addWidget(lbl_src)
        src_layout.addWidget(self.txt_src_path)
        src_layout.addWidget(self.btn_src_browse)
        row1_layout.addLayout(src_layout)

        # 左右交換按鈕
        self.btn_swap = QPushButton()
        self.btn_swap.setObjectName("btnSwap")
        self.btn_swap.setFixedSize(30, 30)
        swap_icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "swap.png"
        )
        self.btn_swap.setIcon(QIcon(swap_icon_path))
        self.btn_swap.setIconSize(QSize(SWAP_ICON_SIZE, SWAP_ICON_SIZE))
        self.btn_swap.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_swap.clicked.connect(self.swap_csv_paths)
        row1_layout.addWidget(self.btn_swap)

        # 輸出
        out_layout = QHBoxLayout()
        lbl_out = QLabel("輸出 CSV：")
        self.txt_out_path = QLineEdit()
        self.txt_out_path.setPlaceholderText("選擇輸出 CSV...")
        self.btn_out_browse = QPushButton("瀏覽...")
        self.btn_out_browse.setObjectName("btnBrowse")
        self.btn_out_browse.clicked.connect(self.browse_output_file)
        out_layout.addWidget(lbl_out)
        out_layout.addWidget(self.txt_out_path)
        out_layout.addWidget(self.btn_out_browse)
        row1_layout.addLayout(out_layout)

        files_content_layout.addLayout(row1_layout)

        # 第二列：行號、欄號與開始按鈕
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(15)

        lbl_start_row = QLabel("起始行號：")
        self.txt_start_row = QLineEdit("2")
        self.txt_start_row.setPlaceholderText("預設為 1")
        self.txt_start_row.setValidator(QIntValidator(1, 9999999))
        self.txt_start_row.setMaximumWidth(INPUT_START_ROW_MAX_WIDTH)

        lbl_end_row = QLabel("結束行號：")
        self.txt_end_row = QLineEdit()
        self.txt_end_row.setPlaceholderText("預設至檔尾")
        self.txt_end_row.setValidator(QIntValidator(1, 9999999))
        self.txt_end_row.setMaximumWidth(INPUT_END_ROW_MAX_WIDTH)

        lbl_src_col = QLabel("來源欄號：")
        self.txt_src_col = QLineEdit("1")
        self.txt_src_col.setValidator(QIntValidator(1, 9999))
        self.txt_src_col.setMaximumWidth(INPUT_COL_MAX_WIDTH)

        lbl_tgt_col = QLabel("目標欄號：")
        self.txt_tgt_col = QLineEdit("2")
        self.txt_tgt_col.setValidator(QIntValidator(1, 9999))
        self.txt_tgt_col.setMaximumWidth(INPUT_COL_MAX_WIDTH)

        self.btn_start = QPushButton("載入")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.setMinimumWidth(START_BUTTON_MIN_WIDTH)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self.on_start_clicked)

        row2_layout.addWidget(lbl_start_row)
        row2_layout.addWidget(self.txt_start_row)
        row2_layout.addWidget(lbl_end_row)
        row2_layout.addWidget(self.txt_end_row)
        row2_layout.addWidget(lbl_src_col)
        row2_layout.addWidget(self.txt_src_col)
        row2_layout.addWidget(lbl_tgt_col)
        row2_layout.addWidget(self.txt_tgt_col)
        row2_layout.addStretch()
        row2_layout.addWidget(self.btn_start)

        files_content_layout.addLayout(row2_layout)
        layout.addWidget(self.files_content_widget)

    def toggle_files_panel(self) -> None:
        collapsed = self.files_content_widget.isVisible()
        self.files_content_widget.setVisible(not collapsed)
        self.btn_toggle_files.setText("▼" if collapsed else "▲")
        cfg = self.context.io_panel_config
        cfg.collapsed = collapsed
        cfg.dirty = True

    def swap_csv_paths(self) -> None:
        src = self.txt_src_path.text()
        out = self.txt_out_path.text()
        self.txt_src_path.setText(out)
        self.txt_out_path.setText(src)

    def browse_source_file(self) -> None:
        current_src = self.txt_src_path.text().strip()
        initial_path = current_src if current_src else os.path.expanduser("~")
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇來源 CSV 檔案", initial_path, "CSV 檔案 (*.csv);;所有檔案 (*)"
        )
        if file_path:
            current_out = self.txt_out_path.text().strip()
            if not validate_paths_not_equal(self, file_path, current_out, mode="browse_src"):
                return

            self.txt_src_path.setText(file_path)
            # 自動推導輸出檔案路徑
            if not self.txt_out_path.text().strip():
                dir_name, file_name = os.path.split(file_path)
                name, ext = os.path.splitext(file_name)
                default_out = os.path.join(dir_name, f"{name}_translated{ext}")
                self.txt_out_path.setText(default_out)

    def browse_output_file(self) -> None:
        current_out = self.txt_out_path.text().strip()
        initial_path = current_out if current_out else os.path.expanduser("~")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "選擇儲存輸出 CSV 檔案", initial_path, "CSV 檔案 (*.csv);;所有檔案 (*)"
        )
        if file_path:
            current_src = self.txt_src_path.text().strip()
            if not validate_paths_not_equal(self, current_src, file_path, mode="browse_out"):
                return

            self.txt_out_path.setText(file_path)

    def _on_text_changed(self, text: str) -> None:
        self.source_file_changed.emit(text)

    def apply_config(self, cfg: IoPanelConfig) -> None:
        self.txt_src_path.setText(cfg.source_path)
        self.txt_out_path.setText(cfg.output_path)

        # 安全檢查：來源與輸出路徑不可相同
        src_path = self.txt_src_path.text().strip()
        out_path = self.txt_out_path.text().strip()
        if not validate_paths_not_equal(self, src_path, out_path, mode="config"):
            self.txt_out_path.clear()

        self.txt_start_row.setText(cfg.start_row)
        self.txt_end_row.setText(cfg.end_row)
        self.txt_src_col.setText(cfg.src_col)
        self.txt_tgt_col.setText(cfg.tgt_col)

        # 折疊狀態
        if cfg.collapsed:
            self.files_content_widget.setVisible(False)
            self.btn_toggle_files.setText("▼")
        else:
            self.files_content_widget.setVisible(True)
            self.btn_toggle_files.setText("▲")

    def update_config(self, cfg: IoPanelConfig) -> None:
        cfg.source_path = self.txt_src_path.text().strip()
        cfg.output_path = self.txt_out_path.text().strip()
        cfg.start_row = self.txt_start_row.text()
        cfg.end_row = self.txt_end_row.text()
        cfg.src_col = self.txt_src_col.text()
        cfg.tgt_col = self.txt_tgt_col.text()
        cfg.collapsed = not self.files_content_widget.isVisible()
        cfg.dirty = True

    def set_end_row_placeholder(self, total_rows: int) -> None:
        self.txt_end_row.setPlaceholderText(f"預設至檔尾 ({total_rows})")


    def set_enabled(self, enabled: bool) -> None:
        self._ui_enabled_state = enabled
        self.txt_src_path.setEnabled(enabled)
        self.txt_out_path.setEnabled(enabled)
        self.btn_src_browse.setEnabled(enabled)
        self.btn_out_browse.setEnabled(enabled)
        self.btn_swap.setEnabled(enabled)
        self.txt_start_row.setEnabled(enabled)
        self.txt_end_row.setEnabled(enabled)
        self.txt_src_col.setEnabled(enabled)
        self.txt_tgt_col.setEnabled(enabled)
        
        self.update_button_ui()

    def on_start_clicked(self) -> None:
        if self.loader.is_running():
            if not self.loader.is_cancelled():
                self.loader.cancel_task()
                self.update_button_ui()
        else:
            self.loader.start_load_task()

    def on_loader_started(self) -> None:
        self.update_button_ui()

    def on_loader_finished(self) -> None:
        self.update_button_ui()

    def on_loader_cancelled(self) -> None:
        self.update_button_ui()

    def update_button_ui(self) -> None:
        style_disabled = "background-color: #24283b; color: #565f89;"
        style_critical = "background-color: #f7768e; color: #1a1b26;"
        style_normal = ""

        if self.loader.is_running():
            if self.loader.is_cancelled():
                self.btn_start.setText("正在停止...")
                self.btn_start.setEnabled(False)
                self.btn_start.setStyleSheet(style_disabled)
            else:
                self.btn_start.setText("停止載入")
                self.btn_start.setEnabled(True)
                self.btn_start.setStyleSheet(style_critical)
        else:
            self.btn_start.setText("載入")
            self.btn_start.setStyleSheet(style_normal)
            self.btn_start.setEnabled(self._ui_enabled_state)
