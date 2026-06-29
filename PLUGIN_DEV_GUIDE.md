# 外掛實作指南 (PLUGIN_DEV_GUIDE.md)

> **適用對象**：任何開發者（含 AI Agent）在建立新的 CsvTranslator 外掛面板時，**以本文件為唯一參考**。  
> **核心承諾**：嚴格遵照本文件，即可在不需要人類介入除錯的情況下，產出 100% 符合規範的外掛面板。

---

## 目錄

1. [第一部分：快速起步](#第一部分快速起步-quick-start--boilerplate)
   - 1.1 [檔案結構規範](#11-檔案結構規範)
   - 1.2 [基礎類別繼承](#12-基礎類別繼承)
   - 1.3 [Hello World 樣板](#13-hello-world-樣板)
2. [第二部分：一致性策略](#第二部分一致性策略)
   - 2.1 [資料編輯](#21-資料編輯)
   - 2.2 [UI 設計規範](#22-ui-設計規範)
   - 2.3 [流程與資料管理規範](#23-流程與資料管理規範)
3. [第三部分：API 參考與嚴格規範](#第三部分api-參考與嚴格規範)
   - 3.1 [事件通訊機制（Signal）](#31-事件通訊機制signal)
   - 3.2 [樣式套用函式（theme）](#32-樣式套用函式theme)
   - 3.3 [共用資料（common_data）](#33-共用資料common_data)
   - 3.4 [工具函式（utils）](#34-工具函式utils)
   - 3.5 [隔離限制與開發建議（Anti-patterns & Best Practices）](#35-隔離限制與開發建議anti-patterns--best-practices)

---

## 第一部分：快速起步 (Quick Start & Boilerplate)

### 1.1 檔案結構規範

每個外掛必須是一個**獨立資料夾**，放置於專案根目錄下。  
資料夾內**必須**包含 `plugin.py` 作為唯一入口點，主程式會動態載入此檔案。

```
my_plugin/               <- 外掛資料夾（名稱自訂）
└── plugin.py            <- 必要入口，外掛類別名稱必須為 PanelClass
```

> **規定**：外掛類別名稱**必須**為 `PanelClass`，主程式以此名稱進行動態載入。

---

### 1.2 基礎類別繼承

外掛面板**必須**繼承 `plugin_sdk.panel_base.BasePluginPanel`。

```python
from plugin_sdk.panel_base import BasePluginPanel

class PanelClass(BasePluginPanel):
    ...
```

`BasePluginPanel` 的建構子簽名如下：

```python
def __init__(self, parent=None, title_text="", require_data_loading=True, context: PluginContext = None)
```

| 參數 | 說明 |
|------|------|
| `title_text` | 顯示在面板頂端的標題文字；傳空字串則不顯示標題 |
| `require_data_loading` | `True`（預設）代表需要 CSV 資料才能操作，基底類別會自動顯示「尚未載入資料」並管理 `controls_container` 的可見性；`False` 代表面板不依賴資料，所有 widget 直接加入 `controls_layout` |
| `context` | 由主程式注入的 `PluginContext`，必須透過此物件存取 CSV 資料與狀態 |

---

### 1.3 Hello World 樣板

以下是可直接複製執行的**最極簡**完整 `plugin.py`。  
它實作了所有 `NotImplementedError` 介面，並示範正確的 `__init__` 呼叫與 Config 架構。

```python
# my_plugin/plugin.py
from dataclasses import dataclass

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt

# pyrefly: ignore [missing-import]
from plugin_sdk.panel_base import BasePluginPanel
# pyrefly: ignore [missing-import]
from plugin_sdk.theme import applyPrimaryButtonStyle


# ── 1. 定義 Config dataclass ──────────────────────────────────────────────────
@dataclass
class MyPluginConfig:
    dirty: bool = False
    # 在此加入面板所需的設定欄位


# ── 2. 定義面板類別（固定名稱 PanelClass）────────────────────────────────────
class PanelClass(BasePluginPanel):

    def __init__(self, parent=None, context=None):
        super().__init__(
            parent,
            title_text="我的外掛",      # 顯示在面板頂端的標題
            require_data_loading=True,  # 設為 False 可讓面板在無資料時也能操作
            context=context,
        )
        self.config = MyPluginConfig()
        self._init_ui()

    # ── 3. 建立 UI（加入 controls_layout）────────────────────────────────────
    def _init_ui(self):
        self.btn_run = QPushButton("執行")
        applyPrimaryButtonStyle(self.btn_run, is_running=False)
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.clicked.connect(self.run_main_action)
        self.controls_layout.addWidget(self.btn_run)

    # ── 4. 必須實作的 Interface 方法 ──────────────────────────────────────────

    def get_uuid(self) -> str:
        """回傳此面板的唯一 UUID（請自行產生，不得與其他外掛重複）"""
        return "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"  # 替換為真實 UUID

    def get_package_name(self) -> str:
        """回傳設定檔中對應的識別名稱（英數字，不得與其他外掛重複）"""
        return "my_plugin"

    def serialize_config(self) -> dict:
        """將 Config 序列化為可供主程式儲存的 dict"""
        cfg = self.config
        return {
            # "key": cfg.field,
        }

    def deserialize_config(self, data: dict) -> None:
        """從主程式 restore 的 dict 還原 Config，並更新 UI"""
        cfg = self.config
        # cfg.field = data.get("key", default_value)
        self._restore_ui_from_config()

    # ── 5. 選擇性複寫的 Interface 方法 ───────────────────────────────────────

    def run_main_action(self) -> None:
        """主要功能按鈕的進入點。執行前先驗證 Config 是否有效。"""
        if not self.context or not self.context.is_data_loaded:
            self.update_status("尚未載入資料")
            return
        # 執行任務...
        self.update_status("執行完畢")

    def on_csv_data_refreshed(self) -> None:
        """
        資料載入或標頭狀態變更時由基底類別自動觸發。
        複寫此方法以更新欄位下拉選單等依賴資料的 UI 元件。
        """
        pass

    # ── 6. 內部輔助方法 ───────────────────────────────────────────────────────

    def _restore_ui_from_config(self) -> None:
        """
        從 Config 還原 UI 元件狀態。
        必須用 blockSignals(True/False) 包圍，避免誤觸 dirty flag。
        """
        # self.some_widget.blockSignals(True)
        # try:
        #     self.some_widget.setValue(self.config.some_field)
        # finally:
        #     self.some_widget.blockSignals(False)
        pass
```

---

## 第二部分：一致性策略

### 2.1 資料編輯

在處理 CSV 資料的編輯或修改時，**強烈建議只編輯可見列（Visible Rows）**，以避免修改到使用者預期之外的資料（即被使用者過濾、隱藏的資料）。

- **取得可見列索引**：使用 `self.context.csv_data.get_visible_indices()` 或 `self.context.csv_data.visible_indices`。
- **取得可見列資料**：使用 `self.context.csv_data.get_visible_rows()`。
- **操作建議**：在走訪資料進行編輯時，僅針對可見的列索引進行操作，避免修改到隱藏的列。

---

### 2.2 UI 設計規範

#### 2.2.1 圖示（Icon）設計

- **外部圖示**（顯示在主程式的頁籤/工具列）：`BasePluginPanel.get_icon()` 已提供**預設實作**，會自動以 `get_package_name()` 的前兩個字母產生**白色文字、透明背景、無邊框**的圖示。想提供獨特的圖示，可以覆寫 **`get_icon()`**。
- **面板內圖示**：推薦使用相同的極簡風格（白色、透明背景、無邊框）。

#### 2.2.2 樣式套用

- 主要任務按鈕（如「開始翻譯」）**強烈建議**使用 `applyPrimaryButtonStyle`，並根據執行狀態傳入 `is_running` 參數：

  ```python
  from plugin_sdk.theme import applyPrimaryButtonStyle

  applyPrimaryButtonStyle(self.btn_run, is_running=False)  # 就緒狀態：藍色
  applyPrimaryButtonStyle(self.btn_run, is_running=True)   # 執行中：紅色（作為「停止」按鈕）
  ```

- 其餘元件優先使用 `plugin_sdk.theme` 中的標準樣式函式（詳見 [3.2 節](#32-樣式套用函式theme)）。

#### 2.2.3 面板寬度與捲動

- 面板最大寬度為 `SIDEBAR_MAX_WIDTH = 341`（px），定義於 `plugin_sdk.theme`。
- **建議做法**：提供垂直捲動（如使用 `QScrollArea`），並**儘量避免**水平捲動。
- 使用 `QGridLayout` 或 `QVBoxLayout` 佈局，避免元件超出面板寬度。

#### 2.2.4 資料載入狀態判斷

- 需要判斷 CSV 是否已載入時，**必須**使用 `self.context.is_data_loaded`：

  ```python
  if self.context and self.context.is_data_loaded:
      # 資料已載入
  ```

- 當 `require_data_loading=True` 時，基底類別已自動訂閱 `data_loaded` 信號，並在資料載入/解除時呼叫 `show_controls()` / `reset_panel()`。**無需在子類別中重複處理此邏輯**，只需複寫 `on_csv_data_refreshed()` 更新 UI 內容即可。

#### 2.2.5 欄位選單的列舉規則

列舉欄位時，**建議**使用以下公式計算要顯示的欄位總數，**無論資料是否已載入**：

```python
csv_data = self.context.csv_data
limit = max(csv_data.num_cols, self.config.col_a + 1, self.config.col_b + 1)
```

- 欄位名稱**建議**使用 `csv_data.get_column_header(i)` 取得，**無論資料是否已載入**。
- **最佳實踐**：建議避免在 `get_column_header` 的回傳值上自行加入前綴或後綴，以維持 UI 顯示的簡潔與一致。

```python
for i in range(limit):
    col_name = csv_data.get_column_header(i)  # 直接使用，不加前後綴
    self.combo_col.addItem(col_name, i)
```

#### 2.2.6 含非欄位選項的選單（例如「所有欄位」）

若欄位選單中需要包含非欄位選項（例如「所有欄位」），**強烈建議**：

- **非欄位選項排在欄位選項之前**（UI index 0 起始）。

**Config 的 index 記錄與序列化映射規則**：

| UI index | 序列化儲存值 | 說明 |
|----------|------------|------|
| 0 | −1 | 第一個非欄位選項（如「所有欄位」） |
| 1 | −2 | 第二個非欄位選項 |
| … | … | 依此類推 |
| N_NON_COL | 0 | 第一個欄位選項（0-based 欄位 index = 0） |
| N_NON_COL + k | k | 第 k+1 個欄位（0-based 欄位 index = k） |

其中 `N_NON_COL` 為非欄位選項的總數。

**範例（N_NON_COL = 1，只有「所有欄位」一項）**：

```python
N_NON_COL = 1  # 非欄位選項數量

# --- 建立選單 ---
self.combo_col.addItem("所有欄位")          # UI index = 0
for i in range(limit):
    col_name = csv_data.get_column_header(i)
    self.combo_col.addItem(col_name)         # UI index = i + N_NON_COL

# --- Config 記錄 UI index ---
# _on_combo_changed 中：
def _on_col_changed(self, ui_index: int) -> None:
    if self.config.col != ui_index:
        self.config.col = ui_index
        self.config.dirty = True

# --- 序列化：UI index → 儲存值 ---
def _ui_to_stored(self, ui_index: int) -> int:
    if ui_index < N_NON_COL:
        return -(ui_index + 1)       # 0 -> -1, 1 -> -2, ...
    return ui_index - N_NON_COL     # N_NON_COL -> 0, N_NON_COL+1 -> 1, ...

# --- 反序列化：儲存值 → UI index ---
def _stored_to_ui(self, stored: int) -> int:
    if stored < 0:
        ui_index = -(stored + 1)     # -1 -> 0, -2 -> 1, ...
        if ui_index >= N_NON_COL:
            ui_index = 0             # 超出當前映射範圍，退回第一個非欄位選項
        return ui_index
    return stored + N_NON_COL       # 0 -> N_NON_COL, 1 -> N_NON_COL+1, ...
```

---

### 2.3 流程與資料管理規範

#### 2.3.1 資料來源與儲存

- **主程式負責**載入與儲存 CSV 檔案。外掛面板**不需要知道**來源檔案路徑或輸出檔案路徑。
- `self.context.csv_data`（即 `CsvData` 物件）**必定存在**，不論是否已載入資料。可安全存取 `csv_data.num_cols`、`csv_data.get_column_header()` 等屬性，無需做 None 檢查。

#### 2.3.2 Config 管理原則

外掛面板**建議自行宣告並管理 Config dataclass**，作為可靠的資料來源與實作建議：

1. **即時同步**：使用者每次變更 UI 元件時，立即寫入 Config，並設定 `config.dirty = True`。
2. **無實際變更則不設 dirty**：若新值與舊值相同，跳過寫入與設 dirty。
3. **欄位 index 記錄**：
   - 純欄位選單：Config 記錄 `combo.currentData()`，即 0-based 欄位 index。
   - 含非欄位選項的選單：Config 記錄 UI 上的 0-based index（含偏移），序列化/反序列化時再做映射（見 [2.2.6 節](#226-含非欄位選項的選單例如所有欄位)）。
4. **序列化/反序列化**：實作 `serialize_config()` 與 `deserialize_config()`，主程式負責在適當時機呼叫。

#### 2.3.3 Restore Config 的執行時機與 Signal 管理

- Restore Config（`deserialize_config` 被呼叫）**只發生在程式剛啟動時**，不必考慮 Config 在執行期間被 restore 事件覆蓋的情況。
- Restore Config 時，**強烈建議使用 `blockSignals(True/False)` 暫時切斷所有 UI 元件的信號**，這是避免還原過程觸發 `_on_xxx_changed` 等事件而誤設 dirty flag 的**最佳實踐**：

```python
def _restore_ui_from_config(self) -> None:
    widgets = [self.combo_a, self.combo_b, self.slider_c]
    for w in widgets:
        w.blockSignals(True)
    try:
        self.combo_a.setCurrentIndex(self.config.col_a)
        self.combo_b.setCurrentIndex(self.config.col_b)
        self.slider_c.setValue(self.config.val_c)
    finally:
        for w in widgets:
            w.blockSignals(False)
```

#### 2.3.4 Config 有效性驗證時機

- **建議做法**：僅在開始執行任務前（`run_main_action()` / 按鈕 `on_clicked`）驗證 Config 是否有效。
- **最佳實踐**：平常無須特別根據資料是否已載入、或載入的資料是否符合 Config 內容，動態啟用/禁用元件或彈出警告，以保持 UI 反應的流暢度。

#### 2.3.5 靜默儲存請求

外掛執行任務並修改資料後，若需觸發主程式自動儲存，發送 `request_silent_save` Signal：

```python
self.request_silent_save.emit()
```

#### 2.3.6 通知主程式資料已變更

外掛修改 `csv_data.all_rows` 內容後，**務必**通知主程式以同步資料狀態：

```python
self.context.csv_data.set_modified(True)
self.context.csv_data.data_changed.emit()
```

---

## 第三部分：API 參考與嚴格規範

### 3.1 事件通訊機制（Signal）

以下 Signal 均定義於 `BasePluginPanel`，直接在 `self` 上 emit 即可。

| Signal | 簽名 | 觸發時機 |
|--------|------|---------|
| `request_lock_ui` | `pyqtSignal(bool)` | 任務開始時 emit `True` 鎖定全域 UI；結束時 emit `False` 解鎖 |
| `progress_updated` | `pyqtSignal(int, int)` | 更新進度條，參數為 `(current, total)` |
| `status_updated` | `pyqtSignal(str)` | 更新狀態列文字 |
| `log_emitted` | `pyqtSignal(str, str)` | 輸出 Log 訊息，參數為 `(level, message)`，`level` 建議使用 `"INFO"`、`"WARNING"`、`"ERROR"` |
| `request_start_worker` | `pyqtSignal(object)` | 請求主程式在 Worker Thread 中執行傳入的可呼叫物件（適用於需要背景執行的任務） |
| `request_silent_save` | `pyqtSignal()` | 任務完成後，請求主程式靜默（不彈對話框）儲存當前 CSV 資料 |

**便捷方法一覽**（等同直接 emit 對應 Signal）：

```python
self.lock_ui(True)                       # 等同 self.request_lock_ui.emit(True)
self.update_progress(50, 100)            # 等同 self.progress_updated.emit(50, 100)
self.update_status("處理中...")          # 等同 self.status_updated.emit("處理中...")
self.write_log("INFO", "開始執行任務")   # 等同 self.log_emitted.emit("INFO", "開始執行任務")
```

**基底類別自動訂閱的 CsvData Signal**：

| CsvData Signal | 觸發時機 | 基底類別行為 |
|---------------|---------|-------------|
| `data_loaded` | CSV 載入或解除載入 | 自動呼叫 `show_controls()` 或 `reset_panel()`，並呼叫 `on_csv_data_refreshed()` |
| `header_state_changed` | 「第一行為標題」狀態切換 | 自動呼叫 `on_csv_data_refreshed()` |

子類別只需複寫 `on_csv_data_refreshed()` 即可響應以上兩個事件。

---

### 3.2 樣式套用函式（theme）

以下函式全部定義於 `plugin_sdk.theme`，**直接傳入 Widget 物件**即可套用樣式。

```python
from plugin_sdk.theme import (
    applyStandardLabelStyle,
    applyStandardButtonStyle,
    applyStandardLineEditStyle,
    applyStandardComboBoxStyle,
    applyStandardCheckBoxStyle,
    applyStandardSliderStyle,
    applyTitleLabel,
    applyHintLabel,
    applyPrimaryButtonStyle,
    SIDEBAR_MAX_WIDTH,
    WidgetType,
    getStandardFontSize,
    getStandardTextColor,
    getStandardBgColor,
    getStandardBorder,
    getStandardBorderRadius,
)
```

| 函式 | 適用元件 | 說明 |
|------|---------|------|
| `applyStandardLabelStyle(widget)` | `QLabel` | 標準說明文字樣式 |
| `applyStandardButtonStyle(widget)` | `QPushButton` | 標準次要按鈕樣式（非主要任務按鈕） |
| `applyStandardLineEditStyle(widget)` | `QLineEdit` | 標準文字輸入框樣式 |
| `applyStandardComboBoxStyle(widget)` | `QComboBox` | 標準下拉選單樣式 |
| `applyStandardCheckBoxStyle(widget)` | `QCheckBox` | 標準核取方塊樣式 |
| `applyStandardSliderStyle(widget)` | `QSlider` | 標準滑桿樣式 |
| `applyTitleLabel(widget)` | `QLabel` | 面板章節標題樣式（藍色粗體） |
| `applyHintLabel(widget)` | `QLabel` | 提示文字樣式（灰色斜體，如「尚未載入資料」） |
| `applyPrimaryButtonStyle(button, is_running=False)` | `QPushButton` | **主要任務按鈕**專用。`is_running=False` 為就緒（藍色），`is_running=True` 為停止（紅色） |
| `SIDEBAR_MAX_WIDTH` | 常數 | 面板最大寬度，值為 `341`（px） |

**低階色彩/樣式查詢函式**（進階用途，一般開發直接使用上列高階函式即可）：

| 函式 | 說明 |
|------|------|
| `getStandardFontSize(widget_type: WidgetType) -> int` | 回傳指定元件類型的標準字型大小 |
| `getStandardTextColor(widget_type: WidgetType, state: str = "normal") -> str` | 回傳指定元件在指定狀態下的文字色彩（十六進位字串） |
| `getStandardBgColor(widget_type: WidgetType, state: str = "normal") -> str` | 回傳指定元件在指定狀態下的背景色彩（十六進位字串） |
| `getStandardBorder(widget_type: WidgetType, state: str = "normal") -> str` | 回傳指定元件在指定狀態下的邊框樣式字串 |
| `getStandardBorderRadius(widget_type: WidgetType) -> str` | 回傳指定元件的圓角半徑字串 |

`WidgetType` 列舉值：`STD_LABEL`、`STD_BUTTON`、`STD_LINE_EDIT`、`STD_COMBO_BOX`、`STD_CHECK_BOX`、`STD_SLIDER`

---

### 3.3 共用資料（common_data）

外掛透過 `self.context`（`PluginContext` 物件）存取 CSV 資料，**不得**直接 import `common_data` 模組。

#### PluginContext

```python
# 存取方式（在 BasePluginPanel 子類別中）
self.context.csv_data             # CsvData 物件，必定不為 None
self.context.is_data_loaded       # bool，True 表示資料已載入（all_rows 非空）
self.context.is_first_row_header  # bool，True 表示第一行為標題
```

#### CsvData 屬性與方法

| 屬性 / 方法 | 型別 | 說明 |
|------------|------|------|
| `csv_data.all_rows` | `List[List[str]]` | 所有列的原始資料（含標題行） |
| `csv_data.num_cols` | `int` | 最大欄位數 |
| `csv_data.is_header` | `bool` | 是否以第一行為標題 |
| `csv_data.is_modified` | `bool` | 資料是否已修改 |
| `csv_data.visible_indices` | `List[int]` | 目前可見（未被過濾）的列索引 |
| `csv_data.get_column_header(col: int) -> str` | `str` | 取得第 `col` 欄（0-based）的標頭文字 |
| `csv_data.get_visible_indices() -> List[int]` | `List[int]` | 同 `visible_indices` |
| `csv_data.get_visible_rows() -> List[List[str]]` | `List[List[str]]` | 取得所有可見列的資料 |
| `csv_data.update_cell(row, col, value)` | `None` | 更新指定儲存格的值，**自動**設 `is_modified=True` 並 emit `data_changed` |
| `csv_data.set_modified(modified: bool)` | `None` | 手動設定修改狀態 |

**CsvData Signals**（外掛可連接，但通常透過基底類別自動處理）：

| Signal | 簽名 | 說明 |
|--------|------|------|
| `data_loaded` | `pyqtSignal()` | 資料載入或解除載入後發出 |
| `data_changed` | `pyqtSignal()` | 儲存格內容變更後發出 |
| `filter_changed` | `pyqtSignal()` | 過濾條件變更後發出 |
| `header_state_changed` | `pyqtSignal(bool)` | 「第一行為標題」狀態切換後發出 |
| `modified_changed` | `pyqtSignal(bool)` | `is_modified` 狀態切換後發出 |

---

### 3.4 工具函式（utils）

以下工具函式定義於 `utils` 模組，外掛可直接 import 使用。

```python
from utils import ThrottledProgress
```

#### `ThrottledProgress`

限制 Signal 發送頻率的 Helper，適合在任務迴圈中使用，避免過於頻繁地更新進度條而影響效能。

```python
from utils import ThrottledProgress

# 建立：傳入目標 Signal，預設每秒最多 5 次（間隔 0.2 秒）
throttled = ThrottledProgress(self.progress_updated, min_interval=0.2)

# 使用：在迴圈中呼叫 emit，會自動過濾過於頻繁的呼叫
throttled.emit(current, total)

# 強制發送（不受頻率限制，適合最後一筆）
throttled.emit(total, total, force=True)
```

| 方法 | 說明 |
|------|------|
| `ThrottledProgress(signal, min_interval=0.2)` | 建構，傳入 `pyqtSignal` 物件與最小間隔秒數 |
| `.emit(*args, force=False) -> bool` | 嘗試發送；回傳 `True` 表示成功發送，`False` 表示被過濾 |

---

### 3.5 隔離限制與開發建議（Anti-patterns & Best Practices）

以下包含**嚴格禁止**的行為（違反將導致面板無法正常載入、系統崩潰或與主程式衝突），以及開發時的**最佳實踐**。

#### 禁止直接存取主程式模組

外掛**只允許** import 以下模組，不得引用任何其他主程式內部模組：

```
✅ 允許：plugin_sdk
✅ 允許：utils
✅ 允許：PyQt6（標準框架）
✅ 允許：Python 標準函式庫（os、sys、dataclasses 等）
✅ 允許：外掛自身資料夾內的子模組

❌ 禁止：from src.ui import ...
❌ 禁止：from src.base import ...
❌ 禁止：直接 from common_data.csv_data import CsvData（應透過 self.context.csv_data 存取）
❌ 禁止：存取主程式的任何 AppContext、MainWindow 或其他內部類別
```

#### 禁止發明不存在的 API

- **禁止**呼叫任何本文件未列出的 `plugin_sdk`、`common_data`、`utils` 介面。
- **禁止**假設 `BasePluginPanel` 有除本文件所列以外的 Signal 或方法。

#### 建議避免在 Restore Config 期間觸發 dirty flag

Restore Config（`deserialize_config` / `_restore_ui_from_config`）期間，**建議使用** `blockSignals` 保護所有 UI 元件，避免還原操作錯誤設置 `config.dirty = True`。

#### 禁止外掛自行讀寫 CSV 檔案

外掛**不得**直接讀取或寫入 CSV 檔案。所有資料變更必須透過 `csv_data.update_cell()` 或 `csv_data.set_modified()` 操作，並在需要時 emit `request_silent_save` 通知主程式儲存。

#### 建議避免自行修改 get_column_header 的回傳格式

`csv_data.get_column_header(i)` 的回傳格式由主程式統一管理。**最佳實踐**是外掛避免在回傳值上自行加入任何前綴或後綴。

#### 建議避免在 controls_layout 以外的位置直接加入 Widget

當 `require_data_loading=True` 時，`self.controls_layout` 是主要建議加入 Widget 的佈局。若直接操作 `self.main_layout`，可能會影響基底類別管理的「尚未載入資料」提示可見性邏輯。

#### 禁止在 `__init__` 中呼叫 `show_controls()` 或 `reset_panel()`

這兩個方法由基底類別根據 `data_loaded` Signal 自動呼叫，**禁止**在 `__init__` 或其他非響應事件的地方手動呼叫，以免造成初始顯示狀態錯誤。

---

*文件版本：對應 plugin_sdk 版本截至 2026-06-29。*
