"""
filter_config.py — 過濾面板設定與序列化
"""

from dataclasses import dataclass, field

@dataclass
class FilterPanelConfig:
    dirty: bool = False
    rules: list = field(default_factory=list)
    logic_tree: dict = field(default_factory=dict)
    expr_text: str = "#1"
    start_row: str = "1"
    end_row: str = ""

def serialize_filter_config(config: FilterPanelConfig) -> dict:
    """將 FilterPanelConfig 序列化為 dict。"""
    return {
        "rules": config.rules,
        "logic_tree": config.logic_tree,
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
        logic_tree=data.get("logic_tree", {}),
        expr_text=data.get("expr_text", "#1"),
        start_row=data.get("start_row", "1"),
        end_row=data.get("end_row", ""),
    )
