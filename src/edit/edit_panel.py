# src/edit/edit_panel.py
try:
    import regex as re_engine
    HAS_ADVANCED_REGEX = True
except ImportError:
    import re as re_engine
    HAS_ADVANCED_REGEX = False

from plugin_sdk.panel_base import BasePluginPanel
from plugin_sdk import theme
from PyQt6.QtWidgets import QLabel, QComboBox, QLineEdit, QPushButton, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QObject, pyqtSignal


class _RegexReplaceWorker(QObject):
    progress = pyqtSignal(int, int)   # current, total
    finished = pyqtSignal(str)        # "finished" | "error" | "cancelled"
    log_emitted = pyqtSignal(str, str) # level, message

    def __init__(self, csv_data, visible_indices, dst_col, compiled_pattern, replacement_str):
        super().__init__()
        self.csv_data = csv_data
        self.visible_indices = visible_indices
        self.dst_col = dst_col
        self.compiled_pattern = compiled_pattern
        self.replacement_str = replacement_str
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        total = len(self.visible_indices)
        for idx, row_idx in enumerate(self.visible_indices):
            if self._cancelled:
                self.finished.emit("cancelled")
                return

            try:
                row = self.csv_data.all_rows[row_idx]
                # 確保列長度足夠，避免 index out of range 造成崩潰
                while len(row) <= self.dst_col:
                    row.append("")

                src_val = row[self.dst_col]

                # Worker 執行期防護
                try:
                    new_val = self.compiled_pattern.sub(self.replacement_str, src_val)
                    row[self.dst_col] = new_val
                except Exception as e:
                    # 發生錯誤時：把錯誤訊息印到日誌面板，不變更資料內容。
                    self.log_emitted.emit("ERROR", f"列 {row_idx + 1} 取代失敗: {str(e)}")
            except Exception:
                pass

            self.progress.emit(idx + 1, total)

        self.finished.emit("finished")


