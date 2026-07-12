# src/plugin_sdk/host_adapter.py
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QIcon

if TYPE_CHECKING:
    from plugin_sdk.panel_base import BasePluginPanel


class PluginHostAdapter:
    """
    主程式方向盤 ── 主程式控制外掛生命週期的唯一合法代理。

    [服務對象] 主程式端模組（LeftPanel, MainWindow, UiStateMixin,
               SettingsMixin 等一切 Host 身份的模組）。

    [職責範圍] 作為主程式存取外掛的單一入口，代理所有生命週期控制操作，
               包含：初始化、啟用/停用、取消任務、查詢狀態、
               序列化/反序列化設定、以及取得 UI Widget。
               內部持有實體面板 _panel 的強引用，並轉呼叫其 _internal_xxx() 方法。

    [Thread 管理] PluginHostAdapter 是系統中唯一負責建立 QThread、
               管理 Worker GC 保活的類別。外掛透過 api.run_worker() 委託，
               由此類別統一接收並執行全套 Thread 生命週期管理。

    [存取禁令] 嚴禁外掛子類別（Plugin Developers 所編寫的 PanelClass 及其
               任何內部邏輯）持有或呼叫此物件。
               外掛應透過 self.api（PluginAPI 實例）進行所有對外通訊。
    """

    def __init__(self, panel: "BasePluginPanel") -> None:
        self._panel = panel
        # GC 保活清單：每個元素為 (worker, thread, throttled_forwarder) tuple
        self._active_workers: list[tuple] = []
        # 當前活躍的 Worker 引用，用於 cancel_task 與 is_task_running 查詢
        self._current_worker = None

    # ── UI 整合 ──────────────────────────────────────────────────────────────

    def get_widget(self) -> QWidget:
        """
        取得可加入 QStackedWidget 的實體 UI Widget。
        供 LeftPanel 在建立面板時呼叫。
        """
        return self._panel

    def get_panel(self) -> "BasePluginPanel":
        """
        取得內部實體面板，僅供 LeftPanel 進行信號連接（_connect_panel_signals）使用。

        【注意】：此方法不應在 LeftPanel 以外的場合呼叫。
                  主程式其他模組（MainWindow, UiStateMixin 等）嚴禁呼叫此方法。
        """
        return self._panel

    # ── Thread 生命週期管理（新架構核心）────────────────────────────────────

    def _on_run_worker_requested(
        self,
        worker,
        task_name: str,
        total: int,
        initial_log: str,
        prevent_sleep: bool,
    ) -> None:
        """
        攔截外掛的 api.run_worker() 請求，統一管理 QThread 生命週期。

        由 LeftPanel._connect_panel_signals() 連接至 panel._request_run_worker 信號，
        是整個架構中唯一合法建立 QThread 的位置。

        執行流程：
          a) 建立 QThread 並 worker.moveToThread()
          b) 對 worker.progress 套用 ThrottledProgress(min_interval=0.2)，
             節流後轉發至 panel._progress_updated
          c) 將 (worker, thread, throttler) 加入 _active_workers GC 保活清單
          d) 啟動 Thread
          e) 攔截 worker.finished 信號，自動執行清理與 finish_task
        """
        from PyQt6.QtCore import QThread
        from utils.throttler import ThrottledProgress
        import weakref

        thread = QThread()
        worker.moveToThread(thread)

        # 建立弱引用以打破閉包循環引用
        weak_self = weakref.ref(self)
        weak_worker = weakref.ref(worker)
        weak_thread = weakref.ref(thread)

        # 節流轉發：worker.progress → ThrottledProgress → panel._progress_updated
        # ThrottledProgress 包裝的是 target signal，限制轉發頻率
        _throttled = ThrottledProgress(self._panel._progress_updated, parent=self._panel, min_interval=0.2)

        def _on_worker_progress(current: int, total_count: int):
            _throttled.emit(current, total_count)

        worker.progress.connect(_on_worker_progress)

        # GC 保活：將 worker、thread、throttler 與轉發 slot 全部加入清單防止被回收
        entry = (worker, thread, _throttled, _on_worker_progress)
        self._active_workers.append(entry)
        self._current_worker = worker

        # 完成回調：自動清理 + 通知主程式 finish_task
        def _on_finished(status: str):
            _throttled.cancel()  # 主動取消任何懸掛的補發定時器
            host = weak_self()
            w = weak_worker()
            t = weak_thread()
            if not host or not w or not t:
                return

            # 從 GC 清單移除：使用弱引用 w 遍歷尋找 matching entry，避免閉包強引用 entry
            for e in list(host._active_workers):
                if e[0] is w:
                    host._active_workers.remove(e)
                    break

            # 清除當前 Worker 引用
            if host._current_worker is w:
                host._current_worker = None

            # 斷開信號連接以解除 PyQt 信號對閉包的強引用
            try:
                w.finished.disconnect(_on_finished)
            except (TypeError, AttributeError):
                pass
            try:
                w.progress.disconnect(_on_worker_progress)
            except (TypeError, AttributeError):
                pass

            # 通知主程式任務結束（解鎖 UI、停止計時器）
            host._panel._task_finished.emit(status)
            
            # 安全清理 Thread
            t.quit()
            t.wait()
            t.deleteLater()
            w.deleteLater()

        worker.finished.connect(_on_finished)
        thread.started.connect(worker.run)
        thread.start()

    # ── 生命週期控制 ─────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """
        觸發外掛面板的初始狀態同步（資料載入狀態 / CSV 欄位更新）。
        由 LeftPanel 在面板加入 StackedWidget 後呼叫一次。
        """
        self._panel._internal_initialize()

    def cancel_task(self) -> None:
        """
        命令當前 Worker 取消任務。
        主程式「取消」按鈕的信號槽應呼叫此方法。

        新架構（run_worker）：直接對 _current_worker 呼叫 cancel()。
        """
        if self._current_worker is not None:
            self._current_worker.cancel()

    def set_enabled(self, enabled: bool) -> None:
        """
        啟用或停用外掛面板的 UI 控制元件。
        由 LeftPanel.set_enabled() 統一呼叫，配合全域 UI 鎖定狀態。
        """
        self._panel._internal_set_enabled(enabled)

    def cleanup(self) -> None:
        """
        清理外掛面板與主程式或全域信號的連接，防範記憶體洩漏與懸空信號。
        """
        # 1. 斷開與全域 CsvData 的連接
        if (
            hasattr(self._panel, "context")
            and self._panel.context
            and hasattr(self._panel.context, "csv_data")
            and self._panel.context.csv_data
        ):
            csv_data = self._panel.context.csv_data
            
            # 斷開 data_loaded 信號的 _on_global_data_loaded 與 on_csv_data_refreshed
            if hasattr(csv_data, "data_loaded"):
                if hasattr(self._panel, "_on_global_data_loaded"):
                    try:
                        csv_data.data_loaded.disconnect(self._panel._on_global_data_loaded)
                    except (TypeError, AttributeError):
                        pass
                if hasattr(self._panel, "on_csv_data_refreshed"):
                    try:
                        csv_data.data_loaded.disconnect(self._panel.on_csv_data_refreshed)
                    except (TypeError, AttributeError):
                        pass
            
            # 斷開 header_state_changed 信號的 on_csv_data_refreshed
            if hasattr(csv_data, "header_state_changed") and hasattr(self._panel, "on_csv_data_refreshed"):
                try:
                    csv_data.header_state_changed.disconnect(self._panel.on_csv_data_refreshed)
                except (TypeError, AttributeError):
                    pass

        # 2. 斷開面板本身的私有信號（防範與主程式 Host 之間的信號懸空）
        for signal_name in [
            "_request_lock_ui", "_progress_updated", "_status_updated",
            "_log_emitted", "_task_started", "_task_finished",
            "_request_silent_save", "_request_run_worker"
        ]:
            if hasattr(self._panel, signal_name):
                try:
                    getattr(self._panel, signal_name).disconnect()
                except (TypeError, AttributeError):
                    pass

        # 3. 若有活躍的 worker 任務，強制取消以防止 Thread 洩漏
        self.cancel_task()

    # ── 狀態查詢 ─────────────────────────────────────────────────────────────

    def is_task_running(self) -> bool:
        """
        查詢該外掛是否仍有背景任務在執行。
        新架構：直接查詢 _current_worker 是否存在，不依賴外掛覆寫方法。
        """
        return self._current_worker is not None

    # ── 識別資訊 ─────────────────────────────────────────────────────────────

    def get_uuid(self) -> str:
        """取得此外掛的唯一識別 UUID 字串。"""
        return self._panel._internal_get_uuid()

    def get_package_name(self) -> str:
        """取得此外掛在設定檔中對應的識別名稱（例如 'translate'）。"""
        return self._panel._internal_get_package_name()

    def get_icon(self) -> QIcon:
        """取得此外掛顯示於活動列的圖示。"""
        return self._panel._internal_get_icon()

    # ── 設定序列化 ───────────────────────────────────────────────────────────

    def serialize_config(self) -> dict:
        """將外掛當前 UI 設定序列化為 dict，用於存檔。"""
        return self._panel._internal_serialize_config()

    def deserialize_config(self, data: dict) -> None:
        """從 dict 還原外掛 UI 設定，用於讀取存檔。"""
        self._panel._internal_deserialize_config(data)
