"""
test_logic_node_horizontal_positioning.py — 驗證 LogicNodeItem 水平座標基於相鄰 RuleNodeItem 中點之單元測試
"""

import sys
import os
from PyQt6.QtWidgets import QApplication

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from filter.logic_tree_editor_dialog import LogicTreeEditorDialog


def test_logic_node_horizontal_positioning():
    app = QApplication.instance() or QApplication(sys.argv)

    # 1. 測試非對稱樹: "(#1 AND #2) OR #3"
    expr1 = "(#1 AND #2) OR #3"
    dialog1 = LogicTreeEditorDialog(expression_text=expr1)

    # 取得 LogicNodeItems 並排序 (依 x 座標)
    logic_items1 = sorted(dialog1._initial_logic_items, key=lambda it: it.x())
    assert len(logic_items1) == 2, f"Expected 2 logic items, got {len(logic_items1)}"

    and_item = logic_items1[0]
    or_item = logic_items1[1]

    # Rule 0 (#1): x = 0.0, Rule 1 (#2): x = 110.0, Rule 2 (#3): x = 220.0
    assert and_item.x() == 55.0, f"Expected AND item x=55.0, got {and_item.x()}"
    assert or_item.x() == 165.0, f"Expected OR item x=165.0, got {or_item.x()}"

    # 2. 測試單向深樹: "((#1 AND #2) AND #3) AND #4"
    expr2 = "((#1 AND #2) AND #3) AND #4"
    dialog2 = LogicTreeEditorDialog(expression_text=expr2)

    logic_items2 = sorted(dialog2._initial_logic_items, key=lambda it: it.x())
    assert len(logic_items2) == 3, f"Expected 3 logic items, got {len(logic_items2)}"

    # 驗證每個 LogicNodeItem 的 x 座標分別為 55.0, 165.0, 275.0 (兩兩 Rule 正中間)
    expected_xs = [55.0, 165.0, 275.0]
    actual_xs = [it.x() for it in logic_items2]
    assert actual_xs == expected_xs, f"Expected logic item xs {expected_xs}, got {actual_xs}"

    print("All LogicNodeItem Horizontal Positioning tests passed successfully!")


if __name__ == "__main__":
    test_logic_node_horizontal_positioning()
