import os
import sys
import time
import csv
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QFrame, QHeaderView, QStackedWidget,
    QSplitter
)
from PyQt6.QtCore import Qt, QTimer, QSettings, QSize
from PyQt6.QtGui import QIntValidator, QFont, QIcon

from translation.translation_worker import CSVTranslatorWorker
from translation.translation_panel import TranslationPanel
from edit.edit_panel import EditPanel
from edit.edit_worker import CSVEditWorker
from settings_manager import SettingsManager
from preview.preview_panel import PreviewPanel
from edit.edit_content_panel import EditContentPanel

# UI 佈局常數
WINDOW_DEFAULT_WIDTH = 1100
WINDOW_DEFAULT_HEIGHT = 750
WINDOW_MIN_WIDTH = 950
WINDOW_MIN_HEIGHT = 600

SIDEBAR_FULL_WIDTH = 341
SIDEBAR_MIN_WIDTH = 60
SIDEBAR_WIDTH = 280
ACTIVITY_BAR_WIDTH = 60

#

PROGRESS_BAR_WIDTH = 150
START_BUTTON_MIN_WIDTH = 150

INPUT_START_ROW_MAX_WIDTH = 80
INPUT_END_ROW_MAX_WIDTH = 100
INPUT_COL_MAX_WIDTH = 60

SWAP_BUTTON_SIZE = 32
SWAP_ICON_SIZE = 20



