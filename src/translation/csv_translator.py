from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
from io_panel.io_panel_validator import validate_io_panel_inputs
from translation.csv_translator_worker import CSVTranslatorWorker

class CSVTranslator(QObject):
    request_start_worker = pyqtSignal(object)
    started = pyqtSignal()
    finished = pyqtSignal()
    cancelled = pyqtSignal()

    def __init__(self, parent=None, context=None):
        super().__init__(parent)
        self.parent_win = parent  # TranslationPanel
        self.context = context
        self._current_worker = None

    def is_running(self) -> bool:
        return self._current_worker is not None and self._current_worker.isRunning()

    def start_translation_task(self, src_lang, tgt_lang, batch_interval, single_interval, batch_size):
        if self.is_running():
            return

        is_valid, parsed = validate_io_panel_inputs(
            self.parent_win,
            self.context,
            require_source_path=True,
            require_output_path=True,
            require_source_col=True,
            require_target_col=True,
        )
        if not is_valid:
            return

        worker_instance = CSVTranslatorWorker(
            source_path=self.context.source_path,
            output_path=self.context.output_path,
            start_row=parsed["start_row"],
            end_row=parsed["end_row"],
            source_col=parsed["source_col"],
            target_col=parsed["target_col"],
            source_lang=src_lang,
            target_lang=tgt_lang,
            batch_interval=batch_interval,
            single_interval=single_interval,
            batch_size=batch_size,
        )
        self._current_worker = worker_instance

        # 連接 Worker 完成與錯誤 Signal
        worker_instance.finished_successfully.connect(self._on_worker_success)
        worker_instance.finished_with_error.connect(self._on_worker_error)

        # 請求主視窗啟動 Worker Thread
        self.request_start_worker.emit(worker_instance)
        self.started.emit()

    def cancel_task(self):
        if self._current_worker and self._current_worker.isRunning():
            self._current_worker.cancel()
            self.cancelled.emit()

    def _on_worker_success(self, out_path):
        if not self._current_worker:
            return
        worker = self._current_worker

        # 彈出成功或中斷 QMessageBox
        if worker._is_cancelled:
            title, msg = worker.get_cancel_message(out_path)
            QMessageBox.information(self.parent_win.window(), title, msg)
        else:
            title, msg = worker.get_success_message(out_path)
            QMessageBox.information(self.parent_win.window(), title, msg)

        self.finished.emit()
        self._current_worker = None

    def _on_worker_error(self, err_msg):
        if not self._current_worker:
            return
        worker = self._current_worker

        title, msg = worker.get_error_message(err_msg)
        QMessageBox.critical(self.parent_win.window(), title, msg)

        self.finished.emit()
        self._current_worker = None
