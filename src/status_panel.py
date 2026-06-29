import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QTextEdit, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

from base.main_base_panel import BasePanel
from ui_constants import PROGRESS_BAR_WIDTH
from settings_manager import StatusPanelConfig


class StatusPanel(BasePanel):
    toggle_clicked = pyqtSignal(bool)

    def __init__(self, parent=None, context=None):
        super().__init__(parent, context=context)
        self.setObjectName("rightFrame")
        self.init_ui()

    def init_ui(self):
        layout = self.controls_layout
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        # 狀態標頭列
        self.status_header_widget = QWidget()
        self.status_header_widget.setObjectName("statusHeaderWidget")
        status_header_layout = QHBoxLayout(self.status_header_widget)
        status_header_layout.setContentsMargins(0, 0, 0, 0)
        status_header_layout.setSpacing(15)

        self.btn_toggle_status = QPushButton("▲")
        self.btn_toggle_status.setObjectName("btnToggleStatus")
        self.btn_toggle_status.setFixedSize(20, 20)
        self.btn_toggle_status.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_status.clicked.connect(self.toggle_status_panel)
        status_header_layout.addWidget(self.btn_toggle_status, alignment=Qt.AlignmentFlag.AlignVCenter)

        lbl_log_title = QLabel("執行狀態與日誌")
        lbl_log_title.setObjectName("sectionHeader")
        status_header_layout.addWidget(lbl_log_title, alignment=Qt.AlignmentFlag.AlignVCenter)

        status_header_layout.addStretch()

        # 狀態摘要（已用時間 + 狀態）
        self.lbl_status_summary = QLabel("已用時間：00:00:00 | 狀態：就緒")
        status_header_layout.addWidget(self.lbl_status_summary, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(PROGRESS_BAR_WIDTH)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0/0")
        status_header_layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self.status_header_widget)

        # 日誌輸出框
        self.txt_log = QTextEdit()
        self.txt_log.setObjectName("logConsole")
        self.txt_log.setReadOnly(True)
        layout.addWidget(self.txt_log)

    def append_log(self, level: str, message: str) -> None:
        color_map = {
            "INFO": "#c0caf5",
            "SUCCESS": "#9ece6a",
            "WARNING": "#e0af68",
            "ERROR": "#f7768e",
        }
        color = color_map.get(level, "#c0caf5")
        timestamp = time.strftime("[%H:%M:%S]")
        log_html = (
            f'<font color="#565f89">{timestamp}</font> '
            f'<font color="{color}">[{level}] {message}</font>'
        )

        # 將新日誌插入至頂端（倒序顯示）
        cursor = self.txt_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.insertHtml(log_html)
        cursor.insertBlock()

        # 超過 10001 行時移除最舊的一行
        if self.txt_log.document().blockCount() > 10001:
            end_cursor = self.txt_log.textCursor()
            end_cursor.movePosition(end_cursor.MoveOperation.End)
            end_cursor.movePosition(
                end_cursor.MoveOperation.PreviousBlock, end_cursor.MoveMode.KeepAnchor
            )
            end_cursor.removeSelectedText()

    def update_progress(self, current: int, total: int) -> None:
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{current}/{total}")

    def update_status(self, elapsed_time_str: str, task_status_str: str) -> None:
        self.lbl_status_summary.setText(
            f"已用時間：{elapsed_time_str} | 狀態：{task_status_str}"
        )

    def toggle_status_panel(self) -> None:
        cfg = self.context.status_panel_config
        cfg.collapsed = not cfg.collapsed
        cfg.dirty = True

        self.txt_log.setVisible(not cfg.collapsed)
        self.btn_toggle_status.setText("▲" if not cfg.collapsed else "▼")
        self.toggle_clicked.emit(cfg.collapsed)

    def header_height(self) -> int:
        header_h = self.status_header_widget.sizeHint().height() + 30
        return max(50, header_h)

    def apply_config(self, cfg: StatusPanelConfig) -> None:
        self.txt_log.setVisible(not cfg.collapsed)
        self.btn_toggle_status.setText("▲" if not cfg.collapsed else "▼")
        self.toggle_clicked.emit(cfg.collapsed)

    def update_config(self, cfg: StatusPanelConfig, splitter_sizes: list[int] = None) -> None:
        cfg.collapsed = self.btn_toggle_status.text() == "▼"
        if not cfg.collapsed and splitter_sizes and len(splitter_sizes) > 1 and splitter_sizes[1] > 0:
            cfg.expanded_height = splitter_sizes[1]
        cfg.dirty = True
