from PyQt6.QtWidgets import QLabel, QComboBox, QLineEdit, QPushButton, QCheckBox, QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal
from common_data.task_status import TaskStatus
from plugin_sdk import theme
from edit.base_sub_panel import BaseSubPanel

class _BatchPasteWorker(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(TaskStatus)
    log_emitted = pyqtSignal(str, str)

    def __init__(self, csv_data, visible_indices, is_manual, src_col, manual_text, dst_col, skip_not_empty):
        super().__init__()
        self.csv_data = csv_data
        self.visible_indices = visible_indices
        self.is_manual = is_manual
        self.src_col = src_col
        self.manual_text = manual_text
        self.dst_col = dst_col
        self.skip_not_empty = skip_not_empty
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
                
                # 確保目標列長度足夠
                while len(row) <= self.dst_col:
                    row.append("")
                
                # 若勾選只覆蓋空欄位，且目標欄位已有值，則跳過
                if self.skip_not_empty and str(row[self.dst_col]).strip() != "":
                    self.progress.emit(idx + 1, total)
                    continue

                if self.is_manual:
                    new_val = self.manual_text
                else:
                    # 確保來源列長度足夠
                    while len(row) <= self.src_col:
                        row.append("")
                    new_val = row[self.src_col]

                row[self.dst_col] = new_val

            except Exception as e:
                self.log_emitted.emit("ERROR", f"列 {row_idx + 1} 處理失敗: {str(e)}")
            
            self.progress.emit(idx + 1, total)
            
        self.finished.emit(TaskStatus.FINISHED)

class PasteSubPanel(BaseSubPanel):
    def __init__(self, api, context, parent=None):
        super().__init__("批次貼上", api, context, parent)
        self._worker = None
        
        # Config 變數
        self._config_src = -1          # -1 代表「手動輸入」，>= 0 代表實際欄位索引
        self._config_manual_text = ""
        self._config_dst = 0           # >= 0 代表實際欄位索引
        self._config_skip_not_empty = True

        self._setup_ui()

    def _setup_ui(self):
        # 1. 資料來源
        lbl_src = QLabel("資料來源")
        theme.applyStandardLabelStyle(lbl_src)
        self.content_layout.addWidget(lbl_src)

        self.combo_src = QComboBox()
        theme.applyStandardComboBoxStyle(self.combo_src)
        self.combo_src.currentIndexChanged.connect(self._on_src_changed)
        self.content_layout.addWidget(self.combo_src)

        # 1.5 手動輸入框 (動態顯示/隱藏)
        self.edit_manual = QLineEdit()
        theme.applyStandardLineEditStyle(self.edit_manual)
        self.edit_manual.setPlaceholderText("請輸入要貼上的文字...")
        self.edit_manual.setVisible(False)
        self.edit_manual.textChanged.connect(self._on_manual_changed)
        self.content_layout.addWidget(self.edit_manual)

        # 2. 目標欄位
        lbl_dst = QLabel("目標欄位")
        theme.applyStandardLabelStyle(lbl_dst)
        self.content_layout.addWidget(lbl_dst)

        self.combo_dst = QComboBox()
        theme.applyStandardComboBoxStyle(self.combo_dst)
        self.combo_dst.currentIndexChanged.connect(self._on_dst_changed)
        self.content_layout.addWidget(self.combo_dst)

        # 3. Checkbox
        self.chk_skip_not_empty = QCheckBox("只覆蓋空欄位")
        theme.applyStandardCheckBoxStyle(self.chk_skip_not_empty)
        self.chk_skip_not_empty.setChecked(True)
        self.chk_skip_not_empty.stateChanged.connect(self._on_chk_changed)
        self.content_layout.addWidget(self.chk_skip_not_empty)

        # 4. 主要按鈕
        self.btn_start = QPushButton("開始處理")
        theme.applyPrimaryButtonStyle(self.btn_start, is_running=False)
        self.btn_start.clicked.connect(self._on_btn_clicked)
        self.content_layout.addWidget(self.btn_start)

    # --- 映射邏輯 ---
    def _src_ui_to_stored(self, ui_index: int) -> int:
        return ui_index - 1  # ui=0 -> stored=-1

    def _src_stored_to_ui(self, stored: int) -> int:
        return stored + 1

    # --- 事件處理 ---
    def _on_src_changed(self, ui_index: int) -> None:
        self._config_src = self._src_ui_to_stored(ui_index)
        self.edit_manual.setVisible(self._config_src == -1)

    def _on_manual_changed(self, text: str) -> None:
        self._config_manual_text = text

    def _on_dst_changed(self, index: int) -> None:
        self._config_dst = index

    def _on_chk_changed(self, state: int) -> None:
        self._config_skip_not_empty = bool(state)

    # --- 生命週期 ---
    def get_config(self) -> dict:
        return {
            "src": self._config_src,
            "manual_text": self._config_manual_text,
            "dst": self._config_dst,
            "skip_not_empty": self._config_skip_not_empty,
        }

    def restore_config(self, data: dict) -> None:
        self._config_src = data.get("src", -1)
        self._config_manual_text = data.get("manual_text", "")
        self._config_dst = data.get("dst", 0)
        self._config_skip_not_empty = data.get("skip_not_empty", True)

        self.combo_src.blockSignals(True)
        self.combo_dst.blockSignals(True)
        self.edit_manual.blockSignals(True)
        self.chk_skip_not_empty.blockSignals(True)
        try:
            self.edit_manual.setText(self._config_manual_text)
            self.chk_skip_not_empty.setChecked(self._config_skip_not_empty)
            self.edit_manual.setVisible(self._config_src == -1)
        finally:
            self.combo_src.blockSignals(False)
            self.combo_dst.blockSignals(False)
            self.edit_manual.blockSignals(False)
            self.chk_skip_not_empty.blockSignals(False)

    def on_data_refreshed(self) -> None:
        if not self.context or not self.context.is_data_loaded:
            return
        
        csv_data = self.context.csv_data
        limit = max(csv_data.num_cols, self._config_dst + 1)
        if self._config_src >= 0:
            limit = max(limit, self._config_src + 1)

        self.combo_src.blockSignals(True)
        self.combo_dst.blockSignals(True)
        try:
            self.combo_src.clear()
            self.combo_dst.clear()
            
            self.combo_src.addItem("手動輸入")
            for col in range(limit):
                header = csv_data.get_column_header(col)
                self.combo_src.addItem(header)
                self.combo_dst.addItem(header)

            ui_src = self._src_stored_to_ui(self._config_src)
            max_src = self.combo_src.count() - 1
            self.combo_src.setCurrentIndex(max(0, min(ui_src, max_src)))

            ui_dst = self._config_dst
            max_dst = self.combo_dst.count() - 1
            self.combo_dst.setCurrentIndex(max(0, min(ui_dst, max_dst)))
        finally:
            self.combo_src.blockSignals(False)
            self.combo_dst.blockSignals(False)

    def set_panel_enabled(self, global_enabled: bool) -> None:
        self.combo_src.setEnabled(global_enabled)
        self.edit_manual.setEnabled(global_enabled)
        self.combo_dst.setEnabled(global_enabled)
        self.chk_skip_not_empty.setEnabled(global_enabled)
        self.btn_start.setEnabled(global_enabled or self._is_working)

    def _on_btn_clicked(self):
        if self._is_working:
            if self._worker:
                self._worker.cancel()
                self.btn_start.setEnabled(False)
            return

        if not self.context or not self.context.is_data_loaded:
            self.api.write_log("WARNING", "請先載入 CSV 資料")
            self.api.update_status("❌ 參數錯誤")
            return

        is_manual = (self._config_src == -1)
        
        if not is_manual and self._config_src == self._config_dst:
            self.api.write_log("WARNING", "來源欄位與目標欄位不可相同")
            self.api.update_status("❌ 參數錯誤：欄位重複")
            return

        if not self._config_skip_not_empty:
            reply = QMessageBox.warning(
                self, 
                "警告", 
                "注意：此操作會覆蓋現有資料。\n確定要繼續嗎？", 
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        visible_indices = self.context.csv_data.get_visible_indices()
        if not visible_indices:
            self.api.update_status("ℹ️ 無需處理")
            return

        self._worker = _BatchPasteWorker(
            csv_data=self.context.csv_data,
            visible_indices=visible_indices,
            is_manual=is_manual,
            src_col=self._config_src,
            manual_text=self._config_manual_text,
            dst_col=self._config_dst,
            skip_not_empty=self._config_skip_not_empty
        )
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.log_emitted.connect(self.api.write_log)

        self._is_working = True
        self.btn_start.setText("取消處理")
        theme.applyPrimaryButtonStyle(self.btn_start, is_running=True)

        self.api.run_worker(
            self._worker,
            task_name="批次貼上",
            total=len(visible_indices),
            initial_log="開始批次貼上任務...",
            prevent_sleep=True
        )

    def _on_worker_finished(self, status: TaskStatus):
        self._is_working = False
        self.btn_start.setText("開始處理")
        theme.applyPrimaryButtonStyle(self.btn_start, is_running=False)

        if status == TaskStatus.FINISHED:
            self.context.csv_data.set_modified(True)
            self.context.csv_data.data_changed.emit()
            self.api.request_silent_save()
            self.api.write_log("SUCCESS", "批次貼上任務已完成")
            self.api.update_status("✅ 貼上完成")
        elif status == TaskStatus.CANCELLED:
            self.api.write_log("WARNING", "貼上任務已取消")
            self.api.update_status("⚠️ 任務已取消")
            self.set_panel_enabled(True)
