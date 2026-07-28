"""
layout_engine.py — 邏輯樹幾何佈局計算與 AST 逆向重建引擎
"""

from PyQt6.QtCore import QPointF, Qt
try:
    from filter.logic_tree import logic_tree
    from filter.logic_tree.logic_node import RuleNode, LogicOpNode
    from filter.logic_tree_editor.rule_node_item import RuleNodeItem
    from filter.logic_tree_editor.logic_node_item import LogicNodeItem
except ImportError:
    from filter.logic_tree import logic_tree
    from logic_node import RuleNode, LogicOpNode
    from rule_node_item import RuleNodeItem
    from logic_node_item import LogicNodeItem


class TreeLayoutEngine:
    """
    負責邏輯樹在 QGraphicsScene 上的幾何座標計算、圖形節點構建、
    從節點位置逆向重構 AST Tree，以及拓撲層級修復。
    """

    @staticmethod
    def collect_leaves(node):
        """遞迴蒐集 AST 中所有葉節點 (RuleNode 或 LEAF)。"""
        leaf_nodes = []

        def _collect(n):
            if isinstance(n, RuleNode) or getattr(n, "op_type", None) == "LEAF":
                leaf_nodes.append(n)
            elif hasattr(n, "children"):
                for child in n.children:
                    _collect(child)

        _collect(node)
        return leaf_nodes

    @staticmethod
    def get_rightmost_leaf(n):
        if isinstance(n, RuleNode) or getattr(n, "op_type", None) == "LEAF":
            return n
        return TreeLayoutEngine.get_rightmost_leaf(n.children[-1])

    @staticmethod
    def get_leftmost_leaf(n):
        if isinstance(n, RuleNode) or getattr(n, "op_type", None) == "LEAF":
            return n
        return TreeLayoutEngine.get_leftmost_leaf(n.children[0])

    @staticmethod
    def calculate_node_metrics(tree_root, spacing_x=110.0, base_y=300.0, level_height=80.0):
        """
        計算 AST 中每個節點的深度層級 (level_map) 與 Scene 座標 (pos_map)。
        """
        leaf_nodes = TreeLayoutEngine.collect_leaves(tree_root)
        pos_map = {}
        level_map = {}

        for i, leaf in enumerate(leaf_nodes):
            level_map[leaf] = 0
            pos_map[leaf] = QPointF(i * spacing_x, base_y)

        def _calc_metrics(node):
            if isinstance(node, RuleNode) or getattr(node, "op_type", None) == "LEAF":
                return level_map[node], pos_map[node].x()

            child_levels = []
            for child in node.children:
                c_lvl, _ = _calc_metrics(child)
                child_levels.append(c_lvl)

            node_lvl = 1 + (max(child_levels) if child_levels else 0)

            if len(node.children) >= 2:
                rightmost_left = TreeLayoutEngine.get_rightmost_leaf(node.children[0])
                leftmost_right = TreeLayoutEngine.get_leftmost_leaf(node.children[1])
                node_x = (pos_map[rightmost_left].x() + pos_map[leftmost_right].x()) / 2.0
            elif node.children:
                _, node_x = _calc_metrics(node.children[0])
            else:
                node_x = 0.0

            level_map[node] = node_lvl
            node_y = base_y - node_lvl * level_height
            pos_map[node] = QPointF(node_x, node_y)

            return node_lvl, node_x

        _calc_metrics(tree_root)
        return leaf_nodes, pos_map, level_map

    @staticmethod
    def build_tree_graph(dialog, expression_text: str):
        """
        解析頂部運算式文字，並在 dialog 的 QGraphicsScene 繪製節點與佈局。
        """
        dialog.graphics_scene.clear()
        expr_str = expression_text.strip()
        if not expr_str:
            return None, {}, [], [], [], {}, [], [], [], []

        try:
            tree_root = logic_tree.parse_expression(expr_str)
        except Exception:
            return None, {}, [], [], [], {}, [], [], [], []

        if not tree_root:
            return None, {}, [], [], [], {}, [], [], [], []

        spacing_x = 110.0
        base_y = 300.0
        level_height = 80.0
        dialog._spacing_x = spacing_x
        dialog._base_y = base_y

        leaf_nodes, pos_map, level_map = TreeLayoutEngine.calculate_node_metrics(
            tree_root, spacing_x, base_y, level_height
        )

        node_to_item = {}
        rule_items_by_leaf = {}
        logic_items = []

        def draw_nodes(node):
            pos = pos_map[node]
            if isinstance(node, RuleNode) or getattr(node, "op_type", None) == "LEAF":
                item = RuleNodeItem(node.leaf_idx)
                rule_items_by_leaf[node] = item
            else:
                item = LogicNodeItem(node.op_type)
                logic_items.append(item)

            node_to_item[node] = item
            item.setPos(pos)
            item.setZValue(0)
            dialog.graphics_scene.addItem(item)

            if not (isinstance(node, RuleNode) or getattr(node, "op_type", None) == "LEAF"):
                for child in node.children:
                    draw_nodes(child)

        draw_nodes(tree_root)

        slot_positions = [QPointF(i * spacing_x, base_y) for i in range(len(leaf_nodes))]
        initial_rule_items = [rule_items_by_leaf[leaf] for leaf in leaf_nodes if leaf in rule_items_by_leaf]
        initial_slot_map = {item: i for i, item in enumerate(initial_rule_items)}
        current_slot_order = list(initial_rule_items)

        num_layers = max(0, len(leaf_nodes) - 1)
        layer_positions_y = [base_y - (i + 1) * level_height for i in range(num_layers)]

        logic_items.sort(key=lambda item: (base_y - item.pos().y(), item.pos().x()))
        for i in range(min(num_layers, len(logic_items))):
            logic_items[i].setPos(logic_items[i].x(), layer_positions_y[i])

        initial_logic_items = list(logic_items)
        current_logic_layer_order = list(logic_items)

        boundingRect = dialog.graphics_scene.itemsBoundingRect()
        if not boundingRect.isEmpty():
            padded_rect = boundingRect.adjusted(-60, -60, 60, 60)
            dialog.graphics_scene.setSceneRect(padded_rect)
            dialog.graphics_view.fitInView(padded_rect, Qt.AspectRatioMode.KeepAspectRatio)

        return (
            tree_root,
            node_to_item,
            leaf_nodes,
            slot_positions,
            initial_rule_items,
            initial_slot_map,
            current_slot_order,
            layer_positions_y,
            initial_logic_items,
            current_logic_layer_order,
        )

    @staticmethod
    def rebuild_tree_from_heights(initial_rule_items, current_slot_order, initial_logic_items):
        """
        依照當前 Rule 節點順序與 Logic 節點的高度 (Y 座標)，動態重新建立邏輯樹 (AST)。
        """
        if not initial_rule_items:
            return None, {}

        rule_items = current_slot_order if current_slot_order else initial_rule_items
        if not rule_items:
            return None, {}

        logic_items = sorted(initial_logic_items or [], key=lambda it: it.x())
        num_rules = len(rule_items)

        if num_rules == 1:
            leaf = RuleNode(leaf_idx=rule_items[0].rule_idx)
            return leaf, {leaf: rule_items[0]}

        node_to_item = {}

        def build_subtree(rule_start: int, rule_end: int):
            if rule_start == rule_end:
                leaf = RuleNode(leaf_idx=rule_items[rule_start].rule_idx)
                node_to_item[leaf] = rule_items[rule_start]
                return leaf

            best_op_idx = rule_start
            min_y = logic_items[rule_start].y()

            for op_idx in range(rule_start + 1, rule_end):
                op_y = logic_items[op_idx].y()
                if op_y < min_y:
                    min_y = op_y
                    best_op_idx = op_idx

            op_item = logic_items[best_op_idx]

            left_child = build_subtree(rule_start, best_op_idx)
            right_child = build_subtree(best_op_idx + 1, rule_end)

            parent_node = LogicOpNode(op_type=op_item.op_type, children=[left_child, right_child])
            node_to_item[parent_node] = op_item
            return parent_node

        tree_root = build_subtree(0, num_rules - 1)
        return tree_root, node_to_item

    @staticmethod
    def quick_fix_geometry(tree_root, node_to_item, initial_logic_items, spacing_x=110.0, base_y=300.0, level_height=80.0):
        """
        檢查所有邏輯節點之間的拓撲依賴關係，重新分配它們的高度層級。
        """
        if not tree_root or not node_to_item:
            return []

        leaf_nodes, pos_map, _ = TreeLayoutEngine.calculate_node_metrics(
            tree_root, spacing_x, base_y, level_height
        )

        for node, item in node_to_item.items():
            if isinstance(item, LogicNodeItem) and node in pos_map:
                item.setPos(pos_map[node])
                item.set_visual_state(LogicNodeItem.STATE_NORMAL)

        logic_items = list(initial_logic_items or [])
        logic_items.sort(key=lambda item: (base_y - item.pos().y(), item.pos().x()))
        return logic_items
