"""
test_phase5_geometry_validator.py — Phase 5 幾何合法性檢查模組單元測試 (Slot-bound Model)
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
from filter.logic_node_item import LogicNodeItem
from filter.rule_node_item import RuleNodeItem


def test_phase5_geometry_validator():
    app = QApplication.instance() or QApplication(sys.argv)

    # 1. 初始化邏輯樹運算式: "(#1 AND #2) OR #3"
    expr = "(#1 AND #2) OR #3"
    dialog = LogicTreeEditorDialog(expression_text=expr)

    # 驗證初始佈局為合法狀態
    assert dialog.btn_confirm.text() == "確認"
    for item in dialog._initial_logic_items:
        assert item.visual_state == LogicNodeItem.STATE_NORMAL

    # 2. 測試 Y 軸高度違規: 將 Root 邏輯節點 Y 軸拉低至等於或低於其子節點
    # 取得 LogicNodeItems
    root_op = dialog._node_to_item[dialog._tree_root]  # OR 節點
    child_op = dialog._node_to_item[dialog._tree_root.children[0]]  # AND 節點

    # 將 root 節點設至低於 child 節點 (QGraphicsScene 中 Y 越大越低)
    root_op.setPos(root_op.x(), child_op.y() + 10)
    dialog._validate_geometry()

    assert root_op.visual_state == LogicNodeItem.STATE_INVALID
    assert dialog.btn_confirm.text() == "快速修正"

    # 測試「快速修正」按鈕點擊事件
    dialog._on_confirm_clicked()
    assert dialog.btn_confirm.text() == "確認"

    # 還原高度
    root_op.setPos(root_op.x(), child_op.y() - 80)
    dialog._validate_geometry()
    assert root_op.visual_state == LogicNodeItem.STATE_NORMAL
    assert dialog.btn_confirm.text() == "確認"

    # 3. 測試 Slot-bound 模型下卡片拖曳對調: 幾何永遠保持合法，表達式動態重構
    rule3_item = dialog._initial_rule_items[2]  # #3
    dialog._start_drag(rule3_item, QPointF(0, rule3_item.y()))
    dialog._pending_slot_idx = 0
    dialog._on_hover_timeout()

    # Slot-bound 模式下，幾何連線永遠合法 (STATE_NORMAL)，且文字更新為 "(#3 AND #1) OR #2"
    assert root_op.visual_state == LogicNodeItem.STATE_NORMAL
    assert dialog.txt_expression.toPlainText() == "(#3 AND #1) OR #2"

    # 還原拖曳
    dialog._cancel_drag()
    assert dialog.txt_expression.toPlainText() == "(#1 AND #2) OR #3"

    print("All Phase 5 Geometry Validator tests passed successfully!")


if __name__ == "__main__":
    test_phase5_geometry_validator()
