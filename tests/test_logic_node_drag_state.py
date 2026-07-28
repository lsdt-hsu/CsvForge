"""
test_logic_node_drag_state.py — 驗證拖曳 LogicNodeItem 過程中視覺狀態 (STATE_DRAGGING, STATE_DISPLACED) 之變更
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

from filter.logic_tree_editor_dialog import LogicTreeEditorDialog
from filter.logic_node_item import LogicNodeItem


def test_logic_node_drag_state():
    app = QApplication.instance() or QApplication(sys.argv)

    # 1. 初始化包含三個邏輯運算子的運算式: "(#1 AND #2) OR (#3 XOR #4)"
    expr = "(#1 AND #2) OR (#3 XOR #4)"
    dialog = LogicTreeEditorDialog(expression_text=expr)

    # 取得 LogicNodeItems
    logic_items = list(dialog._initial_logic_items)
    assert len(logic_items) == 3, f"Expected 3 logic items, got {len(logic_items)}"

    dragged_item = logic_items[0]  # 開始拖曳第一個 logic item

    # 2. 測試拖曳開始：應設定狀態為 STATE_DRAGGING
    dialog._start_drag_logic(dragged_item, QPointF(dragged_item.x(), dragged_item.y()))
    assert dialog._is_dragging_logic is True
    assert dragged_item.visual_state == LogicNodeItem.STATE_DRAGGING

    # 3. 測試 Hover 超時位移：將 dragged_item 位移至最高層級
    dialog._pending_logic_layer_idx = 2
    dialog._on_logic_hover_timeout()

    # 驗證 dragged_item 保持 STATE_DRAGGING 狀態
    assert dragged_item.visual_state == LogicNodeItem.STATE_DRAGGING, (
        f"Expected STATE_DRAGGING, got {dragged_item.visual_state}"
    )

    # 驗證受到位置挪移 (displaced) 的其他 logic item 變更為 STATE_DISPLACED
    displaced_items = [
        it for it in logic_items
        if it != dragged_item and dialog._current_logic_layer_order.index(it) != dialog._drag_start_logic_layer_map.get(it)
    ]
    assert len(displaced_items) > 0, "Expected at least one displaced logic item"
    for displaced_item in displaced_items:
        assert displaced_item.visual_state == LogicNodeItem.STATE_DISPLACED, (
            f"Expected STATE_DISPLACED, got {displaced_item.visual_state}"
        )

    # 4. 測試取消拖曳 (Cancel Drag)：所有狀態還原為 STATE_NORMAL (或合法/非法狀態)
    dialog._cancel_logic_drag()
    assert dialog._is_dragging_logic is False
    for item in logic_items:
        assert item.visual_state in (LogicNodeItem.STATE_NORMAL, LogicNodeItem.STATE_INVALID)

    print("All LogicNodeItem Drag State tests passed successfully!")


if __name__ == "__main__":
    test_logic_node_drag_state()
