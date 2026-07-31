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
        """
        扁平化基底方法（空操作）。
        舊設計曾在此合併多叉節點，但該路徑已廢棄（見 add_rule_node）。
        現行系統嚴格維持二元樹不變量，本方法僅保留以維持介面相容性。
        """
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

    # flatten() 方法已移除。
    # 舊設計以此遞迴扁平化多叉節點，但 LogicOpNode 現已嚴格維持二元樹不變量，
    # 不再需要合併操作。繼承自 BaseNode.flatten()（空操作）。

    def __repr__(self):
        return f"<LogicOpNode op_type={self.op_type} children_count={len(self.children)}>"
