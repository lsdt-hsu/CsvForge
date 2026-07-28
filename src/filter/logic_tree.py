"""
logic_tree.py — 邏輯樹運算式解析、操作與序列化
"""

import re

try:
    from filter.logic_node import BaseNode, RuleNode, LogicOpNode
except ImportError:
    from logic_node import BaseNode, RuleNode, LogicOpNode


class LogicNode(BaseNode):
    """向後相容之 LogicNode 工廠與型別判斷介面"""

    def __new__(cls, op_type, children=None, leaf_idx=None):
        if op_type == "LEAF":
            return RuleNode(leaf_idx=leaf_idx)
        return LogicOpNode(op_type=op_type, children=children)


def to_string(node, parent_op=None):
    """將邏輯樹轉回文字表示，混用不同類型運算時自動加上括號，連續同類型則去括號。"""
    if not node:
        return ""
    if node.op_type == "LEAF" or isinstance(node, RuleNode):
        return f"#{node.leaf_idx}"

    child_strs = [to_string(c, node.op_type) for c in node.children]
    expr = f" {node.op_type} ".join(child_strs)

    # 若 parent_op 存在且與當前類型不同，則強制加上括號
    if parent_op is not None and parent_op != node.op_type:
        return f"({expr})"
    return expr


def find_parent_and_child(node, target_idx, parent=None):
    """在樹中尋找 leaf_idx 為 target_idx 的葉子節點及其 Parent 節點。"""
    if not node:
        return None
    if node.op_type == "LEAF" or isinstance(node, RuleNode):
        if node.leaf_idx == target_idx:
            return (parent, node)
        return None
    for child in node.children:
        res = find_parent_and_child(child, target_idx, node)
        if res is not None:
            return res
    return None


def prune_tree(node):
    """遞迴修剪樹結構，將僅剩單一子節點的運算節點直接提昇。"""
    if not node or node.op_type == "LEAF" or isinstance(node, RuleNode):
        return node

    node.children = [prune_tree(c) for c in node.children]

    new_children = []
    for c in node.children:
        if isinstance(c, LogicOpNode) and c.op_type in ("AND", "OR", "XOR") and len(c.children) == 1:
            new_children.append(c.children[0])
        else:
            new_children.append(c)
    node.children = new_children

    return node


def clean_tree(tree):
    """清理與縮併整棵樹，確保根節點不會為單一子節點。"""
    if not tree:
        return None
    if tree.op_type == "LEAF" or isinstance(tree, RuleNode):
        return tree

    tree = prune_tree(tree)
    while isinstance(tree, LogicOpNode) and tree.op_type in ("AND", "OR", "XOR") and len(tree.children) == 1:
        tree = tree.children[0]
    return tree


def add_rule_node(tree, new_idx):
    """
    新增規則：將新規則 leaf_idx=new_idx 加到前一個規則 (new_idx-1) 所屬的群組中。
    如果前一個規則無 Parent (即原本為單一 Root 節點)，則建立一個 AND 群組包覆兩者。
    """
    new_leaf = RuleNode(leaf_idx=new_idx)
    if not tree:
        return new_leaf

    parent, target_node = find_parent_and_child(tree, new_idx - 1)
    if parent is None:
        # 代表 target_node 就是根節點
        new_root = LogicOpNode("AND", children=[tree, new_leaf])
        return new_root
    else:
        parent.children.append(new_leaf)
        # 進行扁平化維持結構正確
        tree.flatten()
        return tree


def decrement_leafs(node, threshold):
    """將所有 leaf_idx 大於 threshold 的葉子節點序號遞減 1。"""
    if not node:
        return
    if node.op_type == "LEAF" or isinstance(node, RuleNode):
        if node.leaf_idx > threshold:
            node.leaf_idx -= 1
    else:
        for child in node.children:
            decrement_leafs(child, threshold)


def remove_rule_node(tree, del_idx):
    """
    刪除規則：從樹中移除 leaf_idx=del_idx 的葉子節點。
    更新剩餘葉子節點序號，並執行樹的縮併修剪。
    """
    if not tree:
        return None

    parent, target_node = find_parent_and_child(tree, del_idx)
    if parent is None:
        # 刪除了唯一的根節點
        return None

    parent.children.remove(target_node)

    # 清理與縮併樹
    tree = clean_tree(tree)

    # 序號向前遞補
    if tree:
        decrement_leafs(tree, del_idx)

    return tree


