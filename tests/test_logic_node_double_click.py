"""
test_logic_node_double_click.py — LogicNodeItem 雙擊與運算子切換對話框單元測試
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from filter.logic_tree_editor_dialog import LogicTreeEditorDialog, LogicOpSelectionDialog
from filter.logic_node_item import LogicNodeItem


def test_logic_op_selection_dialog():
    app = QApplication.instance() or QApplication(sys.argv)

    # 1. 測試預設為 AND 時的 Radio Button 狀態
    dlg_and = LogicOpSelectionDialog(current_op="AND")
    assert dlg_and.rad_and.isChecked()
    assert dlg_and.get_selected_op() == "AND"

    # 2. 測試選擇 OR
    dlg_or = LogicOpSelectionDialog(current_op="OR")
    assert dlg_or.rad_or.isChecked()
    dlg_or.rad_xor.setChecked(True)
    dlg_or._on_confirm()
    assert dlg_or.get_selected_op() == "XOR"

    # 3. 測試選擇 XOR
    dlg_xor = LogicOpSelectionDialog(current_op="XOR")
    assert dlg_xor.rad_xor.isChecked()


def test_logic_node_operator_change_and_expression_update():
    app = QApplication.instance() or QApplication(sys.argv)

    # 1. 初始化邏輯樹: "(#1 AND #2) OR #3"
    expr = "(#1 AND #2) OR #3"
    dialog = LogicTreeEditorDialog(expression_text=expr)
    assert dialog.get_expression_text() == "(#1 AND #2) OR #3"

    logic_items_by_x = sorted(dialog._initial_logic_items, key=lambda it: it.x())
    and_item = logic_items_by_x[0]  # AND 節點
    or_item = logic_items_by_x[1]   # OR 節點

    assert and_item.op_type == "AND"
    assert or_item.op_type == "OR"

    # 2. 將 AND 變更為 XOR
    and_item.set_op_type("XOR")
    assert and_item.op_type == "XOR"

    # 觸發運算樹重構與運算式更新
    dialog._rebuild_tree_from_heights()
    dialog.txt_expression.setPlainText(dialog.get_expression_text())
    dialog._sync_ast_and_update_expression()
    dialog._validate_geometry()

    assert dialog.get_expression_text() == "(#1 XOR #2) OR #3"

    # 3. 再將 OR 變更為 AND
    or_item.set_op_type("AND")
    assert or_item.op_type == "AND"

    dialog._rebuild_tree_from_heights()
    dialog.txt_expression.setPlainText(dialog.get_expression_text())
    dialog._sync_ast_and_update_expression()
    dialog._validate_geometry()

    assert dialog.get_expression_text() == "(#1 XOR #2) AND #3"

    print("All Logic Node Double Click & Op Change tests passed successfully!")


if __name__ == "__main__":
    test_logic_op_selection_dialog()
    test_logic_node_operator_change_and_expression_update()
