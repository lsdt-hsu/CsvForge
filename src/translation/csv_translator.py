# src/translation/csv_translator.py
from PyQt6.QtCore import QObject, pyqtSignal
from translation.translation_validator import validate_translation_inputs
from translation.csv_translator_worker import CSVTranslatorWorker

class CSVTranslator(QObject):
    started = pyqtSignal()
    finished = pyqtSignal()
    cancelled = pyqtSignal()
    translation_done = pyqtSignal()
    data_changed = pyqtSignal()

    def __init__(self, parent=None, context=None):
        super().__init__(parent)
        self.parent_win = parent  # TranslationPanel
        self.context = context
        self._current_worker = None
        self._has_error = False

    def is_running(self) -> bool:
        return self._current_worker is not None and self._current_worker.isRunning()

    def start_translation_task(self, src_lang, tgt_lang, batch_interval, single_interval, batch_size, src_col, tgt_col):
        if self.is_running():
            return

        is_valid, parsed = validate_translation_inputs(
            self.parent_win,
            src_col,
            tgt_col
        )
        if not is_valid:
            return

        visible_row_indices = self.context.csv_data.get_visible_indices()
        all_rows = self.context.csv_data.all_rows

        worker_instance = CSVTranslatorWorker(
            all_rows=all_rows,
            visible_row_indices=visible_row_indices,
            source_col_idx=parsed["source_col"],
            target_col_idx=parsed["target_col"],
            source_lang=src_lang,
            target_lang=tgt_lang,
            batch_interval=batch_interval,
            single_interval=single_interval,
            batch_size=batch_size,
        )
        self._current_worker = worker_instance
        self._has_error = False

        # 連接 Worker 完成與錯誤 Signal
        worker_instance.finished_successfully.connect(self._on_worker_success)
        worker_instance.finished_with_error.connect(self._on_worker_error)
        worker_instance.data_changed.connect(self.data_changed.emit)

        # 串接 Worker 進度、日誌、狀態至 TranslationPanel 基底類別方法
        worker_instance.progress_updated.connect(self.parent_win.api.update_progress)
        worker_instance.log_emitted.connect(self.parent_win.api.write_log)
        worker_instance.status_updated.connect(self.parent_win.api.update_status)

        # 啟動 Worker Thread
        worker_instance.start()
        self.started.emit()

    def cancel_task(self):
        if self._current_worker and self._current_worker.isRunning():
            self._current_worker.cancel()
            self.cancelled.emit()

    def _on_worker_success(self):
        if not self._current_worker:
            return
        self.finished.emit()
        self.translation_done.emit()
        self._current_worker = None

    def _on_worker_error(self, err_msg):
        if not self._current_worker:
            return
        self._has_error = True
        self.finished.emit()
        self.translation_done.emit()
        self._current_worker = None
