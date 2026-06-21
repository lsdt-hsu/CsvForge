import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QFrame, QStackedWidget,
    QSplitter
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QIntValidator, QIcon

from translation.translation_panel import TranslationPanel
from edit.edit_panel import EditPanel
from settings_manager import SettingsManager
from data_editor.data_editor_panel import DataEditorPanel
from ui_constants import (
    WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    SIDEBAR_FULL_WIDTH, SIDEBAR_WIDTH, ACTIVITY_BAR_WIDTH,
    PROGRESS_BAR_WIDTH, START_BUTTON_MIN_WIDTH,
    INPUT_START_ROW_MAX_WIDTH, INPUT_END_ROW_MAX_WIDTH, INPUT_COL_MAX_WIDTH,
    SWAP_ICON_SIZE,
)
from ui_mixins import UiStateMixin, FileOpsMixin, SettingsMixin, FilterMixin, WorkerMixin


class MainWindow(UiStateMixin, FileOpsMixin, SettingsMixin, FilterMixin, WorkerMixin, QMainWindow):
    """
    主視窗：負責 UI 佈局建構與初始化。
    各項業務邏輯透過 Mixin 繼承組合：
      UiStateMixin    — 日誌、控制項啟停、分頁切換、按鈕狀態
      FileOpsMixin    — 檔案操作與存檔
      SettingsMixin   — 設定持久化與 Splitter 管理
      FilterMixin     — 過濾協調
      WorkerMixin     — Worker 生命週期管理
    """

    def __init__(self):
        super().__init__()
        self.worker = None
        self.start_time = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_elapsed_time)
        self.settings_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.json"
        )
        self.settings_manager = SettingsManager(self.settings_path)

        self.status_expanded = True
        self.status_expanded_height = 250
        self.settings_restored = False

        # WorkerMixin 私有狀態
        self._worker_sleep_prevented = False

        self.init_ui()
        self.restore_settings()

    # ── 左側面板建構 ──────────────────────────────────────────────────────────

    def _build_left_panel(self):
        self.left_container = QFrame()
        self.left_container.setObjectName("leftContainer")
        self.left_container.setFixedWidth(SIDEBAR_FULL_WIDTH)

        left_layout = QHBoxLayout(self.left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # 1. 活動列 (QWidget)
        self.activity_bar = QWidget()
        self.activity_bar.setObjectName("activityBarWidget")
        self.activity_bar.setFixedWidth(ACTIVITY_BAR_WIDTH)

        activity_layout = QVBoxLayout(self.activity_bar)
        activity_layout.setContentsMargins(10, 15, 10, 15)
        activity_layout.setSpacing(10)
        activity_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 翻譯按鈕
        translate_icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "translate.png"
        )
        self.btn_translate = QPushButton()
        self.btn_translate.setObjectName("btnActivityTranslate")
        self.btn_translate.setFixedSize(40, 40)
        self.btn_translate.setIcon(QIcon(translate_icon_path))
        self.btn_translate.setIconSize(QSize(40, 40))
        self.btn_translate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_translate.clicked.connect(lambda: self.switch_sidebar_tab("translate"))
        self.btn_translate.setProperty("active", True)
        activity_layout.addWidget(self.btn_translate)

        # 編輯按鈕
        edit_icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "edit.png"
        )
        self.btn_edit = QPushButton()
        self.btn_edit.setObjectName("btnActivityEdit")
        self.btn_edit.setFixedSize(40, 40)
        self.btn_edit.setIcon(QIcon(edit_icon_path))
        self.btn_edit.setIconSize(QSize(40, 40))
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit.clicked.connect(lambda: self.switch_sidebar_tab("edit"))
        self.btn_edit.setProperty("active", False)
        activity_layout.addWidget(self.btn_edit)

        activity_layout.addStretch()

        left_layout.addWidget(self.activity_bar)

        # 2. 垂直分割線 (QWidget)
        self.v_line = QWidget()
        self.v_line.setObjectName("sidebarSeparator")
        self.v_line.setFixedWidth(1)
        left_layout.addWidget(self.v_line)

        # 3. 側邊欄 (QWidget)
        self.sidebar = QWidget()
        self.sidebar.setObjectName("leftSidebarWidget")
        self.sidebar.setFixedWidth(SIDEBAR_WIDTH)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 15, 15, 15)
        sidebar_layout.setSpacing(15)

        # 堆疊式容器 (QStackedWidget)
        self.sidebar_stacked = QStackedWidget()

        self.translation_panel = TranslationPanel()
        self.translation_panel.btn_start.clicked.connect(self.on_start_button_clicked)
        self.edit_panel = EditPanel()
        self.edit_panel.request_filter.connect(self.start_filtering)

        self.sidebar_stacked.addWidget(self.translation_panel)
        self.sidebar_stacked.addWidget(self.edit_panel)

        sidebar_layout.addWidget(self.sidebar_stacked, stretch=1)

        left_layout.addWidget(self.sidebar)

    # ── 右側上半部：輸入與輸出面板 ───────────────────────────────────────────

    def _build_files_group(self):
        grp_files = QFrame()
        grp_files.setObjectName("rightFrame")
        grp_files_layout = QVBoxLayout(grp_files)
        grp_files_layout.setContentsMargins(15, 12, 15, 12)
        grp_files_layout.setSpacing(10)

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

        grp_files_layout.addWidget(title_row_widget)

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
        self.txt_src_path.textChanged.connect(self.on_source_file_changed)
        btn_src_browse = QPushButton("瀏覽...")
        btn_src_browse.setObjectName("btnBrowse")
        btn_src_browse.clicked.connect(self.browse_source_file)
        src_layout.addWidget(lbl_src)
        src_layout.addWidget(self.txt_src_path)
        src_layout.addWidget(btn_src_browse)
        row1_layout.addLayout(src_layout)

        # 左右交換按鈕
        self.btn_swap = QPushButton()
        self.btn_swap.setObjectName("btnSwap")
        self.btn_swap.setFixedSize(30, 30)
        swap_icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "swap.png"
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
        btn_out_browse = QPushButton("瀏覽...")
        btn_out_browse.setObjectName("btnBrowse")
        btn_out_browse.clicked.connect(self.browse_output_file)
        out_layout.addWidget(lbl_out)
        out_layout.addWidget(self.txt_out_path)
        out_layout.addWidget(btn_out_browse)
        row1_layout.addLayout(out_layout)

        files_content_layout.addLayout(row1_layout)

        # 第二列：行號、欄號與開始按鈕
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(15)

        lbl_start_row = QLabel("起始行號：")
        self.txt_start_row = QLineEdit("2")
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
        self.btn_start.clicked.connect(self.on_start_button_clicked)

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
        grp_files_layout.addWidget(self.files_content_widget)
        return grp_files

    # ── 右側下半部：執行狀態與日誌面板 ─────────────────────────────────────

    def _build_status_group(self):
        grp_status = QFrame()
        grp_status.setObjectName("rightFrame")
        grp_status_layout = QVBoxLayout(grp_status)
        grp_status_layout.setContentsMargins(15, 15, 15, 15)
        grp_status_layout.setSpacing(8)

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
        self.elapsed_time_str = "00:00:00"
        self.task_status_str = "就緒"
        self.lbl_status_summary = QLabel("已用時間：00:00:00 | 狀態：就緒")
        status_header_layout.addWidget(self.lbl_status_summary, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(PROGRESS_BAR_WIDTH)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0/0")
        status_header_layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignVCenter)

        grp_status_layout.addWidget(self.status_header_widget)

        # 日誌輸出框
        self.txt_log = QTextEdit()
        self.txt_log.setObjectName("logConsole")
        self.txt_log.setReadOnly(True)
        grp_status_layout.addWidget(self.txt_log)
        return grp_status

    # ── 主視窗初始化 ─────────────────────────────────────────────────────────

    def init_ui(self):
        self.setWindowTitle("CsvTranslator - CSV 批次翻譯工具")
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        main_widget = QWidget()
        main_widget.setObjectName("mainContainer")
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 左側大容器：活動列 + 側邊欄
        self._build_left_panel()
        main_layout.addWidget(self.left_container)

        # 右側面板
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)

        self.grp_files = self._build_files_group()
        right_panel.addWidget(self.grp_files)

        # 來源預覽與日誌面板採用 QSplitter 垂直排列
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.setObjectName("rightSplitter")

        # 內容面板
        self.edit_content_panel = DataEditorPanel()
        self.edit_content_panel.request_save.connect(self.save_edit_data)
        self.edit_content_panel.header_state_changed.connect(self.on_header_state_changed)

        self.grp_status = self._build_status_group()
        self.grp_status.setMinimumHeight(140)

        self.right_splitter.addWidget(self.edit_content_panel)
        self.right_splitter.addWidget(self.grp_status)
        self.right_splitter.setStretchFactor(0, 1)
        self.right_splitter.setStretchFactor(1, 0)
        self.right_splitter.splitterMoved.connect(self.on_splitter_moved)

        right_panel.addWidget(self.right_splitter)
        main_layout.addLayout(right_panel, stretch=1)

        self.apply_style()

    # ── QSS 樣式 ─────────────────────────────────────────────────────────────

    def apply_style(self):
        qss = """
        /* 主視窗樣式 */
        QMainWindow {
            background-color: #1a1b26;
        }
        QWidget#mainContainer {
            background-color: #1a1b26;
        }

        /* 面板樣式 */
        QFrame#leftContainer {
            background-color: #20212e;
            border: 1px solid #2f3047;
            border-radius: 12px;
        }
        QWidget#sidebarSeparator {
            background-color: #2f3047;
        }
        QFrame#grpFrame {
            background-color: transparent;
            border: none;
            border-radius: 0px;
            padding: 0px;
        }
        QFrame#rightFrame {
            background-color: #20212e;
            border: 1px solid #2f3047;
            border-radius: 12px;
        }

        /* 活動列按鈕 */
        QPushButton#btnActivityTranslate, QPushButton#btnActivityEdit {
            background-color: transparent;
            border: none;
            border-radius: 8px;
            padding: 0px;
        }
        QPushButton#btnActivityTranslate:hover, QPushButton#btnActivityEdit:hover {
            background-color: #2e3047;
        }
        QPushButton#btnActivityTranslate[active="true"], QPushButton#btnActivityEdit[active="true"] {
            background-color: #3b4261;
        }

        /* 折疊按鈕樣式 */
        QPushButton#btnToggleFiles, QPushButton#btnToggleStatus {
            background-color: transparent;
            color: #7aa2f7;
            border: none;
            font-size: 11px;
            font-weight: bold;
            padding: 0px;
        }
        QPushButton#btnToggleFiles:hover, QPushButton#btnToggleStatus:hover {
            color: #89ddff;
        }

        /* Splitter 分隔線樣式 */
        QSplitter::handle {
            background-color: #2f3047;
        }
        QSplitter::handle:hover {
            background-color: #7aa2f7;
        }
        QSplitter::handle:horizontal {
            width: 4px;
        }
        QSplitter::handle:vertical {
            height: 4px;
        }

        /* QCheckBox 美化樣式 */
        QCheckBox {
            color: #a9b1d6;
            font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
            font-size: 13px;
        }
        QCheckBox:hover {
            color: #c0caf5;
        }

        /* 標籤字型與文字樣式 */
        QLabel {
            color: #a9b1d6;
            font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
            font-size: 13px;
        }
        QWidget#titleRowWidget {
            margin-bottom: 5px;
        }
        QLabel#appTitle {
            font-size: 22px;
            font-weight: bold;
            color: #7aa2f7;
            font-family: "Segoe UI", "Microsoft JhengHei", sans-serif;
        }
        QLabel#sectionHeader {
            font-size: 14px;
            font-weight: bold;
            color: #7aa2f7;
        }
        QLabel#previewStatus {
            font-size: 11px;
            color: #565f89;
        }

        /* 輸入框與下拉選單 */
        QLineEdit, QComboBox {
            background-color: #16161e;
            border: 1px solid #2f3047;
            border-radius: 6px;
            padding: 7px;
            color: #c0caf5;
        }
        QLineEdit:focus, QComboBox:focus {
            border: 1px solid #7aa2f7;
        }
        QComboBox::drop-down {
            border: 0px;
        }

        /* 按鈕樣式 */
        QPushButton {
            background-color: #414868;
            color: #c0caf5;
            border: none;
            border-radius: 6px;
            padding: 8px 15px;
            font-weight: bold;
            font-size: 13px;
        }
        QPushButton:hover {
            background-color: #565f89;
        }
        QPushButton:pressed {
            background-color: #3b4261;
        }
        QPushButton#btnStart {
            background-color: #7aa2f7;
            color: #1a1b26;
            font-size: 15px;
            padding: 12px;
        }
        QPushButton#btnStart:hover {
            background-color: #89ddff;
        }
        QPushButton#btnStart:disabled {
            background-color: #24283b;
            color: #565f89;
        }

        QPushButton#btnBrowse {
            background-color: #3b4261;
            font-size: 12px;
            padding: 7px 12px;
        }
        QPushButton#btnBrowse:hover {
            background-color: #414868;
        }

        QPushButton#btnSwap, QPushButton#btnSwapRules, QPushButton#btnSaveData {
            background-color: #3b4261;
            border: none;
            border-radius: 6px;
            padding: 0px;
        }
        QPushButton#btnSwap:hover, QPushButton#btnSwapRules:hover, QPushButton#btnSaveData:hover {
            background-color: #414868;
        }
        QPushButton#btnSwap:pressed, QPushButton#btnSwapRules:pressed, QPushButton#btnSaveData:pressed {
            background-color: #2e3c64;
        }
        QPushButton#btnSaveData:disabled {
            background-color: #1c1d27;
            border: 1px dashed #2f3047;
        }

        /* 表格樣式 */
        QTableWidget, QTableView {
            background-color: #16161e;
            color: #a9b1d6;
            border: 1px solid #2f3047;
            gridline-color: #232433;
            border-radius: 8px;
            outline: none;
        }
        QTableWidget::item, QTableView::item {
            padding: 5px;
            outline: none;
        }
        QTableWidget::item:selected, QTableView::item:selected {
            background-color: #2e3c64;
            color: #c0caf5;
            outline: none;
        }
        QAbstractItemView QLineEdit {
            background-color: #16161e;
            color: #c0caf5;
            border: none;
            border-radius: 0px;
            padding: 0px;
            margin: 0px;
        }
        QHeaderView::section {
            background-color: #20212e;
            color: #7aa2f7;
            padding: 6px;
            border: 1px solid #2f3047;
            font-weight: bold;
        }
        QScrollBar:vertical {
            background-color: #16161e;
            width: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background-color: #3b4261;
            min-height: 20px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #414868;
        }

        /* 進度條樣式 */
        QProgressBar {
            border: 1px solid #2f3047;
            border-radius: 6px;
            background-color: #16161e;
            text-align: center;
            color: #c0caf5;
            font-weight: bold;
            font-size: 11px;
            height: 18px;
        }
        QProgressBar::chunk {
            background-color: #0000ff;
            border-radius: 5px;
        }

        QTextEdit#logConsole {
            background-color: #16161e;
            border: 1px solid #2f3047;
            border-radius: 8px;
            font-family: "Consolas", "Courier New", monospace;
            font-size: 12px;
            color: #9ece6a;
            padding: 8px;
        }

        /* 圓形切換按鈕 */
        QPushButton#btnToggleRule {
            background-color: #3b4261;
            color: #7aa2f7;
            border: 1px solid #2f3047;
            border-radius: 15px;
            font-size: 16px;
            font-weight: bold;
            padding: 0px;
        }
        QPushButton#btnToggleRule:hover {
            background-color: #414868;
            color: #89ddff;
            border-color: #7aa2f7;
        }
        QPushButton#btnToggleRule:pressed {
            background-color: #2e3c64;
        }

        /* QRadioButton 美化樣式 */
        QRadioButton {
            color: #a9b1d6;
            font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
            font-size: 13px;
        }
        QRadioButton:hover {
            color: #c0caf5;
        }
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border-radius: 8px;
            border: 2px solid #2f3047;
            background-color: #16161e;
        }
        QRadioButton::indicator:hover {
            border-color: #7aa2f7;
        }
        QRadioButton::indicator:checked {
            border-color: #7aa2f7;
            background-color: #7aa2f7;
        }
        """
        self.setStyleSheet(qss)

    def on_header_state_changed(self, is_hdr: bool) -> None:
        """當『第一行為標題』狀態改變時，更新編輯過濾面板的比對欄位與比對目標下拉選單。"""
        all_rows = self.edit_content_panel.get_all_rows()
        if all_rows:
            num_cols = max(len(r) for r in all_rows)
            headers = all_rows[0] if is_hdr else None
            self.edit_panel.update_column_dropdowns(num_cols, headers)

    # ── 視窗關閉事件 ─────────────────────────────────────────────────────────

    def closeEvent(self, event):
        """Qt 事件覆寫：視窗關閉時恢復系統休眠設定並儲存所有設定。
        必須呼叫 super().closeEvent(event) 維持 MRO 鏈完整性。
        """
        if getattr(self, "_worker_sleep_prevented", False):
            from utils import prevent_sleep
            prevent_sleep(False)
        self.save_settings()
        super().closeEvent(event)  # ← MRO 鏈傳遞至 QMainWindow，勿省略
