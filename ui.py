import os
import sys
import time
import csv
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QFrame, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, QSettings, QSize
from PyQt6.QtGui import QIntValidator, QFont, QIcon

from utils import detect_encoding, detect_delimiter
from translation_worker import CSVTranslatorWorker
from translation_panel import TranslationPanel

# 恢復視窗幾何狀態
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.start_time = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_elapsed_time)
        self.settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.ini")
        self.default_dir = os.path.expanduser("~")
        
        self.init_ui()
        self.restore_settings()

    def init_ui(self):
        self.setWindowTitle("CsvTranslator - CSV 批次翻譯工具")
        self.resize(1100, 750)
        self.setMinimumSize(950, 600)
        
        # 主視窗佈局設定
        main_widget = QWidget()
        main_widget.setObjectName("mainContainer")
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ----------------- 左側大容器：合併活動列與設定欄 -----------------
        self.left_container = QFrame()
        self.left_container.setObjectName("leftContainer")
        self.left_container.setFixedWidth(341)  # 預設展開：60 + 1 + 280
        
        left_layout = QHBoxLayout(self.left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # 1. 活動列 (QWidget)
        self.activity_bar = QWidget()
        self.activity_bar.setObjectName("activityBarWidget")
        self.activity_bar.setFixedWidth(60)
        
        activity_layout = QVBoxLayout(self.activity_bar)
        activity_layout.setContentsMargins(10, 15, 10, 15)
        activity_layout.setSpacing(10)
        activity_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "translate.png")
        self.btn_translate = QPushButton()
        self.btn_translate.setObjectName("btnActivityTranslate")
        self.btn_translate.setFixedSize(40, 40)
        self.btn_translate.setIcon(QIcon(icon_path))
        self.btn_translate.setIconSize(QSize(40, 40))
        self.btn_translate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_translate.clicked.connect(self.toggle_sidebar)
        self.btn_translate.setProperty("active", True)
        
        activity_layout.addWidget(self.btn_translate)
        activity_layout.addStretch()
        
        left_layout.addWidget(self.activity_bar)

        # 2. 垂直分割線 (QWidget)
        self.v_line = QWidget()
        self.v_line.setObjectName("sidebarSeparator")
        self.v_line.setFixedWidth(1)
        left_layout.addWidget(self.v_line)

        # 3. 側邊欄：翻譯設定 (QWidget)
        self.sidebar = QWidget()
        self.sidebar.setObjectName("leftSidebarWidget")
        self.sidebar.setFixedWidth(280)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 15, 15, 15)
        sidebar_layout.setSpacing(15)

        # 翻譯設定面板
        self.translation_panel = TranslationPanel()
        sidebar_layout.addWidget(self.translation_panel)
        sidebar_layout.addStretch()

        left_layout.addWidget(self.sidebar)
        
        main_layout.addWidget(self.left_container)

        # ----------------- 右側面板：控制主區域與日誌 -----------------
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)


        # 輸入與輸出面板（2列橫向配置）
        grp_files = QFrame()
        grp_files.setObjectName("rightFrame")
        grp_files_layout = QVBoxLayout(grp_files)
        grp_files_layout.setContentsMargins(15, 12, 15, 12)
        grp_files_layout.setSpacing(10)

        # 標題與段落標頭列（對齊下緣）
        title_row_widget = QWidget()
        title_row_widget.setObjectName("titleRowWidget")
        title_layout = QHBoxLayout(title_row_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(10)
        
        lbl_files_sec = QLabel("輸入與輸出")
        lbl_files_sec.setObjectName("sectionHeader")
        title_layout.addWidget(lbl_files_sec, alignment=Qt.AlignmentFlag.AlignBottom)
        
        title_layout.addStretch()
        
        lbl_title = QLabel("CsvTranslator")
        lbl_title.setObjectName("appTitle")
        title_layout.addWidget(lbl_title, alignment=Qt.AlignmentFlag.AlignBottom)
        
        title_layout.addStretch()
        
        grp_files_layout.addWidget(title_row_widget)

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

        grp_files_layout.addLayout(row1_layout)

        # 第二列：起始/結束行號、來源/目標列號與開始翻譯按鈕
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(15)

        lbl_start_row = QLabel("起始行號：")
        self.txt_start_row = QLineEdit("2")
        self.txt_start_row.setValidator(QIntValidator(1, 9999999))
        self.txt_start_row.setMaximumWidth(80)

        lbl_end_row = QLabel("結束行號：")
        self.txt_end_row = QLineEdit()
        self.txt_end_row.setPlaceholderText("預設至檔尾")
        self.txt_end_row.setValidator(QIntValidator(1, 9999999))
        self.txt_end_row.setMaximumWidth(100)

        lbl_src_col = QLabel("來源列號：")
        self.txt_src_col = QLineEdit("1")
        self.txt_src_col.setValidator(QIntValidator(1, 9999))
        self.txt_src_col.setMaximumWidth(60)

        lbl_tgt_col = QLabel("目標列號：")
        self.txt_tgt_col = QLineEdit("2")
        self.txt_tgt_col.setValidator(QIntValidator(1, 9999))
        self.txt_tgt_col.setMaximumWidth(60)

        self.btn_start = QPushButton("開始")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.setMinimumWidth(150)
        self.btn_start.clicked.connect(self.start_translation)

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

        grp_files_layout.addLayout(row2_layout)
        right_panel.addWidget(grp_files)

        # A. 來源檔案預覽
        grp_preview = QFrame()
        grp_preview.setObjectName("rightFrame")
        grp_preview_layout = QVBoxLayout(grp_preview)
        grp_preview_layout.setContentsMargins(15, 15, 15, 15)
        grp_preview_layout.setSpacing(8)

        # 預覽標頭列（包含狀態訊息）
        preview_header_widget = QWidget()
        preview_header_layout = QHBoxLayout(preview_header_widget)
        preview_header_layout.setContentsMargins(0, 0, 0, 0)
        preview_header_layout.setSpacing(10)

        lbl_preview_title = QLabel("來源檔案預覽 (前 10 行)")
        lbl_preview_title.setObjectName("sectionHeader")
        preview_header_layout.addWidget(lbl_preview_title)

        preview_header_layout.addStretch()

        self.lbl_preview_status = QLabel("尚未選擇來源 CSV 檔案")
        self.lbl_preview_status.setObjectName("previewStatus")
        self.lbl_preview_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        preview_header_layout.addWidget(self.lbl_preview_status)

        grp_preview_layout.addWidget(preview_header_widget)

        self.table_preview = QTableWidget()
        self.table_preview.setRowCount(0)
        self.table_preview.setColumnCount(0)
        self.table_preview.horizontalHeader().setDefaultSectionSize(110)
        self.table_preview.verticalHeader().setDefaultSectionSize(28)
        grp_preview_layout.addWidget(self.table_preview)

        right_panel.addWidget(grp_preview, stretch=3)

        # B. 執行狀態與日誌
        grp_status = QFrame()
        grp_status.setObjectName("rightFrame")
        grp_status_layout = QVBoxLayout(grp_status)
        grp_status_layout.setContentsMargins(15, 15, 15, 15)
        grp_status_layout.setSpacing(8)

        # 狀態與日誌標頭列
        status_header_widget = QWidget()
        status_header_layout = QHBoxLayout(status_header_widget)
        status_header_layout.setContentsMargins(0, 0, 0, 0)
        status_header_layout.setSpacing(15)

        lbl_log_title = QLabel("執行狀態與日誌")
        lbl_log_title.setObjectName("sectionHeader")
        status_header_layout.addWidget(lbl_log_title)

        status_header_layout.addStretch()

        # 狀態訊息：僅顯示已用時間與狀態
        self.elapsed_time_str = "00:00:00"
        self.task_status_str = "就緒"
        self.lbl_status_summary = QLabel("已用時間：00:00:00 | 狀態：就緒")
        status_header_layout.addWidget(self.lbl_status_summary)

        # 進度條：顯示 n/m (筆數)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(150)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0/0")
        status_header_layout.addWidget(self.progress_bar)

        grp_status_layout.addWidget(status_header_widget)

        # 結束行號
        self.txt_log = QTextEdit()
        self.txt_log.setObjectName("logConsole")
        self.txt_log.setReadOnly(True)
        grp_status_layout.addWidget(self.txt_log)

        right_panel.addWidget(grp_status, stretch=4)

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
        QPushButton#btnActivityTranslate {
            background-color: transparent;
            border: none;
            border-radius: 8px;
            padding: 0px;
        }
        QPushButton#btnActivityTranslate:hover {
            background-color: #2e3047;
        }
        QPushButton#btnActivityTranslate[active="true"] {
            background-color: #3b4261;
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



        /* 表格樣式 */
        QTableWidget {
            background-color: #16161e;
            color: #a9b1d6;
            border: 1px solid #2f3047;
            gridline-color: #232433;
            border-radius: 8px;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QTableWidget::item:selected {
            background-color: #2e3c64;
            color: #c0caf5;
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
            background-color: #9ece6a;
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
    def browse_source_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇來源 CSV 檔案", self.default_dir, "CSV 檔案 (*.csv);;所有檔案 (*)"
        )
        if file_path:
            self.txt_src_path.setText(file_path)
            self.default_dir = os.path.dirname(os.path.abspath(file_path))
            # 自動推導輸出檔案路徑
            if not self.txt_out_path.text().strip():
                dir_name, file_name = os.path.split(file_path)
                name, ext = os.path.splitext(file_name)
                default_out = os.path.join(dir_name, f"{name}_translated{ext}")
                self.txt_out_path.setText(default_out)

    def browse_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "選擇儲存輸出 CSV 檔案", self.default_dir, "CSV 檔案 (*.csv);;所有檔案 (*)"
        )
        if file_path:
            self.txt_out_path.setText(file_path)
            self.default_dir = os.path.dirname(os.path.abspath(file_path))

    def on_source_file_changed(self, file_path):
        if not file_path.strip() or not os.path.exists(file_path):
            self.table_preview.clear()
            self.table_preview.setRowCount(0)
            self.table_preview.setColumnCount(0)
            self.lbl_preview_status.setText("請選擇來源檔案，或來源檔案不存在")
            self.txt_end_row.setPlaceholderText("預設至檔尾")
            return
        
        self.load_csv_preview(file_path)

    def load_csv_preview(self, file_path):
        try:
            encoding = detect_encoding(file_path)
            delimiter = detect_delimiter(file_path, encoding)
            
            rows = []
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                reader = csv.reader(f, delimiter=delimiter)
                for i, row in enumerate(reader):
                    if i >= 10:
                        break
                    rows.append(row)
            
            if not rows:
                self.lbl_preview_status.setText("來源檔案為空，無法進行預覽")
                return

            max_cols = max(len(r) for r in rows)
            
            self.table_preview.clear()
            self.table_preview.setRowCount(len(rows))
            self.table_preview.setColumnCount(max_cols)
            
            # 設定列與行標頭
            col_headers = [f"第 {i+1} 欄" for i in range(max_cols)]
            self.table_preview.setHorizontalHeaderLabels(col_headers)
            
            row_headers = [f"第 {i+1} 行" for i in range(len(rows))]
            self.table_preview.setVerticalHeaderLabels(row_headers)
            
            for r_idx, row in enumerate(rows):
                for c_idx in range(max_cols):
                    val = row[c_idx] if c_idx < len(row) else ""
                    item = QTableWidgetItem(val)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    self.table_preview.setItem(r_idx, c_idx, item)
            
            self.table_preview.resizeColumnsToContents()
            self.lbl_preview_status.setText(f"預覽載入完成 (編碼: {encoding}, 分隔符: '{delimiter}')")
            
            # 自動推導輸出檔案路徑
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                total_rows = sum(1 for _ in csv.reader(f, delimiter=delimiter))
            self.txt_end_row.setPlaceholderText(f"預設至檔尾 ({total_rows})")

        except Exception as e:
            self.lbl_preview_status.setText(f"載入預覽失敗: {str(e)}")

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

    def start_translation(self):
        # 如果正在翻譯，按按鈕則觸發 STOP 中斷
        if self.btn_start.text() == "STOP":
            if self.worker:
                self.btn_start.setText("正在停止...")
                self.btn_start.setEnabled(False)
                self.task_status_str = "正在中斷工作..."
                self.update_status_summary()
                self.worker.cancel()
            return

        # 檢查輸入欄位範圍
        src_path = self.txt_src_path.text().strip()
        out_path = self.txt_out_path.text().strip()
        
        if not src_path or not os.path.exists(src_path):
            QMessageBox.warning(self, "輸入錯誤", "請選擇正確的來源 CSV 檔案路徑")
            return
        if not out_path:
            QMessageBox.warning(self, "輸入錯誤", "請指定輸出檔案路徑")
            return
        
        # 讀取並驗證行數欄位
        try:
            start_row = int(self.txt_start_row.text())
            if start_row < 1:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "輸入錯誤", "起始行號必須是大於或等於 1 的正整數")
            return

        end_row = None
        if self.txt_end_row.text().strip():
            try:
                end_row = int(self.txt_end_row.text())
                if end_row < start_row:
                    QMessageBox.warning(self, "輸入錯誤", "結束行號不能小於起始行號")
                    return
            except ValueError:
                QMessageBox.warning(self, "輸入錯誤", "結束行號必須是正整數")
                return

        try:
            src_col = int(self.txt_src_col.text())
            tgt_col = int(self.txt_tgt_col.text())
            if src_col < 1 or tgt_col < 1:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "輸入錯誤", "來源列號與目標列號必須是大於或等於 1 的正整數")
            return

        src_lang = self.translation_panel.get_src_lang()
        tgt_lang = self.translation_panel.get_tgt_lang()

        batch_interval = self.translation_panel.get_batch_interval()
        single_interval = self.translation_panel.get_single_interval()

        # 清空舊 UI 顯示狀態
        self.txt_log.clear()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0/0")
        self.elapsed_time_str = "00:00:00"
        self.task_status_str = "翻譯中..."
        self.update_status_summary()
        
        # 記錄開始時間
        self.start_time = time.time()
        self.timer.start(1000)

        # 如果正在翻譯，按按鈕則觸發 STOP 中斷
        self.btn_start.setText("STOP")
        self.btn_start.setStyleSheet("background-color: #f7768e; color: #1a1b26;")

        self.set_ui_enabled(False)

        # 初始化背景翻譯工作器
        self.worker = CSVTranslatorWorker(
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
        self.worker.progress_updated.connect(self.on_worker_progress)
        self.worker.log_emitted.connect(self.append_log)
        self.worker.finished_successfully.connect(self.on_worker_success)
        self.worker.finished_with_error.connect(self.on_worker_error)
        
        self.worker.start()

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
            QMessageBox.information(self, "中斷", f"已取消翻譯！\n檔案已儲存至：\n{out_path}")
        else:
            self.task_status_str = "完成"
            self.update_status_summary()
            QMessageBox.information(self, "成功", f"翻譯完成！\n檔案已儲存至：\n{out_path}")

    def on_worker_error(self, err_msg):
        self.timer.stop()
        self.task_status_str = "錯誤"
        self.update_status_summary()
        self.set_ui_enabled(True)
        QMessageBox.critical(self, "翻譯中斷", f"翻譯過程發生錯誤：\n{err_msg}")

    def set_ui_enabled(self, enabled):
        self.txt_src_path.setEnabled(enabled)
        self.txt_out_path.setEnabled(enabled)
        self.txt_start_row.setEnabled(enabled)
        self.txt_end_row.setEnabled(enabled)
        self.txt_src_col.setEnabled(enabled)
        self.txt_tgt_col.setEnabled(enabled)
        self.translation_panel.set_enabled(enabled)
        
        if enabled:
            self.btn_start.setEnabled(True)
            self.btn_start.setText("開始")
            self.btn_start.setStyleSheet("") # 恢復 QSS 原生樣式

    def toggle_sidebar(self):
        if self.sidebar.isVisible():
            self.sidebar.setVisible(False)
            self.v_line.setVisible(False)
            self.left_container.setFixedWidth(60)
            self.btn_translate.setProperty("active", False)
        else:
            self.sidebar.setVisible(True)
            self.v_line.setVisible(True)
            self.left_container.setFixedWidth(341)
            self.btn_translate.setProperty("active", True)
        self.btn_translate.style().polish(self.btn_translate)

    def restore_settings(self):
        if not os.path.exists(self.settings_path):
            return
        try:
            settings = QSettings(self.settings_path, QSettings.Format.IniFormat)
            
            geom = settings.value("geometry")
            if geom is not None:
                self.restoreGeometry(geom)
            
            # 恢復視窗最大化狀態
            is_max = settings.value("isMaximized")
            if is_max == "true" or is_max is True:
                self.showMaximized()
            
            # 讀取工作資料夾路徑
            self.default_dir = settings.value("default_dir", os.path.expanduser("~"))
            
            # 恢復使用者輸入欄位設定
            self.txt_start_row.setText(settings.value("start_row", "2"))
            self.txt_end_row.setText(settings.value("end_row", ""))
            self.txt_src_col.setText(settings.value("src_col", "1"))
            self.txt_tgt_col.setText(settings.value("tgt_col", "2"))

            # 讀取批次與單筆間隔時間並驗證其合法性
            batch_val = settings.value("batch_interval", "10")
            if not batch_val.isdigit() or not (10 <= int(batch_val) <= 30):
                batch_val = "10"
            self.translation_panel.set_batch_interval(batch_val)

            single_val = settings.value("single_interval", "1")
            if not single_val.isdigit() or not (1 <= int(single_val) <= 5):
                single_val = "1"
            self.translation_panel.set_single_interval(single_val)
            
            src_lang = settings.value("src_lang", "en")
            self.translation_panel.set_src_lang(src_lang)
                
            tgt_lang = settings.value("tgt_lang", "zh-TW")
            self.translation_panel.set_tgt_lang(tgt_lang)
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            settings = QSettings(self.settings_path, QSettings.Format.IniFormat)
            settings.setValue("geometry", self.saveGeometry())
            settings.setValue("isMaximized", self.isMaximized())
            settings.setValue("default_dir", self.default_dir)
            settings.setValue("start_row", self.txt_start_row.text())
            settings.setValue("end_row", self.txt_end_row.text())
            settings.setValue("src_col", self.txt_src_col.text())
            settings.setValue("tgt_col", self.txt_tgt_col.text())
            settings.setValue("batch_interval", str(self.translation_panel.get_batch_interval()))
            settings.setValue("single_interval", str(self.translation_panel.get_single_interval()))
            settings.setValue("src_lang", self.translation_panel.get_src_lang())
            settings.setValue("tgt_lang", self.translation_panel.get_tgt_lang())
        except Exception:
            pass
        super().closeEvent(event)