# 恢復視窗幾何狀態
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.start_time = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_elapsed_time)
        self.settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.json")
        self.settings_manager = SettingsManager(self.settings_path)
        
        self.status_expanded = True
        self.status_expanded_height = 250
        self.settings_restored = False
        
        self.init_ui()
        self.restore_settings()

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
        translate_icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "translate.png")
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
        edit_icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "edit.png")
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
        self.edit_panel = EditPanel()
        
        self.sidebar_stacked.addWidget(self.translation_panel)
        self.sidebar_stacked.addWidget(self.edit_panel)
        
        sidebar_layout.addWidget(self.sidebar_stacked)
        sidebar_layout.addStretch()

        left_layout.addWidget(self.sidebar)

    def _build_files_group(self):
        grp_files = QFrame()
        grp_files.setObjectName("rightFrame")
        grp_files_layout = QVBoxLayout(grp_files)
        grp_files_layout.setContentsMargins(15, 12, 15, 12)
        grp_files_layout.setSpacing(10)

        # 標題與段落標頭列
        title_row_widget = QWidget()
        title_row_widget.setObjectName("titleRowWidget")
        title_layout = QHBoxLayout(title_row_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(10)
        
        # 展開/收合按鈕
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

        # 建立內容容器
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
        swap_icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "swap.png")
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

        # 第二列：起始/結束行號、來源/目標列號與開始翻譯按鈕
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

        self.btn_start = QPushButton("開始")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.setMinimumWidth(START_BUTTON_MIN_WIDTH)
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


    def _build_status_group(self):
        grp_status = QFrame()
        grp_status.setObjectName("rightFrame")
        grp_status_layout = QVBoxLayout(grp_status)
        grp_status_layout.setContentsMargins(15, 15, 15, 15)
        grp_status_layout.setSpacing(8)

        # 狀態與日誌標頭列
        self.status_header_widget = QWidget()
        self.status_header_widget.setObjectName("statusHeaderWidget")
        status_header_layout = QHBoxLayout(self.status_header_widget)
        status_header_layout.setContentsMargins(0, 0, 0, 0)
        status_header_layout.setSpacing(15)

        # 展開/收合按鈕
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

        # 狀態訊息：僅顯示已用時間與狀態
        self.elapsed_time_str = "00:00:00"
        self.task_status_str = "就緒"
        self.lbl_status_summary = QLabel("已用時間：00:00:00 | 狀態：就緒")
        status_header_layout.addWidget(self.lbl_status_summary, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 進度條：顯示 n/m (筆數)
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

    def init_ui(self):
        self.setWindowTitle("CsvTranslator - CSV 批次翻譯工具")
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        
        # 主視窗佈局設定
        main_widget = QWidget()
        main_widget.setObjectName("mainContainer")
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ----------------- 左側大容器：合併活動列與設定欄 -----------------
        self._build_left_panel()
        main_layout.addWidget(self.left_container)

        # ----------------- 右側面板：控制主區域與日誌 -----------------
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)

        # 輸入與輸出面板
        self.grp_files = self._build_files_group()
        right_panel.addWidget(self.grp_files)

        # 來源檔案預覽與日誌面板採用 QSplitter 垂直排列
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.setObjectName("rightSplitter")

        # 建立內容堆疊器與預覽、編輯面板
        self.content_stack = QStackedWidget()

        self.preview_panel = PreviewPanel()
        self.preview_panel.preview_loaded.connect(self.on_preview_loaded)

        self.edit_content_panel = EditContentPanel()

        self.content_stack.addWidget(self.preview_panel)
        self.content_stack.addWidget(self.edit_content_panel)

        # 雙向同步「第一行為標題」核取方塊的 clicked 訊號
        self.preview_panel.chk_first_row_header.clicked.connect(
            lambda: self.edit_content_panel.chk_first_row_header.setChecked(self.preview_panel.chk_first_row_header.isChecked())
        )
        self.edit_content_panel.chk_first_row_header.clicked.connect(
            lambda: self.preview_panel.chk_first_row_header.setChecked(self.preview_panel.chk_first_row_header.isChecked())
        )

        self.grp_status = self._build_status_group()
        self.grp_status.setMinimumHeight(140)

        self.right_splitter.addWidget(self.content_stack)
        self.right_splitter.addWidget(self.grp_status)

        # Stretch factor: preview panel is 1, status panel is 0 (keeps status height stable on resize)
        self.right_splitter.setStretchFactor(0, 1)
        self.right_splitter.setStretchFactor(1, 0)
        
        self.right_splitter.splitterMoved.connect(self.on_splitter_moved)

        right_panel.addWidget(self.right_splitter)

        main_layout.addLayout(right_panel, stretch=1)

        # 載入 QSS 樣式設定
        self.apply_style()

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
            background-color: #242538;
            border: 1px solid #2f3047;
            border-radius: 8px;
            padding: 5px;
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

        QPushButton#btnSwap {
            background-color: #3b4261;
            border: none;
            border-radius: 6px;
            padding: 0px;
        }
        QPushButton#btnSwap:hover {
            background-color: #414868;
        }
        QPushButton#btnSwap:pressed {
            background-color: #2e3c64;
        }



        /* 表格樣式 */
        QTableWidget, QTableView {
            background-color: #16161e;
            color: #a9b1d6;
            border: 1px solid #2f3047;
            gridline-color: #232433;
            border-radius: 8px;
            outline: none; /* 移除選取格時的焦點虛線框 */
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
            border: none; /* 編輯時不顯示編輯框外線 */
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
        """
        self.setStyleSheet(qss)

    # ----------------- 事件與邏輯處理函數 -----------------
    def swap_csv_paths(self):
        src = self.txt_src_path.text()
        out = self.txt_out_path.text()
        self.txt_src_path.setText(out)
        self.txt_out_path.setText(src)

    def browse_source_file(self):
        current_src = self.txt_src_path.text().strip()
        initial_path = current_src if current_src else os.path.expanduser("~")
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇來源 CSV 檔案", initial_path, "CSV 檔案 (*.csv);;所有檔案 (*)"
        )
        if file_path:
            # 檢查點：瀏覽來源檔案與輸出檔案相同
            current_out = self.txt_out_path.text().strip()
            if current_out and file_path == current_out:
                QMessageBox.warning(self, "路徑重複", "選擇的來源 CSV 檔案不能與輸出 CSV 檔案路徑相同！請重新選擇。")
                return # 放棄本次選擇結果
            
            self.txt_src_path.setText(file_path)
            # 自動推導輸出檔案路徑
            if not self.txt_out_path.text().strip():
                dir_name, file_name = os.path.split(file_path)
                name, ext = os.path.splitext(file_name)
                default_out = os.path.join(dir_name, f"{name}_translated{ext}")
                self.txt_out_path.setText(default_out)

    def browse_output_file(self):
        current_out = self.txt_out_path.text().strip()
        initial_path = current_out if current_out else os.path.expanduser("~")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "選擇儲存輸出 CSV 檔案", initial_path, "CSV 檔案 (*.csv);;所有檔案 (*)"
        )
        if file_path:
            # 檢查點：瀏覽輸出檔案與來源檔案相同
            current_src = self.txt_src_path.text().strip()
            if current_src and file_path == current_src:
                QMessageBox.warning(self, "路徑重複", "選擇的輸出 CSV 檔案不能與來源 CSV 檔案路徑相同！請重新選擇。")
                return # 放棄本次選擇結果
                
            self.txt_out_path.setText(file_path)

    def on_source_file_changed(self, file_path):
        if not file_path.strip() or not os.path.exists(file_path):
            self.preview_panel.clear_preview()
            self.txt_end_row.setPlaceholderText("預設至檔尾")
            return
        
        self.preview_panel.load_preview(file_path)

    def on_preview_loaded(self, total_rows):
        self.txt_end_row.setPlaceholderText(f"預設至檔尾 ({total_rows})")

    def append_log(self, level, message):
        color_map = {
            "INFO": "#c0caf5",       # 一般日誌
            "SUCCESS": "#9ece6a",    # 成功
            "WARNING": "#e0af68",    # 警告
            "ERROR": "#f7768e"       # 錯誤
        }
        color = color_map.get(level, "#c0caf5")
        timestamp = time.strftime("[%H:%M:%S]")
        log_html = f'<font color="#565f89">{timestamp}</font> <font color="{color}">[{level}] {message}</font>'
        
        # 將新日誌插入至日誌最上方 (倒序)
        cursor = self.txt_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.insertHtml(log_html)
        cursor.insertBlock()
        
        # 將新日誌插入至日誌最上方 (倒序)
        if self.txt_log.document().blockCount() > 10001:
            end_cursor = self.txt_log.textCursor()
            end_cursor.movePosition(end_cursor.MoveOperation.End)
            end_cursor.movePosition(end_cursor.MoveOperation.PreviousBlock, end_cursor.MoveMode.KeepAnchor)
            end_cursor.removeSelectedText()

    def start_task(self):
        # 檢查點：開始任務時來源與輸出不為空且相同
        src_path = self.txt_src_path.text().strip()
        out_path = self.txt_out_path.text().strip()
        if src_path and out_path and src_path == out_path:
            QMessageBox.warning(self, "路徑重複", "來源 CSV 與輸出 CSV 路徑相同，無法開始任務！請變更輸出路徑。")
            return

        # 判斷當前活躍的分頁
        active_tab = "translate"
        if self.sidebar.isVisible() and self.sidebar_stacked.currentWidget() == self.edit_panel:
            active_tab = "edit"

        # 讀取通用設定值（以原始字串傳遞給 Worker，由 Worker 進行多態驗證與轉型）
        src_path = self.txt_src_path.text().strip()
        out_path = self.txt_out_path.text().strip()
        start_row = self.txt_start_row.text().strip()
        end_row = self.txt_end_row.text().strip()

        # 根據活躍分頁初始化背景工作器實例
        if active_tab == "translate":
            src_col = self.txt_src_col.text().strip()
            tgt_col = self.txt_tgt_col.text().strip()
            src_lang = self.translation_panel.get_src_lang()
            tgt_lang = self.translation_panel.get_tgt_lang()
            batch_interval = self.translation_panel.get_batch_interval()
            single_interval = self.translation_panel.get_single_interval()
            
            worker_instance = CSVTranslatorWorker(
                source_path=src_path,
                output_path=out_path,
                start_row=start_row,
                end_row=end_row,
                source_col=src_col,
                target_col=tgt_col,
                source_lang=src_lang,
                target_lang=tgt_lang,
                batch_interval=batch_interval,
                single_interval=single_interval
            )
        else:
            worker_instance = CSVEditWorker(
                source_path=src_path,
                output_path=out_path,
                start_row=start_row,
                end_row=end_row
            )

        # 呼叫工作器進行多態輸入驗證
        is_valid, err_msg = worker_instance.validate_inputs()
        if not is_valid:
            QMessageBox.warning(self, "輸入錯誤", err_msg)
            return

        # 驗證成功，設定工作器屬性
        self.worker = worker_instance

        # 清空舊 UI 顯示狀態
        self.txt_log.clear()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0/0")
        self.elapsed_time_str = "00:00:00"
        self.task_status_str = "翻譯中..." if active_tab == "translate" else "編輯中..."
        self.update_status_summary()
        
        # 記錄開始時間
        self.start_time = time.time()
        self.timer.start(1000)

        self.worker.progress_updated.connect(self.on_worker_progress)
        self.worker.log_emitted.connect(self.append_log)
        self.worker.finished_successfully.connect(self.on_worker_success)
        self.worker.finished_with_error.connect(self.on_worker_error)
        
        self.worker.start()

        # 改變開始按鈕狀態與啟用狀態
        self.set_ui_enabled(False)
        self.update_start_button_ui()

    def update_status_summary(self):
        self.lbl_status_summary.setText(f"已用時間：{self.elapsed_time_str} | 狀態：{self.task_status_str}")

    def on_worker_progress(self, current, total):
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{current}/{total}")

    def update_elapsed_time(self):
        elapsed = int(time.time() - self.start_time)
        hrs = elapsed // 3600
        mins = (elapsed % 3600) // 60
        secs = elapsed % 60
        self.elapsed_time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        self.update_status_summary()

    def on_worker_success(self, out_path):
        self.timer.stop()
        self.set_ui_enabled(True)
        if self.worker and self.worker._is_cancelled:
            self.task_status_str = "已取消"
            self.update_status_summary()
            title, msg = self.worker.get_cancel_message(out_path)
            QMessageBox.information(self, title, msg)
        else:
            self.task_status_str = "完成"
            self.update_status_summary()
            
            # 判斷當前是否為編輯分頁
            active_tab = "translate"
            if self.sidebar.isVisible() and self.sidebar_stacked.currentWidget() == self.edit_panel:
                active_tab = "edit"
                
            if active_tab == "edit" and hasattr(self.worker, "loaded_rows"):
                start_row = 1
                try:
                    start_row = int(self.txt_start_row.text())
                except ValueError:
                    pass
                end_row = None
                if self.txt_end_row.text().strip():
                    try:
                        end_row = int(self.txt_end_row.text())
                    except ValueError:
                        pass
                
                self.edit_content_panel.load_data(self.worker.loaded_rows, start_row, end_row)
                self.content_stack.setCurrentWidget(self.edit_content_panel)
                
            title, msg = self.worker.get_success_message(out_path)
            QMessageBox.information(self, title, msg)

    def on_worker_error(self, err_msg):
        self.timer.stop()
        self.task_status_str = "錯誤"
        self.update_status_summary()
        self.set_ui_enabled(True)
        title, msg = self.worker.get_error_message(err_msg)
        QMessageBox.critical(self, title, msg)

    def set_ui_enabled(self, enabled):
        self.txt_src_path.setEnabled(enabled)
        self.txt_out_path.setEnabled(enabled)
        self.txt_start_row.setEnabled(enabled)
        self.txt_end_row.setEnabled(enabled)
        self.txt_src_col.setEnabled(enabled)
        self.txt_tgt_col.setEnabled(enabled)
        self.translation_panel.set_enabled(enabled)
        self.edit_panel.set_enabled(enabled)
        
        if enabled:
            self.btn_start.setEnabled(True)
            self.update_start_button_ui()

    def switch_sidebar_tab(self, tab_name):
        is_task_running = self.worker is not None and self.worker.isRunning()

        # 判斷點選的是否為當前活躍的分頁
        is_same_tab = False
        if tab_name == "translate" and self.sidebar_stacked.currentWidget() == self.translation_panel:
            is_same_tab = True
        elif tab_name == "edit" and self.sidebar_stacked.currentWidget() == self.edit_panel:
            is_same_tab = True

        # 如果任務正在處理中，禁止切換到其他功能面板，僅允許收合/展開當前面板
        if is_task_running and not is_same_tab:
            return

        if self.sidebar.isVisible() and is_same_tab:
            # 收合
            self.sidebar.setVisible(False)
            self.v_line.setVisible(False)
            self.left_container.setFixedWidth(SIDEBAR_MIN_WIDTH)
            self.btn_translate.setProperty("active", False)
            self.btn_edit.setProperty("active", False)
        else:
            # 展開並切換
            self.sidebar.setVisible(True)
            self.v_line.setVisible(True)
            self.left_container.setFixedWidth(SIDEBAR_FULL_WIDTH)
            
            if tab_name == "translate":
                self.sidebar_stacked.setCurrentWidget(self.translation_panel)
                self.btn_translate.setProperty("active", True)
                self.btn_edit.setProperty("active", False)
                self.content_stack.setCurrentWidget(self.preview_panel)
            elif tab_name == "edit":
                self.sidebar_stacked.setCurrentWidget(self.edit_panel)
                self.btn_translate.setProperty("active", False)
                self.btn_edit.setProperty("active", True)
                if self.edit_content_panel.table_model.all_rows:
                    self.content_stack.setCurrentWidget(self.edit_content_panel)
                else:
                    self.content_stack.setCurrentWidget(self.preview_panel)
                
        # 刷新按鈕樣式
        self.btn_translate.style().polish(self.btn_translate)
        self.btn_edit.style().polish(self.btn_edit)
        
        # 更新開始按鈕狀態字樣
        self.update_start_button_ui()
        
        # 切換面板後立即儲存狀態
        self.save_settings()

    def save_settings(self):
        # 視窗幾何位置與大小文字化儲存
        is_max = self.isMaximized()
        geom = self.normalGeometry() if is_max else self.geometry()
        
        # 組合 Active Tab 狀態
        if not self.sidebar.isVisible():
            active_tab = "hidden"
        elif self.sidebar_stacked.currentWidget() == self.translation_panel:
            active_tab = "translate"
        else:
            active_tab = "edit"

        # 確保在儲存前更新最新狀態面板的展開高度
        if self.status_expanded:
            sizes = self.right_splitter.sizes()
            if len(sizes) > 1:
                self.status_expanded_height = sizes[1]

        data = {
            "window": {
                "x": geom.x(),
                "y": geom.y(),
                "width": geom.width(),
                "height": geom.height(),
                "is_maximized": is_max
            },
            "main": {
                "source_path": self.txt_src_path.text().strip(),
                "output_path": self.txt_out_path.text().strip(),
                "start_row": self.txt_start_row.text(),
                "end_row": self.txt_end_row.text(),
                "src_col": self.txt_src_col.text(),
                "tgt_col": self.txt_tgt_col.text(),
                "active_tab": active_tab
            },
            "panels": {
                "translate": self.translation_panel.get_config(),
                "edit": self.edit_panel.get_config(),
                "status": {
                    "expanded_height": self.status_expanded_height,
                    "collapsed": not self.status_expanded
                },
                "files": {
                    "collapsed": not self.files_content_widget.isVisible()
                },
                "preview": {
                    "first_row_header": self.preview_panel.is_first_row_header()
                }
            }
        }
        self.settings_manager.save(data)

    def restore_settings(self):
        data = self.settings_manager.load()
        if not data:
            return
            
        try:
            # 1. 恢復視窗幾何大小與位置
            if "window" in data:
                w_data = data["window"]
                x = w_data.get("x", 100)
                y = w_data.get("y", 100)
                width = w_data.get("width", WINDOW_DEFAULT_WIDTH)
                height = w_data.get("height", WINDOW_DEFAULT_HEIGHT)
                self.setGeometry(x, y, width, height)
                if w_data.get("is_maximized", False):
                    self.showMaximized()
            
            # 2. 恢復主程式欄位與狀態
            if "main" in data:
                m_data = data["main"]
                self.txt_src_path.setText(m_data.get("source_path", ""))
                self.txt_out_path.setText(m_data.get("output_path", ""))
                
                # 檢查點：開啟程式時兩者不為空且內容相同
                src_path = self.txt_src_path.text().strip()
                out_path = self.txt_out_path.text().strip()
                if src_path and out_path and src_path == out_path:
                    QMessageBox.warning(self, "路徑重複", "偵測到儲存的來源 CSV 與輸出 CSV 路徑相同！已自動清空輸出路徑以防檔案毀損。")
                    self.txt_out_path.clear()
                    
                self.txt_start_row.setText(m_data.get("start_row", "2"))
                self.txt_end_row.setText(m_data.get("end_row", ""))
                self.txt_src_col.setText(m_data.get("src_col", "1"))
                self.txt_tgt_col.setText(m_data.get("tgt_col", "2"))
                
                # 恢復活躍面板
                active_tab = m_data.get("active_tab", "translate")
                if active_tab == "hidden":
                    self.sidebar.setVisible(False)
                    self.v_line.setVisible(False)
                    self.left_container.setFixedWidth(SIDEBAR_MIN_WIDTH)
                    self.btn_translate.setProperty("active", False)
                    self.btn_edit.setProperty("active", False)
                else:
                    self.switch_sidebar_tab(active_tab)

            # 3. 分配並恢復面板專屬組態區段
            if "panels" in data:
                p_data = data["panels"]
                self.translation_panel.set_config(p_data.get("translate", {}))
                self.edit_panel.set_config(p_data.get("edit", {}))
                
                # 恢復展開與折疊設定
                status_cfg = p_data.get("status", {})
                self.status_expanded_height = status_cfg.get("expanded_height", 250)
                status_collapsed = status_cfg.get("collapsed", False)
                self.status_expanded = not status_collapsed
                self.btn_toggle_status.setText("▲" if self.status_expanded else "▼")
                self.txt_log.setVisible(self.status_expanded)
                if not self.status_expanded:
                    self.grp_status.setMinimumHeight(0)
                    self.grp_status.setMaximumHeight(50)
                else:
                    self.grp_status.setMinimumHeight(140)
                    self.grp_status.setMaximumHeight(16777215)
                
                files_cfg = p_data.get("files", {})
                files_collapsed = files_cfg.get("collapsed", False)
                if files_collapsed:
                    self.files_content_widget.setVisible(False)
                    self.btn_toggle_files.setText("▼")
                else:
                    self.files_content_widget.setVisible(True)
                    self.btn_toggle_files.setText("▲")
                
                # 恢復預覽設定
                preview_cfg = p_data.get("preview", {})
                is_hdr = preview_cfg.get("first_row_header", False)
                self.preview_panel.set_first_row_header(is_hdr)
                self.edit_content_panel.set_first_row_header(is_hdr)
            
            # 恢復設定後更新開始按鈕狀態字樣
            self.update_start_button_ui()
        except Exception:
            pass

    def toggle_files_panel(self):
        collapsed = self.files_content_widget.isVisible()
        self.files_content_widget.setVisible(not collapsed)
        self.btn_toggle_files.setText("▼" if collapsed else "▲")
        self.save_settings()

    def toggle_status_panel(self):
        self.status_expanded = not self.status_expanded
        self.txt_log.setVisible(self.status_expanded)
        self.btn_toggle_status.setText("▲" if self.status_expanded else "▼")
        
        if self.status_expanded:
            self.grp_status.setMinimumHeight(140)
            self.grp_status.setMaximumHeight(16777215)
            
            sizes = self.right_splitter.sizes()
            if len(sizes) > 1:
                total_h = sum(sizes)
                status_h = max(140, self.status_expanded_height)
                preview_h = max(200, total_h - status_h)
                if preview_h < 200:
                    preview_h = 200
                    status_h = max(140, total_h - 200)
                self.right_splitter.setSizes([preview_h, status_h])
        else:
            sizes = self.right_splitter.sizes()
            if len(sizes) > 1 and sizes[1] > 100:
                self.status_expanded_height = sizes[1]
                
            header_h = self.status_header_widget.sizeHint().height() + 30
            if header_h < 50:
                header_h = 50
                
            self.grp_status.setMinimumHeight(0)
            self.grp_status.setMaximumHeight(header_h)
            
            sizes = self.right_splitter.sizes()
            if len(sizes) > 1:
                total_h = sum(sizes)
                self.right_splitter.setSizes([total_h - header_h, header_h])
                
        self.save_settings()

    def on_splitter_moved(self, pos, index):
        if self.status_expanded:
            sizes = self.right_splitter.sizes()
            if len(sizes) > 1:
                self.status_expanded_height = sizes[1]

    def showEvent(self, event):
        super().showEvent(event)
        if not self.settings_restored:
            self.settings_restored = True
            self.apply_splitter_sizes()

    def apply_splitter_sizes(self):
        total_h = self.right_splitter.height()
        handle_w = self.right_splitter.handleWidth()
        available_h = total_h - handle_w
        
        if self.status_expanded:
            status_h = max(140, self.status_expanded_height)
            preview_h = max(200, available_h - status_h)
            if preview_h < 200:
                preview_h = 200
                status_h = max(140, available_h - 200)
            self.right_splitter.setSizes([preview_h, status_h])
        else:
            header_h = self.status_header_widget.sizeHint().height() + 30
            if header_h < 50:
                header_h = 50
            preview_h = max(200, available_h - header_h)
            self.right_splitter.setSizes([preview_h, header_h])

    def get_active_panel(self):
        if self.sidebar.isVisible() and self.sidebar_stacked.currentWidget() == self.edit_panel:
            return self.edit_panel
        return self.translation_panel

    def get_start_button_state(self) -> str:
        if self.worker is not None and self.worker.isRunning():
            if self.worker._is_cancelled:
                return "disabled"
            else:
                return "critical"
        return "normal"

    def update_start_button_ui(self):
        state = self.get_start_button_state()
        panel = self.get_active_panel()
        text = panel.get_start_button_text(state)
        self.btn_start.setText(text)
        
        if state == "disabled":
            self.btn_start.setEnabled(False)
            self.btn_start.setStyleSheet("background-color: #24283b; color: #565f89;")
        elif state == "critical":
            self.btn_start.setEnabled(True)
            self.btn_start.setStyleSheet("background-color: #f7768e; color: #1a1b26;")
        else: # normal
            self.btn_start.setEnabled(True)
            self.btn_start.setStyleSheet("") # 恢復 QSS 原生樣式

    def on_start_button_clicked(self):
        state = self.get_start_button_state()
        if state == "disabled":
            return
        panel = self.get_active_panel()
        panel.handle_start_button_click(self, state)

    def cancel_task(self):
        if self.worker:
            self.task_status_str = "正在中斷工作..."
            self.update_status_summary()
            self.worker.cancel()
            self.update_start_button_ui()

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)
