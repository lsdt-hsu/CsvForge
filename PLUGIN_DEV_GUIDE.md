# CsvForge 外掛開發指南 (PLUGIN_DEV_GUIDE.md)

> **版本基準**：本指南依照 `src/plugin_sdk/panel_base.py`、`src/plugin_sdk/plugin_api.py`、`src/plugin_sdk/theme.py`、`src/utils/throttler.py`、`src/common_data/csv_data.py` 最新原始碼撰寫。
> **AI Agent 使用說明**：閱讀本文件後，你應能在不詢問人類的前提下，100% 正確產出合規的外掛面板。

---

## 目錄

- [第零部分：AI Agent 實作提問指引](#第零部分-ai-agent-實作提問指引-agent-directives)
- [第一部分：核心觀念與快速起步](#第一部分核心觀念與快速起步-core-concepts--boilerplate)
  - [1.1 雙門面隔離](#11-雙門面隔離-dual-facade-isolation)
  - [1.2 檔案結構規範](#12-檔案結構規範)
  - [1.3 Import 方式](#13-import-方式重要)
  - [1.4 終極樣板程式碼](#14-終極樣板程式碼-boilerplate)
- [第二部分：API 參考與生命週期](#第二部分api-參考與生命週期-api-reference--lifecycle)
  - [2.1 PluginAPI 對講機完整參考手冊](#21-pluginapi-對講機完整參考手冊)
  - [2.2 事件鉤子](#22-事件鉤子-lifecycle-hooks)
  - [2.3 UI 輔助方法](#23-ui-輔助方法)
  - [2.4 CsvData 資料介面參考](#24-csvdata-資料介面參考)
  - [2.5 核心一致性策略](#25-核心一致性策略-core-consistency-rules)
  - [2.6 樣式套用規範](#26-樣式套用規範-theme)
  - [2.7 UI 與 Config 最佳實踐](#27-ui-與-config-最佳實踐-ux-best-practices)
  - [2.8 UI 佈局與圖示設計規範](#28-ui-佈局與圖示設計規範-layout--icon-design)
- [第三部分：進階工具與效能優化](#第三部分進階工具與效能優化)
  - [3.1 ThrottledProgress — 進度更新限流器](#31-throttledprogress--進度更新限流器)
- [第四部分：絕對禁止的反模式](#第四部分絕對禁止的反模式-strict-anti-patterns)
  - [反模式 1：直接 emit 私有信號](#-反模式-1直接-emit-私有信號)
  - [反模式 2：使用 hasattr / getattr 跨界猜測主程式狀態](#-反模式-2使用-hasattr--getattr-跨界猜測主程式狀態)
  - [反模式 3：匯入或使用 PluginHostAdapter](#-反模式-3匯入或使用-pluginhostadapter)
  - [反模式 4：直接呼叫主程式生命週期方法](#-反模式-4直接呼叫主程式生命週期方法)
  - [反模式 5：Hardcode QSS 樣式](#-反模式-5hardcode-qss-樣式)
  - [反模式 6：在 Config 操作中省略 blockSignals](#-反模式-6在-config-操作中省略-blocksignals)
  - [反模式 7：在資料解除載入或重載時清除 Config 狀態](#-反模式-7在資料解除載入或重載時清除-config-狀態)
- [附錄：_internal_ 方法快速參考](#附錄internal_-方法快速參考)

---

## 第零部分：AI Agent 實作提問指引 (Agent Directives)

身為 AI 開發助理，在協助使用者建立全新的外掛實作計畫（Implementation Plan）時，【必須】主動將以下 Optional 進階功能列為 **Open Questions** 向使用者確認，絕對不可擅自省略：
1. **防止系統休眠**：任務耗時是否較長？是否需要在呼叫 `run_worker` 時開啟 `prevent_sleep=True`？
2. **靜默存檔 (Silent Save)**：任務結束或中斷後，是否需要呼叫 `self.api.request_silent_save()` 進行背景存檔？（建議：若任務會大量修改 CSV 資料，強烈建議開啟）

---

## 第一部分：核心觀念與快速起步 (Core Concepts & Boilerplate)

### 1.1 雙門面隔離 (Dual Facade Isolation)

外掛是一個繼承自 `BasePluginPanel` 的 **PyQt UI 實體**，它與主程式之間存在一道嚴格的邊界。

```
┌──────────────────────────────────────────────────────────────┐
│  主程式 (Host)                                                │
│  LeftPanel ──→ PluginHostAdapter ──→ BasePluginPanel (你的外掛) │
│                                              │                │
│                                         self.api             │
│                                        (PluginAPI)           │
│                                              │                │
│                                    ←── 唯一對外通道 ──→      │
└──────────────────────────────────────────────────────────────┘
```

**黃金守則**：

| 角色 | 可存取的物件 | 禁止存取的物件 |
|------|------------|--------------|
| 外掛（你） | `self.api`、`self.context` | 主程式任何模組、`PluginHostAdapter`、`BasePluginPanel` 的私有信號 |
| 主程式 | `PluginHostAdapter` | 外掛內部邏輯、`PluginAPI` |

開發者不需要、也不應該知道主程式的實作細節。所有對外通訊皆透過 `self.api`。

---

### 1.2 檔案結構規範

外掛存放在任意路徑下，**必須**包含 `plugin.py` 作為唯一入口：

```
your_plugin_folder/
└── plugin.py          ← 唯一入口，必須定義繼承 BasePluginPanel 的類別
```

主程式透過路徑動態載入 `plugin.py`，外掛的主類別名稱【必須嚴格命名為 `PanelClass`】，主程式會以此名稱進行動態載入。絕對不可使用其他名稱。

---

### 1.3 Import 方式（重要）

由於外掛可能存放在電腦上的任意路徑，**無法**使用相對 import 或假設 `plugin_sdk` 在 Python Path 中。主程式在載入外掛前，會確保 `src/` 目錄已加入 `sys.path`，因此外掛應使用以下方式匯入 SDK：

```python
# ✅ 正確：使用頂層套件名稱（主程式已處理 sys.path）
from plugin_sdk import BasePluginPanel, PluginContext
from plugin_sdk import theme
```

> **注意**：`PluginHostAdapter` 刻意未在 `plugin_sdk/__init__.py` 中 export，外掛開發者**無法**且**不應**匯入它。

---

### 1.4 終極樣板程式碼 (Boilerplate)

以下是一個完整、最小可執行的 `plugin.py` 範本，涵蓋所有必須實作的生命週期方法、`blockSignals` 防呆、非欄位選項映射，以及透過 `self.api` 啟動任務的標準流程。**直接複製後修改業務邏輯即可。**

```python
# plugin.py — 外掛面板入口 (完整 Boilerplate)
# 主程式在載入本檔案前，已確保 src/ 目錄在 sys.path 中，
# 因此直接以頂層套件名稱匯入即可。
import uuid

from PyQt6.QtWidgets import QPushButton, QLabel, QComboBox
from PyQt6.QtCore import pyqtSignal, QObject

from plugin_sdk import BasePluginPanel, PluginContext
from plugin_sdk import theme


# ── (選用) 若有耗時背景任務，建議使用 Worker 模式 ──────────────

class _MyWorker(QObject):
    """背景 Worker：不阻塞主線程。"""
    progress = pyqtSignal(int, int)   # current, total
    finished = pyqtSignal(str)        # "finished" | "error" | "cancelled"

    def __init__(self):
        super().__init__()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        """模擬耗時任務（請替換為實際業務邏輯）。"""
        total = 100
        for i in range(total):
            if self._cancelled:
                self.finished.emit("cancelled")
                return
            # --- 實際業務邏輯放這裡 ---
            self.progress.emit(i + 1, total)
        self.finished.emit("finished")


# ── 外掛主類別 ─────────────────────────────────────────────────────────────

class PanelClass(BasePluginPanel):
    """
    外掛面板主類別。
    繼承 BasePluginPanel，透過 self.api 與主程式溝通。
    """

    # 【必要】：定義此外掛的固定 UUID（每個外掛獨立產生，勿重複）
    _UUID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"  # 請替換為 str(uuid.uuid4())

    # 非欄位選項的 UI 索引偏移量（無特殊非欄位選項時設為 0）
    _N_NON_COL_OPTIONS = 0

    def __init__(self, context: PluginContext, parent=None):
        super().__init__(
            parent=parent,
            title_text="我的外掛",       # 顯示在面板頂端的標題
            require_data_loading=True,   # True = 需等待 CSV 載入後才顯示操作 UI
            context=context,
        )
        self._worker = None
        self._config_selected_col = 0   # 儲存還原的欄位設定值（預設選擇第 1 欄）
        self._setup_ui()

    # ── UI 初始化 ──────────────────────────────────────────────────────────

    def _setup_ui(self):
        """建立面板 UI，所有 Widget 加入 self.controls_layout。"""
        # 說明文字
        self.lbl_desc = QLabel("選擇欄位後點擊按鈕執行任務")
        theme.applyStandardLabelStyle(self.lbl_desc)
        self.controls_layout.addWidget(self.lbl_desc)

        # 下拉選單（僅包含實際欄位項目）
        # UI index k → 實際欄位 k（stored value = k）
        self.combo_col = QComboBox()
        theme.applyStandardComboBoxStyle(self.combo_col)
        self.combo_col.currentIndexChanged.connect(self._on_combo_changed)
        self.controls_layout.addWidget(self.combo_col)

        # 彈性填充（將上方元件推頂，讓主按鈕固定於面板底部）
        self.controls_layout.addStretch()

        # 主要動作按鈕
        self.btn_start = QPushButton("開始處理")
        theme.applyPrimaryButtonStyle(self.btn_start, is_running=False)
        self.btn_start.clicked.connect(self._on_btn_clicked)
        self.controls_layout.addWidget(self.btn_start)

    # ── 欄位選項 Index 映射 ──────────────────────────────────────────────────
    # 映射規則：
    #   UI index k            → stored value k（實際欄位索引）
    #   stored value col_idx  → UI index col_idx

    def _ui_to_stored(self, ui_index: int) -> int:
        """將 UI combo index 轉換為要儲存在 config 的整數值。
        當 _N_NON_COL_OPTIONS = 0 時，直接回傳傳入的 index。
        """
        return ui_index - self._N_NON_COL_OPTIONS

    def _stored_to_ui(self, stored: int) -> int:
        """將 config 中的整數值轉換回 UI combo index。
        當 _N_NON_COL_OPTIONS = 0 時，直接回傳傳入的 stored 值。
        """
        return stored + self._N_NON_COL_OPTIONS

    def _on_combo_changed(self, ui_index: int) -> None:
        """下拉選單異動時，即時同步更新內部 Config 變數。"""
        self._config_selected_col = self._ui_to_stored(ui_index)

    # ── 資料刷新 ──────────────────────────────────────────────────────────

    def on_csv_data_refreshed(self) -> None:
        """CSV 資料載入或標頭狀態變更時自動觸發。"""
        if not self.context or not self.context.is_data_loaded:
            return

        # 計算安全上限，確保能容納 Config 中已儲存的欄位索引
        limit = max(
            self.context.csv_data.num_cols,
            self._config_selected_col + 1
        )

        # 切斷信號，防止填充選單時觸發 currentIndexChanged 導致 dirty 標記
        self.combo_col.blockSignals(True)
        try:
            self.combo_col.clear()
            for col in range(limit):
                header = self.context.csv_data.get_column_header(col)
                self.combo_col.addItem(header)

            # 重新選取原本設定的值 (因 limit 公式已履約保證，此處直接 set 即可)
            ui_index = self._stored_to_ui(self._config_selected_col)
            self.combo_col.setCurrentIndex(ui_index)
        finally:
            self.combo_col.blockSignals(False)

    # ── 按鈕點擊邏輯 ───────────────────────────────────────────────────────

    def _on_btn_clicked(self):
        # 1. 執行前驗證：在此處檢查 Config 是否合法，若失敗則提示並 return
        # if self._config_selected_col < 0:
        #     self.api.write_log("WARNING", "請先選擇有效的欄位")
        #     self.api.update_status("❌ 參數錯誤")
        #     return

        # 2. 驗證通過，正式啟動任務
        self._worker = _MyWorker()
        # 主程式會自動接管 Thread、進度節流、UI 鎖定與結束清理
        self.api.run_worker(self._worker, task_name="我的外掛任務", total=100)

    # ── _internal_ 生命週期方法（必須全部覆寫）────────────────────────────

    def _internal_get_uuid(self) -> str:
        """回傳此外掛的唯一 UUID 字串。"""
        return self._UUID

    def _internal_get_package_name(self) -> str:
        """回傳此外掛在設定檔中對應的識別名稱（英文小寫，無空格）。"""
        return "my_plugin"

    def _internal_serialize_config(self) -> dict:
        """
        將面板當前設定序列化為 dict，供主程式存入設定檔。
        由於有即時同步機制，此處直接回傳已同步的內部 Config 變數。
        """
        return {
            "selected_col": self._config_selected_col,
        }

    def _internal_deserialize_config(self, data: dict) -> None:
        """
        從設定檔 dict 還原面板設定。

        【防呆關鍵】：必須在操作 UI 元件前後呼叫 blockSignals(True/False)，
        防止還原設定時觸發元件的 currentIndexChanged 等信號，
        進而錯誤地將文件標記為已修改（dirty）。
        """
        self._config_selected_col = data.get("selected_col", 0)  # 預設選擇第 1 欄
        ui_index = self._stored_to_ui(self._config_selected_col)

        # 切斷信號，確保還原設定不觸發任何副作用
        self.combo_col.blockSignals(True)
        try:
            # 邊界防呆：確保 ui_index 在合法範圍內
            max_index = self.combo_col.count() - 1
            safe_index = max(0, min(ui_index, max_index)) if max_index >= 0 else 0
            self.combo_col.setCurrentIndex(safe_index)
        finally:
            # 使用 finally 確保即使發生例外，信號也必然被恢復
            self.combo_col.blockSignals(False)

    def _internal_set_enabled(self, enabled: bool) -> None:
        """UI 鎖定/解鎖時同步更新內部元件狀態。"""
        super()._internal_set_enabled(enabled)
        # 注意：負責取消任務的主按鈕（如 btn_start）不應被停用，否則使用者無法點擊取消
        self.combo_col.setEnabled(enabled)
```

---

## 第二部分：API 參考與生命週期 (API Reference & Lifecycle)

### 2.1 PluginAPI 對講機完整參考手冊

`self.api` 是 `PluginAPI` 的實例，由 `BasePluginPanel.__init__` 自動建立，外掛透過它進行**所有**對外通訊。

---

#### `self.api.start_task(task_name, total, initial_log, prevent_sleep)`

通知主程式背景任務已啟動。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `task_name` | `str` | ✅ | 任務顯示名稱，出現在狀態列 |
| `total` | `int` | ❌（預設 `0`） | 初始總進度量，`0` 表示不定量 |
| `initial_log` | `str` | ❌（預設 `""`） | 任務開始時寫入日誌的初始訊息 |
| `prevent_sleep` | `bool` | ❌（預設 `False`） | 任務期間是否阻止系統休眠 |

> **⚠️ 架構限制（極重要）**：呼叫 `start_task()` 後，**嚴禁**再呼叫 `self.api.lock_ui(True)`。
> `start_task` 內部已隱含全域 UI 鎖定語意，重複呼叫將導致狀態不一致。
>
> **⚠️ 注意**：若外掛使用 `run_worker` 託管背景任務，主程式會自動呼叫此方法。外掛開發者【嚴禁】在呼叫 `run_worker` 前後手動呼叫 `start_task`，以免破壞主程式狀態機。

---

#### `self.api.finish_task(status)`

通知主程式背景任務已結束，主程式將自動解鎖 UI 並停止計時器。

| 參數 | 型別 | 合法值 |
|------|------|--------|
| `status` | `str` | `"finished"` \| `"error"` \| `"cancelled"` |

> **⚠️ 注意**：若外掛使用 `run_worker` 託管背景任務，主程式會自動呼叫此方法。外掛開發者【嚴禁】在呼叫 `run_worker` 前後手動呼叫 `finish_task`，以免破壞主程式狀態機。

---

#### `self.api.run_worker(worker, task_name, total, initial_log, prevent_sleep)`

將一個背景 Worker 物件託管給主程式。主程式會自動為其建立 QThread、自動套用進度節流、管理資源釋放，並在結束時自動解鎖 UI。

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `worker` | `QObject` | ✅ | 背景執行的 Worker 實例，必須具備 `run()` 與 `cancel()` 方法，以及標準的 `progress` 與 `finished` 信號 |
| `task_name` | `str` | ✅ | 任務顯示名稱，出現在狀態列 |
| `total` | `int` | ❌（預設 `0`） | 初始總進度量，`0` 表示不定量 |
| `initial_log` | `str` | ❌（預設 `""`） | 任務開始時寫入日誌的初始訊息 |
| `prevent_sleep` | `bool` | ❌（預設 `False`） | 任務期間是否阻止系統休眠 |

> **⚠️ 架構鐵律：外掛嚴禁自行建立 QThread。必須將 Worker 交由此方法託管。**
> 主程式會在內部自動將 `worker` 移動到新建立的線程，並對 `worker.progress` 自動套用 `ThrottledProgress(min_interval=0.2)`，無需開發者手動處理。

---

#### `self.api.update_progress(current, total)`

更新主視窗進度條。

| 參數 | 型別 | 說明 |
|------|------|------|
| `current` | `int` | 目前完成數量 |
| `total` | `int` | 總數量 |

---

#### `self.api.update_status(status)`

更新主視窗狀態列文字。

| 參數 | 型別 | 說明 |
|------|------|------|
| `status` | `str` | 任意狀態文字字串 |

---

#### `self.api.write_log(level, message)`

寫入一筆日誌到主視窗日誌面板。

| 參數 | 型別 | 合法值 |
|------|------|--------|
| `level` | `str` | `"INFO"` \| `"WARNING"` \| `"ERROR"` \| `"SUCCESS"` |
| `message` | `str` | 日誌內容文字 |

---

#### `self.api.lock_ui(lock)`

請求主程式鎖定或解鎖 UI。

| 參數 | 型別 | 說明 |
|------|------|------|
| `lock` | `bool` | `True` 鎖定 / `False` 解鎖 |

> **⚠️ 使用限制**：此方法**僅限**「無背景 Worker，但需在主線程進行短暫阻塞操作」的輕量任務使用。
> **若已呼叫 `start_task()`，嚴禁重複呼叫 `lock_ui(True)`。**

---

#### `self.api.request_silent_save()`

向主程式發起靜默存檔請求（後台存檔，不彈出對話框）。

無參數。

---

### 2.2 事件鉤子 (Lifecycle Hooks)

#### `on_csv_data_refreshed(self) -> None`

覆寫此方法以實現「資料載入時的外掛自動觸發」機制。

觸發時機：
- CSV 資料成功載入後（`data_loaded` 信號）
- CSV 資料的標頭狀態（`is_header`）變更後（`header_state_changed` 信號）

```python
def on_csv_data_refreshed(self) -> None:
    """CSV 資料就緒時自動呼叫，可在此讀取 context 並更新 UI。"""
    if not self.context or not self.context.is_data_loaded:
        return

    # 【防呆】操作 UI 元件前後必須切斷信號
    self.combo_col.blockSignals(True)
    try:
        self.combo_col.clear()
        for col in range(self.context.csv_data.num_cols):
            # 使用 get_column_header 取得標準化的欄位標題
            self.combo_col.addItem(self.context.csv_data.get_column_header(col))
    finally:
        self.combo_col.blockSignals(False)
```

**PluginContext 可用屬性**：

| 屬性 | 型別 | 說明 |
|------|------|------|
| `context.csv_data` | `CsvData` | CSV 資料物件（詳見 2.4 節） |
| `context.is_data_loaded` | `bool` | 是否已載入資料 |
| `context.is_first_row_header` | `bool` | 首行是否為 Header |

---

#### `_internal_set_enabled(self, enabled: bool) -> None`（選用覆寫）

主程式 UI 鎖定/解鎖時觸發，可自訂內部元件的啟用/停用邏輯。**若覆寫，必須呼叫 `super()`**：

```python
def _internal_set_enabled(self, enabled: bool) -> None:
    super()._internal_set_enabled(enabled)
    # 注意：負責取消任務的主按鈕（如 btn_start）不應被停用，否則使用者無法點擊取消
    self.combo_options.setEnabled(enabled)
```

---

### 2.3 UI 輔助方法

`BasePluginPanel` 提供兩個 protected 的 UI 輔助方法，可在子類別中呼叫：

| 方法 | 說明 |
|------|------|
| `self.show_controls()` | 隱藏「尚未載入資料」提示，顯示 `controls_container` |
| `self.hide_controls()` | 顯示「尚未載入資料」提示，隱藏 `controls_container` |

> 注意：只有 `require_data_loading=True` 時這兩個方法才有效。

---

### 2.4 CsvData 資料介面參考

透過 `self.context.csv_data` 存取以下方法與屬性：

#### 可用屬性

| 屬性 | 型別 | 說明 |
|------|------|------|
| `all_rows` | `List[List[str]]` | 全部列資料（含 Header 行） |
| `num_cols` | `int` | 最大欄位數 |
| `is_header` | `bool` | 首行是否為 Header |
| `is_modified` | `bool` | 資料是否已被修改（未存檔） |
| `file_path` | `str \| None` | 目前開啟的 CSV 檔案路徑 |
| `delimiter` | `str` | 分隔符（如 `","` 或 `"\t"`） |
| `encoding` | `str` | 檔案編碼（如 `"utf-8"`） |

#### 可用方法

| 方法 | 回傳型別 | 說明 |
|------|---------|------|
| `get_visible_indices()` | `List[int]` | 取得當前可見列的 `all_rows` 索引清單 |
| `get_visible_rows()` | `List[List[str]]` | 取得當前可見的列資料 |
| `get_column_header(col: int)` | `str` | 取得標準化欄位標題字串（**必須**使用此方法，禁止自行拼接格式） |
| `update_cell(row, col, value)` | `None` | 更新單一儲存格並自動發射 `data_changed` 信號 |
| `set_modified(modified: bool)` | `None` | 手動設定修改狀態 |

#### 可用信號（唯讀，僅供 `connect` 訂閱）

| 信號 | 觸發時機 |
|------|---------|
| `data_loaded` | CSV 檔案重新載入完成 |
| `data_changed` | 任意儲存格資料變更 |
| `filter_changed` | 篩選條件變更（影響可見列） |
| `header_state_changed(bool)` | 首行 Header 狀態切換 |
| `modified_changed(bool)` | 修改狀態（is_modified）變更 |

---

### 2.5 核心一致性策略 (Core Consistency Rules)

本節為外掛開發的**強制規範**，確保所有外掛對 CSV 資料的存取與修改行為一致，不破壞主程式的狀態管理。

---

#### 策略 1：資料走訪安全（優先使用可見列）

外掛在走訪 CSV 資料時，**強烈建議**使用 `get_visible_indices()` 取得可見列索引，而非直接遍歷 `all_rows`。這確保外掛不會意外修改被篩選條件隱藏的列。

```python
# ✅ 正確：只操作可見列，不動到隱藏資料
visible_indices = self.context.csv_data.get_visible_indices()
for row_idx in visible_indices:
    row = self.context.csv_data.all_rows[row_idx]
    # --- 對 row 進行讀取或處理 ---

# ❌ 危險：直接遍歷 all_rows 會動到被篩選隱藏的列
for row in self.context.csv_data.all_rows:
    ...
```

> **注意**：`get_visible_indices()` 已自動排除 Header 行（當 `is_header=True` 時），無需手動判斷。

---

#### 策略 2：資料修改後的標準同步流程

外掛在批次修改 `all_rows` 後（例如不使用 `update_cell` 的情況），**必須**手動執行以下兩行代碼通知主程式：

```python
# 【必須執行的兩行】：修改資料後的標準通知流程
self.context.csv_data.set_modified(True)
self.context.csv_data.data_changed.emit()
```

> **說明**：若使用 `CsvData.update_cell(row, col, value)` 進行單格修改，這兩行已內建，不需重複呼叫。
> 只有在手動直接修改 `all_rows` 後才需要手動呼叫。

---

#### 策略 3：進階選單映射 (非欄位選項處理)

> **警語**：**一般情況下**，若選單僅包含實際欄位，`_N_NON_COL_OPTIONS` 應設為 `0`，UI index 即等於實際欄位 index。**僅當**選單需要包含『所有欄位』等特殊選項時，才需要參考以下映射規則。

當 ComboBox 包含「所有欄位」等非實際欄位的選項時，UI index 與設定檔儲存值之間存在偏移量，**必須**使用映射方法進行轉換，不得在程式碼中硬編碼偏移數字。

**標準映射表**（假設有 2 個非欄位選項「所有欄位」、「手動輸入」）：

| UI index | stored value（config 儲存值） | 語意 |
|----------|------------------------------|------|
| `0` | `-1` | 「所有欄位」（非欄位特殊項，第一個選項） |
| `1` | `-2` | 「手動輸入」（非欄位特殊項，第二個選項） |
| `2` | `0` | 實際欄位 0（第 1 欄） |
| `3` | `1` | 實際欄位 1（第 2 欄） |
| `N` | `N - _N_NON_COL_OPTIONS` | 實際欄位 N-2 |

**實作規範**：在外掛類別內定義 `_N_NON_COL_OPTIONS`（非欄位選項數量），並透過 `_ui_to_stored` / `_stored_to_ui` 方法轉換，**不得**在 `_internal_serialize_config` 或 `_internal_deserialize_config` 中直接加減數字偏移量。

---

#### 策略 4：`blockSignals` 防呆（Config 還原與 UI 填充）

在以下兩種情況下，**必須**使用 `blockSignals(True/False)` 包圍操作：

1. `_internal_deserialize_config` 中還原 UI 元件狀態時
2. `on_csv_data_refreshed` 中重新填充選單/欄位時

```python
# ✅ 正確：使用 try/finally 確保信號必然恢復
widget.blockSignals(True)
try:
    widget.setCurrentIndex(some_index)
    # 或 widget.clear() + widget.addItem(...)
finally:
    widget.blockSignals(False)

# ❌ 危險：若中間發生例外，信號將永遠被切斷
widget.blockSignals(True)
widget.setCurrentIndex(some_index)  # 若此處 crash，下行永遠不會執行
widget.blockSignals(False)
```

---

### 2.6 樣式套用規範 (Theme)

**嚴格規則**：開發外掛 UI 時，**必須優先呼叫 `plugin_sdk.theme` 提供的 `applyXXXStyle` 函式**，**嚴禁手動 hardcode QSS 樣式或顏色值**。

匯入方式：
```python
from plugin_sdk import theme
```

#### 高階樣式函式（優先使用）

| 函式 | 適用元件 | 說明 |
|------|---------|------|
| `theme.applyStandardLabelStyle(widget)` | `QLabel` | 標準說明文字樣式 |
| `theme.applyStandardButtonStyle(widget)` | `QPushButton` | 標準次要按鈕樣式 |
| `theme.applyStandardLineEditStyle(widget)` | `QLineEdit` | 標準單行文字輸入框樣式 |
| `theme.applyStandardComboBoxStyle(widget)` | `QComboBox` | 標準下拉選單樣式 |
| `theme.applyStandardCheckBoxStyle(widget)` | `QCheckBox` | 標準核取方塊樣式 |
| `theme.applyStandardSliderStyle(widget)` | `QSlider` | 標準滑桿樣式 |
| `theme.applyTitleLabel(widget)` | `QLabel` | 面板標題樣式（藍色粗體） |
| `theme.applyHintLabel(widget)` | `QLabel` | 提示文字樣式（灰色斜體） |
| `theme.applyPrimaryButtonStyle(widget, is_running=False)` | `QPushButton` | 主要動作按鈕（`is_running=False` 藍色，`is_running=True` 紅色停止） |

#### 低階色彩/樣式查詢函式（進階使用）

僅在需要**自訂元件且無法直接套用高階函式**時，才使用以下低階查詢 API。

首先匯入 `WidgetType` 枚舉：

```python
from plugin_sdk.theme import WidgetType
```

**`WidgetType` 枚舉值**：

| 枚舉值 | 對應元件 |
|--------|---------|
| `WidgetType.STD_LABEL` | `QLabel` |
| `WidgetType.STD_BUTTON` | `QPushButton` |
| `WidgetType.STD_LINE_EDIT` | `QLineEdit` |
| `WidgetType.STD_COMBO_BOX` | `QComboBox` |
| `WidgetType.STD_CHECK_BOX` | `QCheckBox` |
| `WidgetType.STD_SLIDER` | `QSlider` |

**低階查詢函式**：

| 函式 | 回傳型別 | 說明 |
|------|---------|------|
| `theme.getStandardFontSize(widget_type)` | `int` | 取得標準字型大小（目前恆為 `13`） |
| `theme.getStandardTextColor(widget_type, state="normal")` | `str` | 取得文字顏色 HEX 值 |
| `theme.getStandardBgColor(widget_type, state="normal")` | `str` | 取得背景顏色 HEX 值 |
| `theme.getStandardBorder(widget_type, state="normal")` | `str` | 取得邊框樣式字串 |
| `theme.getStandardBorderRadius(widget_type)` | `str` | 取得圓角半徑字串（目前恆為 `"6px"`） |
| `theme.getTitleTextColor()` | `str` | 取得面板標題的標準文字色彩 HEX 值 |
| `theme.getTitleFontSize()` | `int` | 取得面板標題的標準字型大小 |

**`state` 合法值**：

| state 值 | 說明 |
|---------|------|
| `"normal"` | 一般狀態（預設） |
| `"hover"` | 滑鼠懸停（僅 `STD_BUTTON` 有效） |
| `"pressed"` | 按下（僅 `STD_BUTTON` 有效） |
| `"disabled"` | 停用（僅 `STD_BUTTON` 有效） |
| `"focus"` | 鍵盤焦點（僅 `STD_LINE_EDIT`、`STD_COMBO_BOX` 有效） |

**低階函式使用範例**：

```python
from plugin_sdk import theme
from plugin_sdk.theme import WidgetType

# 自訂複合元件需要手動拼接 QSS 時
font_size = theme.getStandardFontSize(WidgetType.STD_LABEL)
text_color = theme.getStandardTextColor(WidgetType.STD_LABEL)

my_custom_widget.setStyleSheet(f"""
    QLabel {{
        color: {text_color};
        font-size: {font_size}px;
    }}
""")
```

#### 常數

| 常數 | 值 | 說明 |
|------|-----|------|
| `theme.SIDEBAR_MAX_WIDTH` | `341` | 側面板最大寬度（px） |

---

## 2.7 UI 與 Config 最佳實踐 (UX Best Practices)

本節描述兩項外掛開發中最容易踩坑的實戰場景，並給出強制性的最佳實踐規範。

---

### 規範 1：欄位選單的列舉防呆公式

#### 問題背景

外掛從設定檔還原了上一次的欄位選擇（例如使用者上次選擇了第 6 欄，`stored_col = 5`），但本次載入的 CSV 只有 3 欄。若 `on_csv_data_refreshed` 中直接以 `csv_data.num_cols` 為上限建立選單，選單只會有 3 個項目，導致還原後的 index 5 超出範圍，程式將靜默回退到 index 0，使用者設定遺失，且不會有任何錯誤提示。

#### 解決方案：安全上限計算公式

填充欄位選單前，**必須**使用以下公式計算選單的安全上限，確保選單至少能容納 Config 中所有已儲存的欄位索引：

```python
# 安全上限公式（假設外掛使用兩個欄位選擇器 col_a 與 col_b）
# self.config 在此泛指已從設定檔讀取的欄位索引值（stored value，非 UI index）
limit = max(
    csv_data.num_cols,
    self.config_col_a + 1,   # stored value + 1 = 至少需要的欄位數
    self.config_col_b + 1,
)
```

> **公式說明**：
> - `csv_data.num_cols`：資料實際具備的欄位數，作為基準下限。
> - `stored_col_X + 1`：Config 中已儲存的索引所需的最少欄位數。加 1 是因為索引從 0 起算（索引 5 代表至少需要 6 欄）。
> - `max(...)` 確保選單長度取三者最大值，使 Config 的還原在任何情況下都不會 out-of-range。

#### 完整實作範例

```python
def on_csv_data_refreshed(self) -> None:
    """CSV 資料載入或標頭變更時，安全填充欄位選單。"""
    if not self.context or not self.context.is_data_loaded:
        return

    csv_data = self.context.csv_data

    # 【防呆公式】計算選單安全上限
    # _config_col_a / _config_col_b 為從 _internal_deserialize_config 讀入的 stored value
    limit = max(
        csv_data.num_cols,
        self._config_col_a + 1,
        self._config_col_b + 1,
    )

    self.combo_col_a.blockSignals(True)
    self.combo_col_b.blockSignals(True)
    try:
        self.combo_col_a.clear()
        self.combo_col_b.clear()
        for i in range(limit):
            # 即使 i >= csv_data.num_cols（超出實際欄位範圍），
            # get_column_header 仍會回傳合理的佔位標題，不會拋出例外
            header = csv_data.get_column_header(i)
            self.combo_col_a.addItem(header)
            self.combo_col_b.addItem(header)

        # 重新選取原本設定的值 (因 limit 公式已履約保證，此處直接 set 即可)
        ui_index_a = self._stored_to_ui(self._config_col_a)
        self.combo_col_a.setCurrentIndex(ui_index_a)

        ui_index_b = self._stored_to_ui(self._config_col_b)
        self.combo_col_b.setCurrentIndex(ui_index_b)
    finally:
        self.combo_col_a.blockSignals(False)
        self.combo_col_b.blockSignals(False)
```

> **極度重要**：在 `clear()` 並重新 `addItem` 後，選單的 index 會被重置。必須在解除 `blockSignals` 前，將 Config 中紀錄的值手動 restore 回 `setCurrentIndex`，否則切換資料時使用者的設定會遺失。
>
> **注意**：即使索引 `i` 超出資料實際欄位數，`get_column_header(i)` 仍會回傳合理的佔位標題（如 `欄位 6`），不會引發例外。**嚴禁**自行拼接格式字串替代此方法。

---

### 規範 2：Config 有效性驗證時機

#### 最佳實踐：平常不做動態啟停

開發者常犯的錯誤是在 `on_csv_data_refreshed` 或每次 UI 元件狀態改變時，就去檢查目前的 Config 值是否合理（例如「兩個欄位不能相同」），並動態啟用或禁用按鈕。

**這種做法應避免**，原因如下：

| 問題 | 說明 |
|------|------|
| 操作流暢度下降 | 使用者在填寫參數的過程中，按鈕可能頻繁閃爍啟停，體驗差 |
| 信號串接複雜 | 需要為每個 UI 元件連接驗證槽函數，維護成本高，且 blockSignals 防呆更加困難 |
| 驗證結果難以呈現 | 僅靠按鈕啟停，使用者無法得知失敗原因 |

#### 嚴格規範：驗證僅在「開始執行前」進行

**唯一合法的驗證時機**是使用者點擊「開始執行」按鈕的槽函數最開頭。若驗證失敗，透過 `self.api.write_log` 或 `self.api.update_status` 提示原因後直接 `return`，**不呼叫 `start_task()`**。

```python
def _on_btn_clicked(self):
    """點擊「開始執行」的槽函數——唯一合法的 Config 驗證位置。"""

    # ── 1. 執行前驗證（在 start_task 之前，失敗即 return）────────────────
    # 由於有即時同步機制，此處直接讀取內部已同步的 Config 變數
    col_a = self._config_col_a
    col_b = self._config_col_b

    if col_a == col_b:
        self.api.write_log("WARNING", "來源欄位與目標欄位不可相同，請重新選擇。")
        self.api.update_status("❌ 參數錯誤：欄位不可相同")
        return  # 驗證失敗，不啟動任務

    if col_a < 0 or col_a >= self.context.csv_data.num_cols:
        self.api.write_log("WARNING", f"來源欄位索引 {col_a} 超出資料範圍（共 {self.context.csv_data.num_cols} 欄）。")
        self.api.update_status("❌ 參數錯誤：欄位索引超出範圍")
        return

    # ── 2. 驗證通過，正式啟動任務 ──────────────────────────────────────────
    self._worker = _MyWorker()
    self.api.run_worker(
        self._worker,
        task_name="我的外掛任務",
        total=self.context.csv_data.num_cols,
        initial_log=f"任務開始：來源欄 {col_a}，目標欄 {col_b}"
    )
```

> **⚠️ 關鍵規則**：`start_task()` 之前的驗證失敗 `return` **不需要**呼叫 `finish_task()`，
> 因為任務根本尚未啟動，主程式的任務狀態未被改變。

---

### 規範 3：Config 的即時同步鐵律

#### 核心精神

Config（不論是內部變數或獨立類別）是外掛狀態的「唯一真理（Single Source of Truth）」。UI 只是視圖。

#### 實作規定

任何 UI 元件的異動（如 `currentIndexChanged`、`textChanged`、`valueChanged`），都**必須**綁定槽函數，即時將值寫入 Config 中。

#### 程式碼範例

```python
# 1. 綁定信號
self.combo_col.currentIndexChanged.connect(self._on_combo_changed)

# 2. 即時同步槽函數
def _on_combo_changed(self, ui_index: int) -> None:
    # 轉換為 stored value 並即時更新 internal config
    self._config_selected_col = self._ui_to_stored(ui_index)
```

#### 強調說明

因為有了即時同步，`on_csv_data_refreshed` 就可以絕對信任並直接讀取 Config 變數來計算 `limit`，而不需要去反查 UI 當下的狀態。

---

## 2.8 UI 佈局與圖示設計規範 (Layout & Icon Design)

---

### 規範 1：面板寬度與捲動限制

#### 寬度上限

側邊面板的最大寬度受限於常數 `theme.SIDEBAR_MAX_WIDTH = 341`（px）。所有外掛 UI 元件的總水平寬度**不得超過此值**，否則將被主程式框架截斷，或在不同系統字型下發生溢出。

#### 佈局最佳實踐

| 建議 | 說明 |
|------|------|
| **優先 `QVBoxLayout`** | 垂直堆疊元件，天然收束為固定寬度，是外掛面板最適合的主佈局 |
| **多欄考慮 `QGridLayout`** | 若需要兩欄對齊（如 Label + Input），改用 `QGridLayout` 以精確控制欄寬比例 |
| **預留垂直捲動空間** | 元件較多時，建議將 `controls_layout` 內的內容包裹在 `QScrollArea` 中，確保在小解析度螢幕上不截斷元件 |
| **極力避免水平捲動** | 水平捲動在側邊面板中使用體驗極差，任何情況下皆不應發生 |

#### `QScrollArea` 包裹範例

```python
from PyQt6.QtWidgets import QScrollArea, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

def _setup_ui(self):
    # 建立可捲動容器
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 關閉水平捲動
    
    # 【UI 防呆】：必須消除 QScrollArea 預設的邊框與背景色，否則會出現突兀的色塊
    scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
    scroll.viewport().setStyleSheet("background: transparent;")

    inner = QWidget()
    inner_layout = QVBoxLayout(inner)
    inner_layout.setContentsMargins(0, 0, 0, 0)

    # 將所有 UI 元件加入 inner_layout
    self.lbl_desc = QLabel("說明文字")
    theme.applyStandardLabelStyle(self.lbl_desc)
    inner_layout.addWidget(self.lbl_desc)
    # ... 其他元件 ...
    inner_layout.addStretch()

    scroll.setWidget(inner)

    # 最後將 scroll 加入面板的 controls_layout
    self.controls_layout.addWidget(scroll)
```

> **注意**：`ScrollBarAlwaysOff` 僅關閉水平捲軸顯示，不影響垂直捲動的正常使用。

---

### 規範 2：外掛圖示 (Icon) 的自動生成機制

#### 預設行為

若開發者**不覆寫** `_internal_get_icon()` 方法，基底類別 `BasePluginPanel` 會自動執行以下邏輯：

1. 呼叫 `_internal_get_package_name()` 取得外掛識別名稱（如 `"my_plugin"`）
2. 擷取前兩個字元（如 `"my"`）
3. 動態繪製成一個**白色文字、透明背景、無邊框**的極簡圖示，顯示於主程式活動列（Activity Bar）

```
_internal_get_package_name() → "my_plugin"
                                    ↓
              擷取前兩字元 → "my"
                                    ↓
         自動繪製極簡圖示 → [my]  （白字，透明底）
```

> **實作說明**：此為全自動機制，不需要在外掛目錄中放置任何圖片檔案，無需額外設定。

#### 自訂圖示設計標準 (Custom Icon Guidelines)

為了融入主程式側邊欄，手動提供圖示時強烈建議遵循以下規範：

| 設計要素 | 強制規範與建議 |
|----------|----------------|
| **顏色 (Color)** | 統一使用 **`#a9b1d6`** (主題標準淡藍灰色) 或 **`#FFFFFF`** (純白色)。避免使用鮮豔色彩或漸層（除特殊 Badge 外）。 |
| **風格 (Style)** | 強烈建議採用「**線條風格 (Outline/Stroke)**」，線條粗細保持一致（約 2px）；若為文字或實心圖案，請保持極簡。 |
| **畫布與邊距 (Canvas)** | 必須為正方形 (1:1)，建議最小尺寸 40x40 px。圖形**絕對不可填滿畫布邊緣**，四周需保留約 10%~15% 的透明 Padding，確保視覺重量與內建圖示一致。 |
| **背景 (Background)** | 必須完全透明。 |
| **檔案格式 (Format)** | 建議使用具有透明通道的 `.png`，或向量格式 `.svg`。 |

##### 程式碼實作範例

```python
from PyQt6.QtGui import QIcon
import os

def _internal_get_icon(self) -> QIcon:
    """覆寫預設的圖示生成邏輯，載入自訂圖示。"""
    # 假設圖示檔案放在外掛目錄下的 assets/icon.png
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    return QIcon(icon_path)
```

> **建議**：若沒有品牌識別需求，**直接沿用預設實作即可**，無需覆寫 `_internal_get_icon()`。

---

### 規範 3：主要動作按鈕位置

若無特殊需求（例如：Filter 面板下方需保留空間給動態新增的規則清單），外掛的『主要動作按鈕（如：開始處理）』應放置於面板的最底部。實作上，請在加入主要按鈕【之前】先呼叫 `self.controls_layout.addStretch()`，將上方元件推頂。

---

## 第三部分：進階工具與效能優化

### 3.1 ThrottledProgress — 進度更新限流器

> **注意：新版架構中，主程式在 `run_worker` 內部已自動對 `worker.progress` 套用 `ThrottledProgress(min_interval=0.2)`。外掛開發者通常【不需要】再手動實作進度節流。**

#### 核心原則
在新架構下，**Worker 內部只需直接呼叫 `self.progress.emit(current, total)`，完全不需要去實作、初始化或匯入節流邏輯。主程式會在外部攔截並自動套用節流效果。**

#### 問題背景

背景 Worker 在高頻率迴圈中（例如處理數萬筆資料），若每次迴圈都直接觸發進度信號，將以每秒數千次的頻率觸發 Qt 信號。Qt 主線程會因此被信號處理淹沒，導致 UI 完全凍結、無法響應使用者操作。主程式在底層正是使用 `ThrottledProgress` 進行限流以解決此問題。

#### ThrottledProgress 規格（僅供底層功能開發者參考）

使用 `utils.ThrottledProgress` 對進度信號進行節流，預設**每 0.2 秒最多發送一次**（即每秒最多 5 次），大幅降低主線程負擔。
同時支援 **Trailing Edge (尾端補發)** 機制：當進度更新在節流時間內被過濾時，定時器會自動在間隔到期時補發最後一次的最新進度，確保 UI 最終能收到如 100% 的進度通知。

#### Import

```python
from utils import ThrottledProgress
```

#### 建構函式

```python
ThrottledProgress(signal, parent, min_interval: float = 0.2)
```

| 參數 | 型別 | 說明 |
|------|------|------|
| `signal` | PyQt Signal | 要被節流的 PyQt 信號物件 |
| `parent` | QObject / any | 生命週期綁定的父物件實例（**不可為 `None`**），內部以弱引用保存，供存活檢測防禦使用 |
| `min_interval` | `float` | 兩次發送之間的最小時間間隔（秒），預設 `0.2` |

#### `emit(*args, force=False) -> bool`

嘗試發送信號。

| 參數 | 型別 | 說明 |
|------|------|------|
| `*args` | any | 傳遞給底層信號的參數 |
| `force` | `bool` | 若 `True`，忽略時間限制強制發送並立即取消排程中的補發 |

回傳 `True` 表示本次信號已立即發送；回傳 `False` 表示被節流過濾（但會自動排程在未來進行尾端補發）。

#### `cancel() -> None`

取消任何懸掛的補發定時器。在發送者（如 Panel 或 Worker）即將被銷毀或完成工作時，**必須主動呼叫此方法**以釋放背景定時執行緒與清理快取。

#### 手動用法範例（僅供底層功能開發者參考）

```python
class _MyWorker(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._cancelled = False

    def run(self):
        total = 50000
        for i in range(total):
            if self._cancelled:
                self.finished.emit("cancelled")
                return
            
            # --- 實際業務邏輯 ---
            
            # 直接發送進度即可，主程式會在外部攔截並自動限流
            self.progress.emit(i + 1, total)

        self.finished.emit("finished")
```

> **注意**：`ThrottledProgress` 是純 Python 工具類別，但在初始化時**強制要求傳入有效的 `parent` 參數**（傳入 `None` 將引發 `ValueError` 崩潰）。此外，呼叫端必須在 parent 銷毀或工作結束時主動調用 `cancel()` 釋放定時器。未正確 cancel 將依循 Fail-Fast 原則拋出 C++ 物件銷毀異常，以利開發除錯。

---

## 第四部分：絕對禁止的反模式 (Strict Anti-Patterns)

下列行為在任何情況下都**絕對禁止**。違反這些規則將導致架構邊界被破壞、程式行為不可預期。

---

### ❌ 反模式 1：直接 emit 私有信號

`BasePluginPanel` 上宣告的以 `_` 開頭的信號（如 `_task_started`、`_task_finished`、`_log_emitted` 等）是內部通訊管道，**只有 `PluginAPI` 有授權呼叫**。

```python
# ❌ 絕對禁止
self._task_started.emit("任務名稱", 100, "開始", False)
self._log_emitted.emit("INFO", "訊息")
self._request_lock_ui.emit(True)

# ✅ 正確做法：透過 self.api
self.api.start_task("任務名稱", total=100, initial_log="開始")
self.api.write_log("INFO", "訊息")
```

---

### ❌ 反模式 2：使用 `hasattr` / `getattr` 跨界猜測主程式狀態

不得使用反射機制探測或存取主程式的任何屬性、狀態或方法。外掛應假設主程式的實作對自己完全不透明。

```python
# ❌ 絕對禁止
if hasattr(self.parent(), "is_running"):
    ...
getattr(self.context, "some_host_method")()

# ✅ 正確做法：只透過 self.api 和 self.context 的公開介面互動
```

---

### ❌ 反模式 3：匯入或使用 `PluginHostAdapter`

`PluginHostAdapter` 是主程式專用的橋接器，刻意未在 `plugin_sdk/__init__.py` 中 export。外掛開發者**無法**且**不應**嘗試匯入它。

```python
# ❌ 絕對禁止
from plugin_sdk.host_adapter import PluginHostAdapter

# ✅ 外掛只需要 BasePluginPanel 與 PluginContext
from plugin_sdk import BasePluginPanel, PluginContext
```

---

### ❌ 反模式 4：直接呼叫主程式生命週期方法

外掛不應直接呼叫主程式的任何生命週期方法（例如假設父元件有 `run_main_action()` 或類似方法）。外掛必須透過自己的生命週期鉤子（如 `on_csv_data_refreshed`）自動觸發。

```python
# ❌ 絕對禁止
self.parent().run_main_action()

# ✅ 正確做法：在 on_csv_data_refreshed 中自動回應資料事件
def on_csv_data_refreshed(self) -> None:
    self._refresh_column_list()
```

---

### ❌ 反模式 5：Hardcode QSS 樣式

外掛 UI 的所有樣式必須透過 `plugin_sdk.theme` 提供的函式套用，不得自行 hardcode 任何 QSS 字串或顏色值。

```python
# ❌ 絕對禁止
widget.setStyleSheet("color: #a9b1d6; font-size: 13px;")

# ✅ 正確做法
theme.applyStandardLabelStyle(widget)
```

---

### ❌ 反模式 6：在 Config 操作中省略 `blockSignals`

在 `_internal_deserialize_config` 或 `on_csv_data_refreshed` 中操作 UI 元件（如 `QComboBox.setCurrentIndex`、`QComboBox.clear` 等），若未切斷信號，可能觸發 `currentIndexChanged` 導致主程式將文件錯誤標記為已修改（dirty），或觸發其他副作用。

```python
# ❌ 危險：還原 config 時觸發 dirty 標記
def _internal_deserialize_config(self, data: dict) -> None:
    self.combo_col.setCurrentIndex(data.get("col", 0))  # 會觸發 currentIndexChanged！

# ✅ 正確：使用 try/finally 切斷信號
def _internal_deserialize_config(self, data: dict) -> None:
    self.combo_col.blockSignals(True)
    try:
        self.combo_col.setCurrentIndex(data.get("col", 0))
    finally:
        self.combo_col.blockSignals(False)
```

---

### ❌ 反模式 7：在資料解除載入或重載時清除 Config 狀態

外掛的 Config 狀態在整個生命週期中應保持永續（Persistent）。當使用者關閉 CSV 檔案（觸發 `hide_controls`）或載入新檔案（觸發 `on_csv_data_refreshed`）時，**絕對禁止**將 Config 變數歸零或洗掉 UI 的選擇狀態。

```python
# ❌ 絕對禁止：在資料刷新時重置 Config
def on_csv_data_refreshed(self) -> None:
    self._config_selected_col = 0  # 錯誤！這會抹除使用者的設定
    self.combo_col.clear()         # 若沒有 restore，等於洗掉設定
```

**正確觀念說明**：
基底類別會自動處理 UI 的隱藏與顯示。外掛只需在 `on_csv_data_refreshed` 中，根據「現存的 Config」重新填充並還原 UI 即可，絕對不要主動去 reset 任何狀態。

**生命週期鐵律**：主程式【只會在啟動時】透過 `_internal_deserialize_config` 讀取並還原一次設定。當後續發生載入或重載 CSV 資料（觸發 `on_csv_data_refreshed`）時，外掛的 UI 元件實體與內部 Config 變數皆完好存在。因此，在資料刷新時，【絕對禁止】呼叫完整的 Config 還原方法（如 `deserialize` 或自定義的 `restore_from_config`）來進行 UI 的銷毀與全盤重建。你只需要針對依賴資料的元件（例如：更新下拉選單的欄位名稱），並利用現存的 Config 變數將選取狀態套用回去（如 `setCurrentIndex`）即可。

---

## 附錄：_internal_ 方法快速參考

下列為子類別**必須覆寫**（raise `NotImplementedError`）的方法：

| 方法簽名 | 回傳型別 | 說明 |
|---------|---------|------|
| `_internal_get_uuid(self)` | `str` | 回傳此外掛的唯一 UUID |
| `_internal_get_package_name(self)` | `str` | 回傳設定檔識別名稱 |
| `_internal_serialize_config(self)` | `dict` | 序列化面板設定 |
| `_internal_deserialize_config(self, data: dict)` | `None` | 還原面板設定 |

下列為子類別**應依需求覆寫**的方法（有預設實作）：

| 方法簽名 | 預設行為 | 說明 |
|---------|---------|------|
| `_internal_set_enabled(self, enabled)` | 無操作 | 需自訂鎖定行為時覆寫 |
| `on_csv_data_refreshed(self)` | 無操作 | 需回應資料事件時覆寫 |

> **說明**：使用 `run_worker` 後，主程式自動持有 worker 引用並處理取消邏輯，無需外掛手動覆寫 `_internal_is_task_running` 與 `_internal_cancel_task` 二方法。
> 
> **提醒**：`_internal_get_icon()` 有預設實作（自動依 `_internal_get_package_name()` 產生縮寫圖示），外掛通常**不需要**覆寫此方法。