class EditPanel(BasePluginPanel):
    _UUID = "4e47a9e3-8287-48f8-b39f-26b669fcf72a"
    _N_NON_COL_OPTIONS = 0

    def __init__(self, parent=None, context=None):
        super().__init__(
            parent=parent,
            title_text="編輯",
            require_data_loading=True,
            context=context,
        )
        self._worker = None
        self._config_dst_col = 0
        self._config_mode = 0  # 0: PCRE, 1: BRE (Sed)
        self._config_find_text = ""
        self._config_replace_text = ""
        self._is_replace_expanded = True
        self._setup_ui()

    def _setup_ui(self):
        # 建立折疊控制按鈕 (Header)
        self.btn_toggle_replace = QPushButton("▼ 批次取代")
        # 設定游標為點擊手勢
        self.btn_toggle_replace.setCursor(Qt.CursorShape.PointingHandCursor)
        # 套用去按鈕化的純文字標題樣式
        self.btn_toggle_replace.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                text-align: left;
                font-weight: bold;
                font-size: {theme.getTitleFontSize()}px;
                color: {theme.getTitleTextColor()};
                padding: 5px 0px;
            }}
            QPushButton:hover {{
                color: #89ddff;
            }}
        """)
        self.btn_toggle_replace.clicked.connect(self._toggle_replace_panel)
        self.controls_layout.addWidget(self.btn_toggle_replace)

        # 建立子面板容器 (Content Area)與其 Layout
        self.replace_content_widget = QWidget()
        replace_layout = QVBoxLayout()
        replace_layout.setContentsMargins(0, 0, 0, 0)
        self.replace_content_widget.setLayout(replace_layout)

        # 1. 說明文字 QLabel (移入子面板內部最上方)
        self.lbl_desc = QLabel()
        if HAS_ADVANCED_REGEX:
            self.lbl_desc.setText("進階模式 (支援 \\U, \\L 大小寫轉換等進階語法)")
        else:
            self.lbl_desc.setText("內建模式 (基礎功能。若需大小寫轉換，請於環境中安裝 regex 套件)")
        theme.applyStandardLabelStyle(self.lbl_desc)
        self.lbl_desc.setWordWrap(True)
        replace_layout.addWidget(self.lbl_desc)

        # 2. 目標欄位
        lbl_dst = QLabel("目標欄位")
        theme.applyStandardLabelStyle(lbl_dst)
        replace_layout.addWidget(lbl_dst)

        self.combo_dst_col = QComboBox()
        theme.applyStandardComboBoxStyle(self.combo_dst_col)
        self.combo_dst_col.currentIndexChanged.connect(self._on_dst_col_changed)
        replace_layout.addWidget(self.combo_dst_col)

        # 3. 處理模式
        lbl_mode = QLabel("處理模式")
        theme.applyStandardLabelStyle(lbl_mode)
        replace_layout.addWidget(lbl_mode)

        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["正規表達式 (PCRE)", "Sed 語法 (BRE)"])
        theme.applyStandardComboBoxStyle(self.combo_mode)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        replace_layout.addWidget(self.combo_mode)

        # 4. 尋找
        lbl_find = QLabel("尋找")
        theme.applyStandardLabelStyle(lbl_find)
        replace_layout.addWidget(lbl_find)

        self.edit_find = QLineEdit()
        theme.applyStandardLineEditStyle(self.edit_find)
        self.edit_find.textChanged.connect(self._on_find_changed)
        replace_layout.addWidget(self.edit_find)

        # 5. 取代為
        lbl_replace = QLabel("取代為")
        theme.applyStandardLabelStyle(lbl_replace)
        replace_layout.addWidget(lbl_replace)

        self.edit_replace = QLineEdit()
        theme.applyStandardLineEditStyle(self.edit_replace)
        self.edit_replace.textChanged.connect(self._on_replace_changed)
        replace_layout.addWidget(self.edit_replace)

        # 7. 主要動作按鈕 (移入容器內部最下方)
        self.btn_start = QPushButton("開始取代")
        theme.applyPrimaryButtonStyle(self.btn_start, is_running=False)
        self.btn_start.clicked.connect(self._on_btn_clicked)
        replace_layout.addWidget(self.btn_start)

        # 將容器加入主 layout
        self.controls_layout.addWidget(self.replace_content_widget)

        # 所有子面板加入完畢後，在 controls_layout 的最底端加入 addStretch()
        self.controls_layout.addStretch()

    def _ui_to_stored(self, ui_index: int) -> int:
        return ui_index - self._N_NON_COL_OPTIONS

    def _stored_to_ui(self, stored: int) -> int:
        return stored + self._N_NON_COL_OPTIONS

    def _on_dst_col_changed(self, ui_index: int) -> None:
        self._config_dst_col = self._ui_to_stored(ui_index)

    def _on_mode_changed(self, index: int) -> None:
        self._config_mode = index

    def _on_find_changed(self, text: str) -> None:
        self._config_find_text = text

    def _on_replace_changed(self, text: str) -> None:
        self._config_replace_text = text

    def _toggle_replace_panel(self) -> None:
        self._is_replace_expanded = not self._is_replace_expanded
        self.replace_content_widget.setVisible(self._is_replace_expanded)
        if self._is_replace_expanded:
            self.btn_toggle_replace.setText("▼ 批次取代")
        else:
            self.btn_toggle_replace.setText("▶ 批次取代")

    def on_csv_data_refreshed(self) -> None:
        if not self.context or not self.context.is_data_loaded:
            return

        csv_data = self.context.csv_data
        limit = max(
            csv_data.num_cols,
            self._config_dst_col + 1,
        )

        self.combo_dst_col.blockSignals(True)
        try:
            self.combo_dst_col.clear()
            for col in range(limit):
                header = csv_data.get_column_header(col)
                self.combo_dst_col.addItem(header)

            ui_dst = self._stored_to_ui(self._config_dst_col)
            self.combo_dst_col.setCurrentIndex(ui_dst)
        finally:
            self.combo_dst_col.blockSignals(False)

    def _internal_get_package_name(self) -> str:
        return "edit_panel"

    def _internal_get_uuid(self) -> str:
        return self._UUID

    def _internal_serialize_config(self) -> dict:
        return {
            "dst_col": self._config_dst_col,
            "mode": self._config_mode,
            "find_text": self._config_find_text,
            "replace_text": self._config_replace_text,
        }

    def _internal_deserialize_config(self, data: dict) -> None:
        self._config_dst_col = data.get("dst_col", 0)
        self._config_mode = data.get("mode", 0)
        self._config_find_text = data.get("find_text", "")
        self._config_replace_text = data.get("replace_text", "")

        ui_dst = self._stored_to_ui(self._config_dst_col)

        self.combo_dst_col.blockSignals(True)
        self.combo_mode.blockSignals(True)
        self.edit_find.blockSignals(True)
        self.edit_replace.blockSignals(True)
        try:
            max_dst = self.combo_dst_col.count() - 1
            safe_dst = max(0, min(ui_dst, max_dst)) if max_dst >= 0 else 0
            self.combo_dst_col.setCurrentIndex(safe_dst)

            self.combo_mode.setCurrentIndex(self._config_mode)
            self.edit_find.setText(self._config_find_text)
            self.edit_replace.setText(self._config_replace_text)
        finally:
            self.combo_dst_col.blockSignals(False)
            self.combo_mode.blockSignals(False)
            self.edit_find.blockSignals(False)
            self.edit_replace.blockSignals(False)

    def _internal_set_enabled(self, enabled: bool) -> None:
        super()._internal_set_enabled(enabled)
        self.combo_dst_col.setEnabled(enabled)
        self.combo_mode.setEnabled(enabled)
        self.edit_find.setEnabled(enabled)
        self.edit_replace.setEnabled(enabled)

    def _validate_regex(self, pattern_str: str, replace_str: str, is_sed_mode: bool) -> tuple[bool, str, object]:
        import re

        # 1. 若為 Sed 模式，進行括號反轉轉譯
        if is_sed_mode:
            # 將原本的 \( 轉為 (, \) 轉為 )，未跳脫的 ( 轉為 \(, ) 轉為 \)
            # 簡單的實作方式：先將 \\ 替換為暫存字元，處理括號後再還原
            temp_pattern = pattern_str.replace(r"\\", "\x00")
            temp_pattern = temp_pattern.replace(r"\(", "\x01").replace(r"\)", "\x02")
            temp_pattern = temp_pattern.replace("(", r"\(").replace(")", r"\)")
            temp_pattern = temp_pattern.replace("\x01", "(").replace("\x02", ")")
            pattern_str = temp_pattern.replace("\x00", r"\\")

        # 2. 測試編譯
        try:
            compiled = re_engine.compile(pattern_str)
        except Exception as e:
            return False, f"尋找字串語法錯誤: {str(e)}", None

        # 3. 靜態掃描取代字串中的群組參照
        max_groups = compiled.groups
        named_groups = compiled.groupindex

        # 暫時移除跳脫的斜線 (如 \\1) 避免干擾判斷
        clean_repl = replace_str.replace(r"\\", "")

        # 檢查 \1, \2 ... \99 形式
        refs = re.findall(r'\\(\d+)', clean_repl)
        for ref in refs:
            if int(ref) > max_groups:
                return False, f"取代字串錯誤：參照了不存在的群組 \\{ref} (目前僅有 {max_groups} 個群組)", None

        # 檢查 \g<name> 或 \g<1> 形式
        g_refs = re.findall(r'\\g<([^>]+)>', clean_repl)
        for ref in g_refs:
            if ref.isdigit():
                if int(ref) > max_groups:
                    return False, f"取代字串錯誤：參照了不存在的群組 \\g<{ref}>", None
            elif ref not in named_groups:
                return False, f"取代字串錯誤：參照了不存在的命名群組 \\g<{ref}>", None

        return True, "", compiled

    def _on_btn_clicked(self):
        # 1. 執行前防呆
        if not self.context or not self.context.is_data_loaded:
            self.api.write_log("WARNING", "請先載入 CSV 資料")
            self.api.update_status("❌ 參數錯誤：未載入資料")
            return

        find_text = self._config_find_text
        replace_text = self._config_replace_text
        mode = self._config_mode
        dst_col = self._config_dst_col

        num_cols = self.context.csv_data.num_cols
        if dst_col < 0 or dst_col >= num_cols:
            self.api.write_log("WARNING", f"欄位索引超出範圍（共 {num_cols} 欄）")
            self.api.update_status("❌ 參數錯誤：欄位索引越界")
            return

        # 呼叫靜態語法分析器進行驗證
        is_valid, err_msg, compiled_pattern = self._validate_regex(
            find_text, replace_text, mode == 1
        )
        if not is_valid:
            self.api.update_status(f"❌ 錯誤：{err_msg}")
            self.api.write_log("ERROR", err_msg)
            return

        # 正式啟動任務
        visible_indices = self.context.csv_data.get_visible_indices()
        if not visible_indices:
            self.api.write_log("INFO", "沒有可見的資料列需要處理")
            self.api.update_status("ℹ️ 無需處理")
            return

        self._worker = _RegexReplaceWorker(
            csv_data=self.context.csv_data,
            visible_indices=visible_indices,
            dst_col=dst_col,
            compiled_pattern=compiled_pattern,
            replacement_str=replace_text
        )
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.log_emitted.connect(self.api.write_log)

        self.api.run_worker(
            self._worker,
            task_name="正規表達式取代",
            total=len(visible_indices),
            initial_log=f"開始取代任務：尋找 '{find_text}' 取代為 '{replace_text}'",
            prevent_sleep=True
        )

    def _on_worker_finished(self, status: str):
        if status == "finished":
            self.context.csv_data.set_modified(True)
            self.context.csv_data.data_changed.emit()
            self.api.request_silent_save()
            self.api.write_log("SUCCESS", "批次取代任務已完成")
            self.api.update_status("✅ 取代完成")
        elif status == "cancelled":
            self.api.write_log("WARNING", "取代任務已取消")
            self.api.update_status("⚠️ 任務已取消")
