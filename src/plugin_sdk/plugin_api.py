# src/plugin_sdk/plugin_api.py
from __future__ import annotations

import weakref
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from plugin_sdk.panel_base import BasePluginPanel


class PluginAPI:
    """
    外掛對講機 ── 外掛子類別與主程式溝通的唯一合法途徑。

    [服務對象] 外掛子類別（Plugin Developers）。
               在 BasePluginPanel.__init__ 中自動建立，透過 self.api 存取。

    [職責範圍] 代理外掛向主程式發送各類通知與請求，包含：
               - 任務生命週期通知（start_task / finish_task）
               - 進度、狀態、日誌的即時更新
               - UI 鎖定請求
               - 靜默存檔請求
               所有方法內部均透過觸發 BasePluginPanel 的私有信號來實現跨層通訊，
               外掛完全不需要知道主程式的存在。

    [存取禁令] 嚴禁主程式端（LeftPanel, MainWindow, UiStateMixin 等任何 Host 模組）
               持有或直接呼叫此物件的任何方法。
               主程式應透過 PluginHostAdapter 進行所有控制操作。
    """

    def __init__(self, panel: "BasePluginPanel") -> None:
        # 使用 weakref.proxy 持有實體面板，避免 Python 與 PyQt C++ 底層生命週期
        # 衝突引發的循環引用（Circular Reference）與記憶體洩漏（Memory Leak）。
        self._panel = weakref.proxy(panel)

    def start_task(
        self,
        task_name: str,
        total: int = 0,
        initial_log: str = "",
        prevent_sleep: bool = False,
    ) -> None:
        """
        通知主程式背景任務已啟動。
        主程式收到後將鎖定 UI、啟動計時器、設定防休眠。

        【架構限制】：呼叫 start_task 後，嚴禁再呼叫 lock_ui(True)，
        因為 start_task 內部已隱含全域 UI 鎖定語意。

        Args:
            task_name: 任務顯示名稱，用於狀態列。
            total: 初始總進度量（0 代表不定量）。
            initial_log: 任務開始時在日誌顯示的初始訊息。
            prevent_sleep: 是否在任務期間阻止系統休眠。
        """
        self._panel._task_started.emit(task_name, total, initial_log, prevent_sleep)

    def finish_task(self, status: str) -> None:
        """
        通知主程式背景任務已結束。
        主程式收到後將解鎖 UI、停止計時器、恢復休眠。

        Args:
            status: 結束狀態，合法值為 "finished" | "error" | "cancelled"。
        """
        self._panel._task_finished.emit(status)

    def update_progress(self, current: int, total: int) -> None:
        """更新進度條顯示。"""
        self._panel._progress_updated.emit(current, total)

    def update_status(self, status: str) -> None:
        """更新主視窗狀態列文字。"""
        self._panel._status_updated.emit(status)

    def write_log(self, level: str, message: str) -> None:
        """
        寫入一筆日誌到主視窗日誌面板。

        Args:
            level: 日誌層級，例如 "INFO" | "WARNING" | "ERROR" | "SUCCESS"。
            message: 日誌內容。
        """
        self._panel._log_emitted.emit(level, message)

    def lock_ui(self, lock: bool) -> None:
        """
        請求主程式鎖定或解鎖 UI。

        【重要限制】：此方法僅限於「無背景 Worker，但需要在主線程進行
        短暫阻塞操作」的輕量任務使用。若已呼叫 start_task()，
        嚴禁重複呼叫 lock_ui(True)。
        """
        self._panel._request_lock_ui.emit(lock)

    def request_silent_save(self) -> None:
        """向主程式發起靜默存檔請求（不彈出對話框的後台存檔）。"""
        self._panel._request_silent_save.emit()
