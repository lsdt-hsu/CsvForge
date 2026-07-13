try:
    import regex as re_engine
    HAS_ADVANCED_REGEX = True
except ImportError:
    import re as re_engine
    HAS_ADVANCED_REGEX = False

import re
from PyQt6.QtWidgets import QLabel, QComboBox, QLineEdit, QPushButton
from PyQt6.QtCore import QObject, pyqtSignal
from common_data.task_status import TaskStatus
from plugin_sdk import theme
from edit.base_sub_panel import BaseSubPanel

# 1. 直接遷移原有的 Worker
class _RegexReplaceWorker(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(TaskStatus)
    log_emitted = pyqtSignal(str, str)

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
                self.finished.emit(TaskStatus.CANCELLED)
                return
            try:
                row = self.csv_data.all_rows[row_idx]
                while len(row) <= self.dst_col:
                    row.append("")
                src_val = row[self.dst_col]
                try:
                    new_val = self.compiled_pattern.sub(self.replacement_str, src_val)
                    row[self.dst_col] = new_val
                except Exception as e:
                    self.log_emitted.emit("ERROR", f"列 {row_idx + 1} 取代失敗: {str(e)}")
            except Exception:
                pass
            self.progress.emit(idx + 1, total)
        self.finished.emit(TaskStatus.FINISHED)

# 2. 實作子面板類別
class ReplaceSubPanel(BaseSubPanel):
    def __init__(self, api, context, parent=None):
        # 呼叫 BaseSubPanel 的 __init__，設定標題為 "批次取代"
        super().__init__("批次取代", api, context, parent)
        self._worker = None
        self._config_dst_col = 0
        self._config_mode = 0  # 0: PCRE, 1: BRE (Sed)
        self._config_find_text = ""
        self._config_replace_text = ""
        self._N_NON_COL_OPTIONS = 0
        
        self._setup_ui()

    def _setup_ui(self):
        # 將元件加入繼承自 BaseSubPanel 的 self.content_layout
        self.lbl_desc = QLabel()
        if HAS_ADVANCED_REGEX:
            self.lbl_desc.setText("進階模式 (支援 \\U, \\L 大小寫轉換等進階語法)")
        else:
            self.lbl_desc.setText("內建模式 (基礎功能。若需大小寫轉換，請於環境中安裝 regex 套件)")
        theme.applyStandardLabelStyle(self.lbl_desc)
        self.lbl_desc.setWordWrap(True)
        self.content_layout.addWidget(self.lbl_desc)

        lbl_dst = QLabel("目標欄位")
        theme.applyStandardLabelStyle(lbl_dst)
        self.content_layout.addWidget(lbl_dst)

        self.combo_dst_col = QComboBox()
        theme.applyStandardComboBoxStyle(self.combo_dst_col)
        self.combo_dst_col.currentIndexChanged.connect(self._on_dst_col_changed)
        self.content_layout.addWidget(self.combo_dst_col)

        lbl_mode = QLabel("處理模式")
        theme.applyStandardLabelStyle(lbl_mode)
        self.content_layout.addWidget(lbl_mode)

        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["正規表達式 (PCRE)", "Sed 語法 (BRE)"])
        theme.applyStandardComboBoxStyle(self.combo_mode)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        self.content_layout.addWidget(self.combo_mode)

        lbl_find = QLabel("尋找")
        theme.applyStandardLabelStyle(lbl_find)
        self.content_layout.addWidget(lbl_find)

        self.edit_find = QLineEdit()
        theme.applyStandardLineEditStyle(self.edit_find)
        self.edit_find.textChanged.connect(self._on_find_changed)
        self.content_layout.addWidget(self.edit_find)

        lbl_replace = QLabel("取代為")
        theme.applyStandardLabelStyle(lbl_replace)
        self.content_layout.addWidget(lbl_replace)

        self.edit_replace = QLineEdit()
        theme.applyStandardLineEditStyle(self.edit_replace)
        self.edit_replace.textChanged.connect(self._on_replace_changed)
        self.content_layout.addWidget(self.edit_replace)

        self.btn_start = QPushButton("開始取代")
        theme.applyPrimaryButtonStyle(self.btn_start, is_running=False)
        self.btn_start.clicked.connect(self._on_btn_clicked)
        self.content_layout.addWidget(self.btn_start)

    # --- Config 與 Event 處理 (原封不動遷移) ---
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

    def get_config(self) -> dict:
        return {
            "dst_col": self._config_dst_col,
            "mode": self._config_mode,
            "find_text": self._config_find_text,
            "replace_text": self._config_replace_text,
        }

    def restore_config(self, data: dict) -> None:
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

    def on_data_refreshed(self) -> None:
        if not self.context or not self.context.is_data_loaded:
            return
        csv_data = self.context.csv_data
        limit = max(csv_data.num_cols, self._config_dst_col + 1)

        self.combo_dst_col.blockSignals(True)
        try:
            self.combo_dst_col.clear()
            for col in range(limit):
                self.combo_dst_col.addItem(csv_data.get_column_header(col))
            ui_dst = self._stored_to_ui(self._config_dst_col)
            self.combo_dst_col.setCurrentIndex(ui_dst)
        finally:
            self.combo_dst_col.blockSignals(False)

    # --- 靜態驗證與執行邏輯 ---
    def _validate_regex(self, pattern_str: str, replace_str: str, is_sed_mode: bool) -> tuple[bool, str, object]:
        if is_sed_mode:
            temp_pattern = pattern_str.replace(r"\\", "\x00")
            temp_pattern = temp_pattern.replace(r"\(", "\x01").replace(r"\)", "\x02")
            temp_pattern = temp_pattern.replace("(", r"\(").replace(")", r"\)")
            temp_pattern = temp_pattern.replace("\x01", "(").replace("\x02", ")")
            pattern_str = temp_pattern.replace("\x00", r"\\")

        try:
            compiled = re_engine.compile(pattern_str)
        except Exception as e:
            return False, f"尋找字串語法錯誤: {str(e)}", None

        max_groups = compiled.groups
        named_groups = compiled.groupindex
        clean_repl = replace_str.replace(r"\\", "")

        refs = re.findall(r'\\(\d+)', clean_repl)
        for ref in refs:
            if int(ref) > max_groups:
                return False, f"取代字串錯誤：參照了不存在的群組 \\{ref} (目前僅有 {max_groups} 個群組)", None

        g_refs = re.findall(r'\\g<([^>]+)>', clean_repl)
        for ref in g_refs:
            if ref.isdigit():
                if int(ref) > max_groups:
                    return False, f"取代字串錯誤：參照了不存在的群組 \\g<{ref}>", None
            elif ref not in named_groups:
                return False, f"取代字串錯誤：參照了不存在的命名群組 \\g<{ref}>", None

        return True, "", compiled

    def _on_btn_clicked(self):
        # 實作取消按鈕行為
        if self._is_working:
            if self._worker:
                self._worker.cancel()
                self.btn_start.setEnabled(False) # 防止連點
            return

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
            self.api.update_status("❌ 參數錯誤：欄位索引越界")
            return

        is_valid, err_msg, compiled_pattern = self._validate_regex(find_text, replace_text, mode == 1)
        if not is_valid:
            self.api.update_status(f"❌ 錯誤：{err_msg}")
            self.api.write_log("ERROR", err_msg)
            return

        visible_indices = self.context.csv_data.get_visible_indices()
        if not visible_indices:
            self.api.update_status("ℹ️ 無需處理")
            return

        self._worker = _RegexReplaceWorker(
            self.context.csv_data, visible_indices, dst_col, compiled_pattern, replace_text
        )
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.log_emitted.connect(self.api.write_log)

        # 標記自己為活動任務的擁有者，並變更按鈕外觀
        self._is_working = True
        self.btn_start.setText("取消取代")
        theme.applyPrimaryButtonStyle(self.btn_start, is_running=True)

        self.api.run_worker(
            self._worker,
            task_name="正規表達式取代",
            total=len(visible_indices),
            initial_log=f"開始取代：尋找 '{find_text}'",
            prevent_sleep=True
        )

    def _on_worker_finished(self, status: TaskStatus):
        self._is_working = False
        self.btn_start.setText("開始取代")
        theme.applyPrimaryButtonStyle(self.btn_start, is_running=False)

        if status == TaskStatus.FINISHED:
            self.context.csv_data.set_modified(True)
            self.context.csv_data.data_changed.emit()
            self.api.request_silent_save()
            self.api.write_log("SUCCESS", "批次取代任務已完成")
            self.api.update_status("✅ 取代完成")
        elif status == TaskStatus.CANCELLED:
            self.api.write_log("WARNING", "取代任務已取消")
            self.api.update_status("⚠️ 任務已取消")
            self.set_panel_enabled(True) # 確保取消後按鈕恢復可用狀態

    # --- 狀態機鎖定邏輯 ---
    def set_panel_enabled(self, global_enabled: bool) -> None:
        self.combo_dst_col.setEnabled(global_enabled)
        self.combo_mode.setEnabled(global_enabled)
        self.edit_find.setEnabled(global_enabled)
        self.edit_replace.setEnabled(global_enabled)
        
        # 核心防呆：如果全域解鎖，或是自己正在執行，按鈕就可以按！
        self.btn_start.setEnabled(global_enabled or self._is_working)
