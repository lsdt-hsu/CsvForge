"""
test_rule_node_drag_ghost_position.py — 驗證拖曳 RuleNodeItem 時, 幻影 (Ghost) 節點之 Y 軸保持不變, 僅 X 軸移動
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from filter.logic_tree_editor import LogicTreeEditorDialog, RuleNodeItem


class MockSceneEvent:
    def __init__(self, pos: QPointF):
        self._pos = pos

    def scenePos(self) -> QPointF:
        return self._pos


def test_rule_node_drag_ghost_position():
    app = QApplication.instance() or QApplication(sys.argv)

    # 1. 初始化包含 Rule 節點的邏輯運算式
    expr = "#1 AND #2"
    dialog = LogicTreeEditorDialog(expression_text=expr)

    rule_items = list(dialog._initial_rule_items)
    assert len(rule_items) == 2, f"Expected 2 rule items, got {len(rule_items)}"

    dragged_item = rule_items[0]
    expected_y = dragged_item.y()

    # 2. 測試 start_drag：傳入滑鼠 Y 座標為 500.0 (與 expected_y 不相符)
    mouse_press_pos = QPointF(100.0, 500.0)
    dialog._start_drag(dragged_item, mouse_press_pos)

    assert dialog._is_dragging is True
    assert dialog._ghost_item is not None
    assert dialog._ghost_item.x() == 100.0, f"Expected ghost X to be 100.0, got {dialog._ghost_item.x()}"
    assert dialog._ghost_item.y() == expected_y, f"Expected ghost Y to be fixed at {expected_y}, got {dialog._ghost_item.y()}"

    # 3. 測試 mouse_move：模擬滑鼠移動至 (250.0, 600.0)
    mouse_move_event = MockSceneEvent(QPointF(250.0, 600.0))
    handled = dialog.handle_scene_mouse_move(mouse_move_event)

    assert handled is True
    assert dialog._ghost_item.x() == 250.0, f"Expected ghost X to be 250.0, got {dialog._ghost_item.x()}"
    assert dialog._ghost_item.y() == expected_y, f"Expected ghost Y to remain fixed at {expected_y}, got {dialog._ghost_item.y()}"

    # 4. 測試 cancel_drag
    dialog._cancel_drag()
    assert dialog._is_dragging is False
    assert dialog._ghost_item is None

    print("All RuleNodeItem Drag Ghost Position tests passed successfully!")


if __name__ == "__main__":
    test_rule_node_drag_ghost_position()
