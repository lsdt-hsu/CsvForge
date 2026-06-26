# CsvTranslator 外掛開發規範與注意事項

### A. 外掛基本目錄結構
每個外掛面板必須是一個獨立的資料夾，且必須包含標準入口檔 `plugin.py`。
* **標準入口檔**：`plugin.py`
* **入口類別**：必須在 `plugin.py` 中定義繼承自 `BasePanel` 的類別，且類別名稱必須固定命名為 `PanelClass`：
  ```python
  from PyQt6.QtWidgets import QLabel
  from base.base_panel import BasePanel

  class PanelClass(BasePanel):
      def __init__(self, parent=None, context=None):
          super().__init__(parent, title_text="我的外掛", require_data_loading=True, context=context)
          self.controls_layout.addWidget(QLabel("我的外掛介面"))

      def get_uuid(self) -> str:
          return "你的唯一UUID-v4"

      def get_package_name(self) -> str:
          return "my_plugin_name"

      def serialize_config(self) -> dict:
          return {}

      def deserialize_config(self, data: dict) -> None:
          pass
  ```

### B. 重要防錯與注意事項

#### ① 模組導入：禁止相對導入，使用同目錄直連導入
* **問題**：若在外掛內部使用 `from .helper import ...` 等相對導入語法，使用 `importlib` 動態加載單一 `.py` 檔案時，會因缺乏 parent package 資訊而引發 `attempted relative import with no known parent package` 錯誤。
* **修正做法**：主程式載入外掛時已將外掛目錄加入 `sys.path`。外掛內部的檔案導入請一律使用**同目錄直連導入**（不帶點號，例如 `from helper import ...`）。

#### ② 存取主視窗（MainWindow）：禁止使用 `self.parent()`
* **問題**：在 PyQt 中，外掛 widget 被加入活動列 layout 後，呼叫 `self.parent()` 常會回傳通用的 `QWidget` 基底物件，導致無法調用主視窗專屬的方法或屬性（例如 `lock_ui_from_panel` 等），進而拋出 `AttributeError` 造成閃退。
* **修正做法**：應在 `PanelClass` 建構子中，直接將傳入的 `parent`（即 `MainWindow` 實例）保存為成員變數 `self.main_window = parent`。後續凡需使用主視窗的功能，請一律使用 `self.main_window`。

#### ③ 訊號連接與主視窗通訊
外掛面板可直接使用繼承自 `BasePanel` 的標準 Qt 訊號，以觸發主視窗解鎖、進度條更新或寫入日誌：
* `self.request_lock_ui.emit(bool)`：請求鎖定/解鎖 UI。
* `self.progress_updated.emit(current, total)`：更新進度條。
* `self.status_updated.emit(status_str)`：更新就緒/執行狀態。
* `self.log_emitted.emit(level, message)`：輸出 INFO/SUCCESS/WARNING/ERROR 等級日誌。
* `self.request_start_worker.emit(worker_instance)`：請求啟動背景執行緒。

#### ④ 設定檔讀寫與 UUID 規格
* 每個外掛必須實作 `get_uuid(self) -> str` 並回傳唯一的 UUIDv4。
* 主程式在讀寫 `settings.json` 時，外掛面板的專屬設定將以 `PLUGIN-{UUID}` 作為最外層區段的 Key 進行存取（而內建面板則是使用面板識別名稱）。
* 當外掛被移除時，該 `PLUGIN-{UUID}` 區段會從設定檔中乾淨抹除。
* 內建的四大面板 UUID 已於 `left_panel.py` 中被 `BUILTIN_UUIDS` 集合宣告保護，外掛 UUID 若與當前面板重複將拒絕載入。
