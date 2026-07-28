"""
logic_node.py — 邏輯樹資料結構節點類別
定義 BaseNode、RuleNode 與 LogicOpNode，達成資料結構與 GUI 元件解耦。
"""


class BaseNode:
    """邏輯樹節點基底類別"""

    def __init__(self, op_type: str):
        self.op_type = op_type
        self.children = []
        self.leaf_idx = None

    def flatten(self):
        """子類別實作扁平化邏輯"""
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__} op_type={self.op_type}>"


class RuleNode(BaseNode):
    """規則節點 (LEAF)，代表單一規則 (例如 #1, #2, ...)"""

    def __init__(self, leaf_idx: int):
        super().__init__("LEAF")
        self.leaf_idx = leaf_idx
        self.children = []

    def flatten(self):
        pass

    def __repr__(self):
        return f"<RuleNode #{self.leaf_idx}>"


class LogicOpNode(BaseNode):
    """邏輯節點，代表邏輯運算子 (AND, OR, XOR)"""

    def __init__(self, op_type: str, children: list = None):
        super().__init__(op_type.upper())
        self.children = children or []
        self.leaf_idx = None

    def flatten(self):
        """遞迴進行子節點扁平化（維持二元樹結構，每個邏輯運算子限定 2 個運算元）。"""
        for child in self.children:
            child.flatten()

    def __repr__(self):
        return f"<LogicOpNode op_type={self.op_type} children_count={len(self.children)}>"