# ----------------- Parser -----------------


class Parser:
    """
    邏輯運算式 Parser。
    支援文法優先權：
    - Expr   -> Term { (OR | XOR) Term }
    - Term   -> Factor { AND Factor }
    - Factor -> '(' Expr ')' | '#'<number>
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self):
        t = self.peek()
        self.pos += 1
        return t

    def parse_expr(self):
        node = self.parse_term()
        while self.peek() in ("OR", "XOR"):
            op = self.consume()
            right = self.parse_term()
            node = LogicOpNode(op, children=[node, right])
        return node

    def parse_term(self):
        node = self.parse_factor()
        while self.peek() == "AND":
            op = self.consume()
            right = self.parse_factor()
            node = LogicOpNode(op, children=[node, right])
        return node

    def parse_factor(self):
        t = self.peek()
        if t == "(":
            self.consume()
            node = self.parse_expr()
            if self.consume() != ")":
                raise SyntaxError("括號未閉合")
            return node
        elif t and t.startswith("#"):
            self.consume()
            try:
                idx = int(t[1:])
            except ValueError:
                raise SyntaxError(f"無效的規則序號: {t}")
            return RuleNode(idx)
        else:
            raise SyntaxError(f"語法錯誤，未預期的符號: {t if t else 'EOF'}")


def parse_expression(expr_str: str, current_count: int = None):
    """
    解析運算式字串並做語意檢查。
    傳回解析扁平化後的 LogicNode (BaseNode 樹)。若語法或語意不合法，拋出 ValueError。
    """
    if not expr_str or not expr_str.strip():
        if current_count == 0 or current_count is None:
            return None
        raise ValueError("運算式為空")

    # 詞法分析：擷取括號、AND/OR/XOR 以及 #數字
    tokens = re.findall(r"\(|\)|AND|OR|XOR|#\d+", expr_str, re.IGNORECASE)

    cleaned_tokens = []
    for t in tokens:
        up = t.upper()
        if up in ("AND", "OR", "XOR"):
            cleaned_tokens.append(up)
        else:
            cleaned_tokens.append(t)

    if not cleaned_tokens:
        raise ValueError("運算式無有效 Token")

    parser = Parser(cleaned_tokens)
    try:
        tree = parser.parse_expr()
        if parser.pos < len(cleaned_tokens):
            raise SyntaxError(f"語法錯誤，多餘的符號: {cleaned_tokens[parser.pos]}")
    except SyntaxError as e:
        raise ValueError(f"語法錯誤: {e}")

    # 執行扁平化壓平連續 AND/OR/XOR
    tree.flatten()

    # 語意驗證（若傳入 current_count 且 > 0）
    if current_count is not None and current_count > 0:
        leafs = []

        def collect_leafs(node):
            if node.op_type == "LEAF" or isinstance(node, RuleNode):
                leafs.append(node.leaf_idx)
            else:
                for child in node.children:
                    collect_leafs(child)

        collect_leafs(tree)

        expected = set(range(1, current_count + 1))
        actual = set(leafs)

        if len(leafs) != current_count:
            raise ValueError(
                f"規則數量不匹配：當前有 {current_count} 條規則，但運算式包含 {len(leafs)} 個規則"
            )
        if actual != expected:
            raise ValueError(
                f"規則序號不匹配：運算式必須包含 #{', #'.join(map(str, expected))} 且無重複"
            )

    return tree


# ----------------- Serialization -----------------


def serialize_tree(node):
    if not node:
        return None
    if node.op_type == "LEAF" or isinstance(node, RuleNode):
        return {"type": "LEAF", "idx": node.leaf_idx}
    return {
        "type": node.op_type,
        "children": [serialize_tree(c) for c in node.children],
    }


def deserialize_tree(data):
    if not data:
        return None
    if data.get("type") == "LEAF":
        return RuleNode(leaf_idx=data.get("idx"))
    return LogicOpNode(
        op_type=data.get("type", "AND"),
        children=[deserialize_tree(c) for c in data.get("children", [])],
    )
