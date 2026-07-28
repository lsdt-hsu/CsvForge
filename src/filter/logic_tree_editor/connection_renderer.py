"""
connection_renderer.py — 邏輯樹拓撲幾何檢查與 Slot-bound 連線渲染器模組
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
    負責 Post-Order 掃描邏輯樹拓撲結構、檢查 Y 軸高度幾何合法性、
    更新 LogicNodeItem 視覺狀態，以及渲染與管理 Slot-bound Model 的 QGraphicsLineItem。
    """

    @staticmethod
    def validate_geometry(dialog):
        """
        幾何合法性檢查器 (Geometry Validator)。
        由底層向上 (Post-Order) 掃描邏輯樹拓撲結構與 QGraphicsItem 幾何位置。
        - 檢查條件 1：父邏輯節點 Y 軸高度等於或低於子節點 Height (parent.y() >= child.y())
        """
        tree_root = getattr(dialog, "_tree_root", None)
        node_to_item = getattr(dialog, "_node_to_item", None)

        if not tree_root or not node_to_item:
            return

        invalid_nodes = set()

        # 建立 AST Leaf 節點與當前 Slot Item 之對應 (第 i 個 Leaf -> Slot i 上的 Item)
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

        def scan_node(node):
            if isinstance(node, RuleNode) or getattr(node, "op_type", None) == "LEAF":
                return

            if hasattr(node, "children"):
                for child in node.children:
                    scan_node(child)

            parent_item = node_to_item.get(node)
            if not parent_item:
                return

            if hasattr(node, "children"):
                for child in node.children:
                    child_item = get_item_for_node(child)
                    if child_item and parent_item.y() >= child_item.y():
                        invalid_nodes.add(node)
                        break

        scan_node(tree_root)

        # 更新 LogicNodeItem 視覺狀態
        initial_logics = getattr(dialog, "_initial_logic_items", [])
        is_dragging_logic = getattr(dialog, "_is_dragging_logic", False)
        dragged_logic_item = getattr(dialog, "_dragged_logic_item", None)
        drag_start_layer_map = getattr(dialog, "_drag_start_logic_layer_map", {})
        current_layer_order = getattr(dialog, "_current_logic_layer_order", [])

        for item in initial_logics:
            node = next((n for n, it in node_to_item.items() if it == item), None)
            if is_dragging_logic and item == dragged_logic_item:
                item.set_visual_state(LogicNodeItem.STATE_DRAGGING)
            elif (
                is_dragging_logic
                and item in drag_start_layer_map
                and item in current_layer_order
                and current_layer_order.index(item) != drag_start_layer_map.get(item)
            ):
                item.set_visual_state(LogicNodeItem.STATE_DISPLACED)
            elif node and node in invalid_nodes:
                item.set_visual_state(LogicNodeItem.STATE_INVALID)
            else:
                item.set_visual_state(LogicNodeItem.STATE_NORMAL)

        # 依據檢查結果切換按鈕文字
        if hasattr(dialog, "btn_confirm"):
            if invalid_nodes:
                dialog.btn_confirm.setText("快速修正")
            else:
                dialog.btn_confirm.setText("確認")

        # 重新計算並繪製動態連線 (Slot-bound 連線)
        TreeConnectionRenderer.update_connection_lines(dialog)

    @staticmethod
    def update_connection_lines(dialog):
        """
        即時重新計算並繪製所有節點間的連接線 (Slot-bound Model)。
        - 採 Post-Order (由下往上) 遞迴檢查與繪製。
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

                    # 高度檢查：若父節點 Y >= 子節點 Y，則不繪製
                    if parent_item.y() >= child_item.y():
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
