"""
settings_manager.py — 設定管理員

職責：
  - 定義所有 Config 資料類別（dataclass），每個帶有 dirty flag。
  - load()：讀取 settings.json，建立 Config 物件字典；若不存在則使用預設值。
  - save()：若所有 Config 的 dirty == False，忽略存檔請求；
            否則序列化「所有」Config 物件（保持設定檔完整性），按固定順序寫入，
            存檔後清除所有 dirty flag。

設計決策：
  各面板直接讀取 / 寫入 Config 物件欄位（資料相依性），
  而非透過 get_config() / set_config() 序列化橋接（程式流程相依性）。
  程式流程相依性在程式流程被修改時（例如新增儲存時機、修改初始化順序），
  若橋接方法的呼叫端未同步更新，容易造成設定丟失或順序錯誤等難以追蹤的 Bug，
  且難以被靜態分析工具偵測。
  資料相依性（直接依賴 Config 類別的欄位定義）更易於靜態分析，
  欄位變更時編輯器能直接提示錯誤位置。
"""

import json
import os
from dataclasses import dataclass, field

from ui_constants import WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT


# ── Config 資料類別 ────────────────────────────────────────────────────────────
# 每個 Config 對應 settings.json 中的一個第一階層物件。
# dirty flag：從設定檔讀入時預設為 False，各模組修改組態時設為 True，存檔後清為 False。
# 序列化時略過 dirty 欄位，不寫入 JSON。

@dataclass
class WindowConfig:
    """
    主視窗組態。
    寫入擁有者：MainWindow（SettingsMixin）。
    """
    dirty: bool = False
    x: int = 100
    y: int = 100
    width: int = WINDOW_DEFAULT_WIDTH
    height: int = WINDOW_DEFAULT_HEIGHT
    is_maximized: bool = False


@dataclass
class MainConfig:
    """
    主程式組態（目前僅記錄最後選擇的功能面板）。
    寫入擁有者：MainWindow（SettingsMixin）。
    """
    dirty: bool = False
    active_tab: str = "filter"


@dataclass
class SidePanelConfig:
    """
    側邊欄組態（折疊狀態）。
    寫入擁有者：MainWindow（SettingsMixin）。
    """
    dirty: bool = False
    collapsed: bool = False

@dataclass
class IoPanelConfig:
    """
    輸入與輸出面板組態（路徑、欄號、折疊狀態）。
    寫入擁有者：MainWindow（SettingsMixin）。
    注意：此組態僅作為 IO Panel 控件的初始預設值來源；
          執行時動態讀取的路徑等值仍透過 AppContext 存取器半直接取得編輯框最新值。
    """
    dirty: bool = False
    source_path: str = ""
    output_path: str = ""
    collapsed: bool = False


@dataclass
class DataEditorConfig:
    """
    資料編輯面板組態。
    寫入擁有者：DataEditorPanel。
    """
    dirty: bool = False
    first_row_header: bool = False


@dataclass
class StatusPanelConfig:
    """
    執行狀態與日誌面板組態。
    寫入擁有者：MainWindow（SettingsMixin）。
    """
    dirty: bool = False
    expanded_height: int = 250
    collapsed: bool = False


@dataclass
class TranslatePanelConfig:
    """
    翻譯面板組態。
    寫入擁有者：TranslationPanel。
    """
    dirty: bool = False
    batch_interval: int = 10
    single_interval: float = 1.0
    batch_size: int = 18
    src_lang: str = "ja"
    tgt_lang: str = "zh-TW"
    src_col: str = "1"
    tgt_col: str = "2"


@dataclass
class FilterPanelConfig:
    """
    編輯過濾面板組態。
    寫入擁有者：EditPanel。
    """
    dirty: bool = False
    rules: list = field(default_factory=list)
    logic_tree: dict = field(default_factory=dict)
    expr_text: str = "#1"
    start_row: str = "1"
    end_row: str = ""


