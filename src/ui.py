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

from settings_manager import SettingsManager
from data_editor.data_editor_panel import DataEditorPanel
from ui_constants import (
    WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    SIDEBAR_FULL_WIDTH, SIDEBAR_WIDTH, ACTIVITY_BAR_WIDTH,
    PROGRESS_BAR_WIDTH, START_BUTTON_MIN_WIDTH,
    INPUT_COL_MAX_WIDTH,
    SWAP_ICON_SIZE,
)
from ui_mixins import UiStateMixin, SettingsMixin, WorkerMixin
from in_out.io_panel import IoPanel
from in_out.io_panel_validator import validate_paths_not_equal
from status_panel import StatusPanel
from left_panel import LeftPanel


class MainWindow(UiStateMixin, SettingsMixin, WorkerMixin, QMainWindow):
    """
    主視窗：負責 UI 佈局建構與初始化。
    各項業務邏輯透過 Mixin 繼承組合：
      UiStateMixin    — 日誌、控制項啟停、分頁切換、按鈕狀態
      SettingsMixin   — 設定持久化與 Splitter 管理
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

        # Config 物件字典，由 SettingsManager.load() 填入、AppContext 存取
        self._configs = {}

        # WorkerMixin 私有狀態
        self._worker_sleep_prevented = False

        # Splitter 初始化旗標（替代舊的 settings_restored）
        self._splitter_applied = False

        # 初始狀態與計時字串，防止 UI 面板提早呼叫狀態更新時出錯
        self.elapsed_time_str = "00:00:00"
        self.task_status_str = "就緒"

        # 1. 建立空視窗（預設位置、預設尺寸）
        self.init_ui()

        # 2. SettingsManager 讀入設定，在 AppContext 建立所有 Config 物件
        self._configs = SettingsManager.load(self.settings_path)

        # 3. 套用視窗組態（座標、大小）
        self.apply_window_config()

        # 4. 各面板自行從 AppContext 取得組態並還原 UI 狀態
        self._restore_all_panel_configs()

    def init_ui(self):
        self.setWindowTitle("CsvTranslator - CSV 批次翻譯工具")
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # 實例化 CsvData Model (單例，與 MainWindow 共存亡)
        from common_data.csv_data import CsvData
        self.csv_data = CsvData()

        # 建立 AppContext (必須先建立，因為面板需要使用)
        from base.app_context import AppContext
        self.context = AppContext(self)

        main_widget = QWidget()
        main_widget.setObjectName("mainContainer")
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 建立獨立面板
        # 實例化包含所有子面板的功能 Package 的側面板
        self.left_panel = LeftPanel(parent=self, context=self.context)
        self.io_panel = IoPanel(parent=self, context=self.context)
        self.status_panel = StatusPanel(parent=self, context=self.context)

        # 連接 CSVReader 與 CSVWriter 信號 (自 io_panel)
        self.io_panel.loader.load_completed.connect(self.on_csv_load_completed)
        self.io_panel.loader.task_started.connect(self.on_task_started)
        self.io_panel.loader.task_finished.connect(self.on_task_finished)
        self.io_panel.writer.task_started.connect(self.on_task_started)
        self.io_panel.writer.task_finished.connect(self.on_task_finished)
        self.io_panel.writer.save_completed.connect(self.on_csv_save_completed)

        # 連接 LeftPanel 管理的信號
        self.left_panel.plugin_removed.connect(self.on_plugin_removed)
        self.left_panel.settings_save_requested.connect(self.save_settings)

        main_layout.addWidget(self.left_panel)

        # 右側面板
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)
        right_panel.addWidget(self.io_panel)

        # 連接 IO Panel 訊號
        self.io_panel.source_file_changed.connect(self.on_source_file_changed)

        # 來源預覽與日誌面板採用 QSplitter 垂直排列
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.setObjectName("rightSplitter")

        # 內容面板
        self.edit_content_panel = DataEditorPanel(context=self.context)
        self.csv_data.modified_changed.connect(self.io_panel.on_modified_changed)

        self.status_panel.setMinimumHeight(140)
        # 連接 StatusPanel 訊號
        self.status_panel.toggle_clicked.connect(self.on_status_panel_toggle)

        self.right_splitter.addWidget(self.edit_content_panel)
        self.right_splitter.addWidget(self.status_panel)
        self.right_splitter.setStretchFactor(0, 1)
        self.right_splitter.setStretchFactor(1, 0)
        self.right_splitter.splitterMoved.connect(self.on_splitter_moved)

        right_panel.addWidget(self.right_splitter)
        main_layout.addLayout(right_panel, stretch=1)

        self.apply_style()


    def on_status_panel_toggle(self, collapsed: bool) -> None:
        cfg = self.context.status_panel_config
        if not collapsed:
            self.status_panel.setMinimumHeight(140)
            self.status_panel.setMaximumHeight(16777215)

            sizes = self.right_splitter.sizes()
            if len(sizes) > 1:
                total_h = sum(sizes)
                editor_h, status_h = self._calc_splitter_sizes(total_h, cfg.expanded_height)
                self.right_splitter.setSizes([editor_h, status_h])
        else:
            sizes = self.right_splitter.sizes()
            if len(sizes) > 1 and sizes[1] > 100:
                cfg.expanded_height = sizes[1]

            header_h = self.status_panel.header_height()
            self.status_panel.setMinimumHeight(0)
            self.status_panel.setMaximumHeight(header_h)

            sizes = self.right_splitter.sizes()
            if len(sizes) > 1:
                total_h = sum(sizes)
                self.right_splitter.setSizes([total_h - header_h, header_h])

    def on_csv_load_completed(self, data) -> None:
        # 💉 --- 記憶體吐真劑開始 ---
        import gc
        
        print("--- 準備接收新資料 ---")
        if hasattr(self, 'csv_data') and hasattr(self.csv_data, 'all_rows') and self.csv_data.all_rows:
            old_rows = self.csv_data.all_rows
            
            # 1. 斬斷當前模型對舊資料的掌控
            self.csv_data.all_rows = []
            
            # 2. 強制 Python 立刻去收垃圾
            gc.collect()
            
            # 3. 抓出綁匪：取得記憶體中所有還牽著 old_rows 的物件
            referrers = gc.get_referrers(old_rows)
            
            # 過濾掉我們這段偵錯代碼自己產生的 frame
            suspicious = [r for r in referrers if type(r).__name__ not in ('frame', 'tuple')]
            
            if suspicious:
                print(f"🚨 警告！發現 {len(suspicious)} 個綁匪扣留了舊資料：")
                for i, ref in enumerate(suspicious):
                    if isinstance(ref, dict):
                        # 若綁匪是某個物件的 __dict__，印出它的屬性來確認是誰
                        keys = list(ref.keys())
                        print(f"  [綁匪 {i+1}] 某個物件的內部，它的變數有: {keys[:5]}...")
                    elif isinstance(ref, list):
                        print(f"  [綁匪 {i+1}] 某個 List！可能是 History 陣列，長度: {len(ref)}")
                    else:
                        print(f"  [綁匪 {i+1}] 型別: {type(ref)}")
            else:
                print("✅ 舊資料已無人綁架，可完美回收。")
        # 💉 --- 記憶體吐真劑結束 ---

        # 1. 將資料寫入 Model，這會自動觸發各面板訂閱的刷新信號
        self.csv_data.set_csv_data(
            all_rows=data["all_rows"],
            delimiter=data["delimiter"],
            encoding=data["encoding"],
            file_path=data["file_path"],
            num_cols=data["num_cols"]
        )
        
        # 2. 自動展開側面板，切換到第一個功能（過濾）
        if data["all_rows"]:
            self.left_panel.switch_sidebar_tab("filter", force_expand=True)

    def on_source_file_changed(self, file_path: str) -> None:
        self.csv_data.set_csv_data([], ",", "utf-8", None)

    def on_plugin_removed(self, plugin_key: str) -> None:
        self._configs.pop(plugin_key, None)

    def on_csv_save_completed(self, out_path: str) -> None:
        self.csv_data.set_modified(False)


    def silent_save_edit_data(self) -> None:
        out_path = self.io_panel.txt_out_path.text().strip()
        if not out_path:
            self.append_log("ERROR", "自動存檔失敗：未指定輸出 CSV 檔案路徑！")
            return

        src_path = self.io_panel.txt_src_path.text().strip()
        if src_path and out_path:
            norm_src = os.path.normpath(src_path.strip()).lower()
            norm_out = os.path.normpath(out_path.strip()).lower()
            if norm_src == norm_out:
                self.append_log("ERROR", "自動存檔失敗：來源 CSV 與輸出 CSV 路徑相同！")
                return

        all_rows = self.edit_content_panel.get_all_rows()
        if not all_rows:
            self.append_log("ERROR", "自動存檔失敗：沒有資料可儲存。")
            return

        delimiter = self.edit_content_panel.get_delimiter()

        try:
            self.io_panel.writer.start_save_task(out_path, all_rows, delimiter, silent=True)
        except Exception as e:
            self.append_log("ERROR", f"自動靜默存檔失敗：{str(e)}")

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
        QPushButton[type="activity"] {
            background-color: transparent;
            border: none;
            border-radius: 8px;
            padding: 0px;
        }
        QPushButton[type="activity"]:hover {
            background-color: #2e3047;
        }
        QPushButton[type="activity"][active="true"] {
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

        QPushButton#btnSave {
            background-color: #ff9e64;
            color: #1a1b26;
            font-size: 15px;
            padding: 12px;
        }
        QPushButton#btnSave:hover {
            background-color: #ffb86c;
        }
        QPushButton#btnSave:disabled {
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

        QPushButton#btnSwap, QPushButton#btnSwapRules {
            background-color: #3b4261;
            border: none;
            border-radius: 6px;
            padding: 0px;
        }
        QPushButton#btnSwap:hover, QPushButton#btnSwapRules:hover {
            background-color: #414868;
        }
        QPushButton#btnSwap:pressed, QPushButton#btnSwapRules:pressed {
            background-color: #2e3c64;
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


    # ── 視窗關閉事件 ─────────────────────────────────────────────────────────

    def closeEvent(self, event):
        """Qt 事件覆寫：視窗關閉時恢復系統休眠設定並儲存所有設定。
        必須呼叫 super().closeEvent(event) 維持 MRO 鏈完整性。
        """
        if getattr(self, "_worker_sleep_prevented", False):
            self._set_sleep_prevention(False)
        self.save_settings()
        super().closeEvent(event)  # ← MRO 鏈傳遞至 QMainWindow，勿省略
