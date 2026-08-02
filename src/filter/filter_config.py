"""
filter_config.py — 過濾面板設定與序列化
"""

from enum import IntEnum
from dataclasses import dataclass, field

class CompareMethod(IntEnum):
    FULL_MATCH = 0  # 全符合
    CONTAINS = 1    # 包含
    BELONG = 2      # 屬於
    REGEX = 3       # 正規表達式

@dataclass
class FilterPanelConfig:
    dirty: bool = False
    rules: list = field(default_factory=list)
    expr_text: str = ""
    start_row: str = "1"
    end_row: str = ""

def serialize_filter_config(config: FilterPanelConfig) -> dict:
    """將 FilterPanelConfig 序列化為 dict。"""
    return {
        "rules": config.rules,
        "expr_text": config.expr_text,
        "start_row": config.start_row,
        "end_row": config.end_row,
    }

def deserialize_filter_config(data: dict) -> FilterPanelConfig:
    """將 dict 反序列化為 FilterPanelConfig 物件。"""
    if not data:
        return FilterPanelConfig()
    return FilterPanelConfig(
        rules=data.get("rules", []),
        expr_text=data.get("expr_text", ""),
        start_row=data.get("start_row", "1"),
        end_row=data.get("end_row", ""),
    )