@dataclass
class AiPanelConfig:
    """
    AI 處理面板組態。
    寫入擁有者：AiPanel。
    """
    dirty: bool = False
    ai_service: str = "Google AI"
    google_api_key: str = ""
    google_model: str = "gemini-1.5-flash"
    local_backend: str = "Ollama"
    local_server_url: str = "http://localhost:11434"
    local_model: str = ""
    advanced_num_ctx: int = 4096
    advanced_temperature: float = 0.7
    target_col: str = ""
    prompt_template: str = ""


# ── 固定的序列化鍵值順序 ──────────────────────────────────────────────────────
# 只保留主程式本身的 Config
_CONFIG_KEYS_ORDER = [
    "window",
    "main",
    "side_panel",
    "io_panel",
    "data_editor_panel",
    "status_panel",
]

# 每個 Key 對應的 Config 類別與 JSON 區段 Key 的映射
_CONFIG_CLASSES = {
    "window":            WindowConfig,
    "main":              MainConfig,
    "side_panel":        SidePanelConfig,
    "io_panel":          IoPanelConfig,
    "data_editor_panel": DataEditorConfig,
    "status_panel":      StatusPanelConfig,
}


def _from_dict(cls, data: dict):
    """
    將 JSON dict 的欄位安全地填入 Config dataclass，
    未知欄位忽略，缺少欄位使用預設值，型別轉換失敗時也使用預設值。
    """
    instance = cls()
    for f_name, f_default in instance.__dataclass_fields__.items():
        if f_name == "dirty":
            continue
        if f_name in data:
            try:
                setattr(instance, f_name, data[f_name])
            except Exception:
                pass  # 型別不符時保留預設值
    return instance


def _to_dict(config) -> dict:
    """
    將 Config dataclass 序列化為 dict，略過 dirty 欄位。
    """
    result = {}
    for f_name in config.__dataclass_fields__:
        if f_name == "dirty":
            continue
        result[f_name] = getattr(config, f_name)
    return result


class SettingsManager:
    """
    設定管理員：負責讀取 / 序列化 Config 物件字典與 settings.json 之間的轉換。
    """

    @staticmethod
    def load(filepath: str) -> dict:
        """
        讀取 settings.json，建立並回傳 Config 物件字典。
        若檔案不存在或解析失敗，回傳所有欄位為預設值的 Config 物件。
        """
        raw: dict = {}
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    raw = json.load(f)
            except Exception:
                raw = {}

        configs = {}
        # 1. 載入主程式核心 configs
        for key, cls in _CONFIG_CLASSES.items():
            section = raw.get(key, {})
            configs[key] = _from_dict(cls, section) if section else cls()

        # 2. 將其他非 core 區段以 raw dict 形式保留並傳出
        for key, val in raw.items():
            if key not in _CONFIG_CLASSES:
                configs[key] = val

        return configs

    @staticmethod
    def save(configs: dict, filepath: str) -> bool:
        """
        比對當前與舊有設定檔內容，若有變化則序列化並寫入 settings.json，
        存檔後清除所有 core config 的 dirty flag。
        """
        # 讀取現有 JSON 資料進行比對
        old_data = {}
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
            except Exception:
                old_data = {}

        # 準備即將寫入的資料
        new_data = {}
        
        # 寫入 core configs
        for key in _CONFIG_KEYS_ORDER:
            if key in configs:
                new_data[key] = _to_dict(configs[key])
                
        # 寫入 non-core configs (功能 package 的 configs，格式為 dict)
        for key, val in configs.items():
            if key not in _CONFIG_CLASSES:
                new_data[key] = val

        # 若內容無變化，忽略本次存檔
        if new_data == old_data:
            return False

        # 有變化，寫入檔案
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(new_data, f, indent=4, ensure_ascii=False)
        except Exception:
            return False

        # 存檔成功後，清除 core configs 的 dirty flag
        for cfg in configs.values():
            if hasattr(cfg, "dirty"):
                cfg.dirty = False

        return True

