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

    [存取禁令] 嚴禁外掛子類別（Plugin Developers 所編寫的 PanelClass 及其
               任何內部邏輯）持有或呼叫此物件。
               外掛應透過 self.api（PluginAPI 實例）進行所有對外通訊。
    """

    def __init__(self, panel: "BasePluginPanel") -> None:
        self._panel = panel

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

    # ── 生命週期控制 ─────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """
        觸發外掛面板的初始狀態同步（資料載入狀態 / CSV 欄位更新）。
        由 LeftPanel 在面板加入 StackedWidget 後呼叫一次。
        """
        self._panel._internal_initialize()

    def cancel_task(self) -> None:
        """
        命令外掛取消當前正在執行的背景任務。
        主程式「取消」按鈕的信號槽應呼叫此方法。
        """
        self._panel._internal_cancel_task()

    def set_enabled(self, enabled: bool) -> None:
        """
        啟用或停用外掛面板的 UI 控制元件。
        由 LeftPanel.set_enabled() 統一呼叫，配合全域 UI 鎖定狀態。
        """
        self._panel._internal_set_enabled(enabled)

    # ── 狀態查詢 ─────────────────────────────────────────────────────────────

    def is_task_running(self) -> bool:
        """
        查詢該外掛是否仍有背景任務在執行。
        用於 LeftPanel 在切換分頁前的安全性檢查。
        """
        return self._panel._internal_is_task_running()

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
