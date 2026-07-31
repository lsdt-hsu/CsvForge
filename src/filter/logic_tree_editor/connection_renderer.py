"""
connection_renderer.py — 邏輯樹 Slot-bound 連線渲染器模組
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGraphicsLineItem
from PyQt6.QtGui import QPen, QColor

try:
    from filter.logic_tree.logic_node import RuleNode
    from filter.logic_tree_editor.logic_node_item import LogicNodeItem
except ImportError:
    from logic_node import RuleNode
    from logic_node_item import LogicNodeItem


class TreeConnectionRenderer:
    """
    負責更新 LogicNodeItem 視覺狀態，以及渲染與管理 Slot-bound Model 的 QGraphicsLineItem。
    """

    @staticmethod
    def refresh_display(dialog):
        """
        更新 Logic 節點視覺狀態（DRAGGING / DISPLACED / NORMAL）並重新繪製所有連接線。

        [注意] 此函式不執行幾何合法性檢查，原因如下（詳見 geometry_invalidity_analysis.md）：
          - Y 高度檢查：rebuild_tree_from_heights 的 min-Y 選根演算法（設計不可變）保證
            parent.y() 恆小於 child.y()，幾何合法性在數學上永遠通過，無需執行時期檢查。
          - 子樹交叉檢查：Logic 節點 X 為相鄰葉節點的精確中點（設計不可變），數學上不可能
            發生子樹交叉，無需執行時期檢查。
        因此「快速修正」按鈕及相關的 scan_node 掃描邏輯均已移除。
        """
        initial_logics = getattr(dialog, "_initial_logic_items", [])
        is_dragging_logic = getattr(dialog, "_is_dragging_logic", False)
        dragged_logic_item = getattr(dialog, "_dragged_logic_item", None)
        drag_start_layer_map = getattr(dialog, "_drag_start_logic_layer_map", {})
        current_layer_order = getattr(dialog, "_current_logic_layer_order", [])

        for item in initial_logics:
            if is_dragging_logic and item == dragged_logic_item:
                item.set_visual_state(LogicNodeItem.STATE_DRAGGING)
            elif (
                is_dragging_logic
                and item in drag_start_layer_map
                and item in current_layer_order
                and current_layer_order.index(item) != drag_start_layer_map.get(item)
            ):
                item.set_visual_state(LogicNodeItem.STATE_DISPLACED)
            else:
                item.set_visual_state(LogicNodeItem.STATE_NORMAL)

        TreeConnectionRenderer.update_connection_lines(dialog)

    @staticmethod
    def update_connection_lines(dialog):
        """
        即時重新計算並繪製所有節點間的連接線 (Slot-bound Model)。
        採 Post-Order（由下往上）遞迴繪製。
        """
        tree_root = getattr(dialog, "_tree_root", None)
        node_to_item = getattr(dialog, "_node_to_item", None)

        if not tree_root or not node_to_item:
            return

        # 1. 清理現有連線
        existing_lines = getattr(dialog, "_line_items", [])
        for line_item in existing_lines:
            if line_item.scene() == dialog.graphics_scene:
                dialog.graphics_scene.removeItem(line_item)
        dialog._line_items = []

        line_pen = QPen(QColor("#565f89"), 2.0)
        line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        # 2. 建立 AST Leaf 節點與當前 Slot Item 之對應
        ast_leaves = []

        def collect_leaves(node):
            if isinstance(node, RuleNode) or getattr(node, "op_type", None) == "LEAF":
                ast_leaves.append(node)
            elif hasattr(node, "children"):
                for child in node.children:
                    collect_leaves(child)

        collect_leaves(tree_root)

        slot_item_map = {}
        current_slots = getattr(dialog, "_current_slot_order", [])
        for i, leaf in enumerate(ast_leaves):
            if i < len(current_slots):
                slot_item_map[leaf] = current_slots[i]

        def get_item_for_node(node):
            if isinstance(node, RuleNode) or getattr(node, "op_type", None) == "LEAF":
                return slot_item_map.get(node)
            return node_to_item.get(node)

        def process_node_connections(node):
            if isinstance(node, RuleNode) or getattr(node, "op_type", None) == "LEAF":
                return

            if hasattr(node, "children"):
                for child in node.children:
                    process_node_connections(child)

            parent_item = get_item_for_node(node)
            if not parent_item:
                return

            if hasattr(node, "children"):
                for child in node.children:
                    child_item = get_item_for_node(child)
                    if not child_item:
                        continue

                    line = QGraphicsLineItem(
                        parent_item.x(), parent_item.y(),
                        child_item.x(), child_item.y()
                    )
                    line.setPen(line_pen)
                    line.setZValue(-1)
                    dialog.graphics_scene.addItem(line)
                    dialog._line_items.append(line)

        process_node_connections(tree_root)
