import os
from common_data.csv_data import CsvData
from settings_manager import (
    WindowConfig, MainConfig, IoPanelConfig, DataEditorConfig,
    StatusPanelConfig, SidePanelConfig
)

class AppContext:
    """
    AppContext — 封裝主畫面的動態設定與狀態，提供子面板存取。

    Config 物件存取：
      各面板可透過 xxx_config property 讀取任何一個組態，但每個組態只應被
      一個特定模組寫入（見各 Config dataclass 的 docstring）。

    動態狀態存取：
      source_path、output_path 等執行時動態值仍透過存取器半直接取得
      各編輯框的最新值，而非從 io_panel_config 讀取。
      IoPanelConfig 僅作為 IO Panel 控件的初始預設值來源。
    """

    def __init__(self, main_window):
        self._win = main_window

    # ── Config 物件存取 ───────────────────────────────────────────────────────

    @property
    def window_config(self) -> WindowConfig:
        return self._win._configs["window"]

    @property
    def main_config(self) -> MainConfig:
        return self._win._configs["main"]

    @property
    def io_panel_config(self) -> IoPanelConfig:
        return self._win._configs["io_panel"]

    @property
    def side_panel_config(self) -> SidePanelConfig:
        return self._win._configs["side_panel"]

    @property
    def data_editor_config(self) -> DataEditorConfig:
        return self._win._configs["data_editor_panel"]

    @property
    def status_panel_config(self) -> StatusPanelConfig:
        return self._win._configs["status_panel"]

    # ── 執行時動態狀態存取（解耦資料編輯面板，統一由 LoadedCSVData Model 提供）──

    @property
    def csv_data(self) -> "CsvData":
        return self._win.csv_data

    def set_modified(self, modified: bool) -> None:
        self.csv_data.set_modified(modified)

    @property
    def is_first_row_header(self) -> bool:
        return self.csv_data.is_header

    @property
    def is_modified(self) -> bool:
        return self.csv_data.is_modified

    @property
    def is_ui_locked(self) -> bool:
        return getattr(self._win, "_ui_locked", False)

    @property
    def is_data_loaded(self) -> bool:
        return bool(self.csv_data.all_rows)

    @property
    def all_rows(self) -> list:
        return self.csv_data.all_rows
