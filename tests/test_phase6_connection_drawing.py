"""
test_phase6_connection_drawing.py — Phase 6 Slot 導向連線與 Expression 動態重構單元測試
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF

# 將專案根目錄與 src 加入 sys.path 以利測試載入
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from filter.logic_tree_editor_dialog import LogicTreeEditorDialog


def test_phase6_connection_drawing():
    app = QApplication.instance() or QApplication(sys.argv)

    # 1. 初始化邏輯樹運算式: "(#1 AND #2) OR #3"
    expr = "(#1 AND #2) OR #3"
    dialog = LogicTreeEditorDialog(expression_text=expr)

    # 驗證初始合法狀態下的連線數量 (應包含 4 條連線: AND-Rule1, AND-Rule2, OR-AND, OR-Rule3)
    assert len(dialog._line_items) == 4, f"Expected 4 lines, got {len(dialog._line_items)}"
    assert dialog.txt_expression.toPlainText() == "(#1 AND #2) OR #3"

    # 驗證連線到 Slot 底部的 X 座標為 [0.0, 110.0, 220.0]
    slot_line_xs = sorted([l.line().p2().x() for l in dialog._line_items if l.line().p2().y() == 300])
    assert slot_line_xs == [0.0, 110.0, 220.0], f"Expected slot X coords [0, 110, 220], got {slot_line_xs}"

    # 取得 LogicNodeItems
    root_op = dialog._node_to_item[dialog._tree_root]  # OR 節點
    rule3_item = dialog._initial_rule_items[2]  # #3 節點

    original_root_y = root_op.y()

    # 2. 測試 Y 軸高度違規斷線
    root_op.setPos(root_op.x(), rule3_item.y() + 10)
    dialog._validate_geometry()
    assert len(dialog._line_items) == 2, f"Expected 2 lines after height inversion, got {len(dialog._line_items)}"

    # 還原 Root 高度
    root_op.setPos(root_op.x(), original_root_y)
    dialog._validate_geometry()
    assert len(dialog._line_items) == 4

    # 3. 測試 Slot-bound 模型下的卡片拖曳與 Expression 動態重構 (Slot 2 卡片拖曳至 Slot 0)
    dialog._start_drag(rule3_item, QPointF(0, rule3_item.y()))
    dialog._pending_slot_idx = 0
    dialog._on_hover_timeout()

    # 拖曳預覽期間：
    # - 畫面連線仍 100% 樹狀直連保持 4 條 (連線終點完全固定在 Slot 0, 1, 2)
    assert len(dialog._line_items) == 4, f"Expected 4 lines during Slot drag preview, got {len(dialog._line_items)}"
    slot_line_xs_during_drag = sorted([l.line().p2().x() for l in dialog._line_items if l.line().p2().y() == 300])
    assert slot_line_xs_during_drag == [0.0, 110.0, 220.0], f"Expected [0, 110, 220], got {slot_line_xs_during_drag}"

    # - 頂部文字即時自動重構為 "(#3 AND #1) OR #2"
    assert dialog.txt_expression.toPlainText() == "(#3 AND #1) OR #2", f"Got: {dialog.txt_expression.toPlainText()}"

    # 4. 測試取消拖曳 (Cancel drag)
    dialog._cancel_drag()
    # 取消拖曳後：
    # - 連線保持 4 條，終點固定在 Slot 0, 1, 2
    assert len(dialog._line_items) == 4
    slot_line_xs_after_cancel = sorted([l.line().p2().x() for l in dialog._line_items if l.line().p2().y() == 300])
    assert slot_line_xs_after_cancel == [0.0, 110.0, 220.0]
    # - 頂部文字自動還原為原本的 "(#1 AND #2) OR #3"
    assert dialog.txt_expression.toPlainText() == "(#1 AND #2) OR #3", f"Got: {dialog.txt_expression.toPlainText()}"

    print("All Phase 6 Slot-bound Connection & Expression Reconstruction tests passed successfully!")


if __name__ == "__main__":
    test_phase6_connection_drawing()
