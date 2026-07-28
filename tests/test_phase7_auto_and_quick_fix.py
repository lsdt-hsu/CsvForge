"""
test_phase7_auto_and_quick_fix.py — Phase 7 自動修正 (Auto Repair) 與快速修正 (Quick Fix) 演算法單元測試
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

from filter.logic_tree_editor import LogicTreeEditorDialog, LogicNodeItem


def test_phase7_auto_repair_and_quick_fix():
    app = QApplication.instance() or QApplication(sys.argv)

    # 1. 初始化邏輯樹運算式: "(#1 AND #2) OR #3"
    expr = "(#1 AND #2) OR #3"
    dialog = LogicTreeEditorDialog(expression_text=expr)

    # 驗證初始佈局
    assert dialog.txt_expression.toPlainText() == "(#1 AND #2) OR #3"
    assert dialog.btn_confirm.text() == "確認"

    # 取得 LogicNodeItems (AND 與 OR)
    logic_items_by_x = sorted(dialog._initial_logic_items, key=lambda it: it.x())
    and_item = logic_items_by_x[0]  # AND 節點
    or_item = logic_items_by_x[1]   # OR 節點

    assert and_item.op_type == "AND"
    assert or_item.op_type == "OR"
    assert and_item.y() == 220.0  # Layer 0 (內層)
    assert or_item.y() == 140.0   # Layer 1 (外層 Root)

    # ------------------------------------------------------------------
    # 2. 測試「自動修正」(Auto Repair)：將 AND 拉高至 Layer 1 (Y=140)，OR 拉低至 Layer 0 (Y=220)
    # ------------------------------------------------------------------
    and_item.setPos(and_item.x(), 140.0)
    or_item.setPos(or_item.x(), 220.0)

    # 觸發樹重建
    dialog._rebuild_tree_from_heights()
    dialog.txt_expression.setPlainText(dialog.get_expression_text())
    dialog._sync_ast_and_update_expression()
    dialog._validate_geometry()

    # 驗證樹已自動修正為 "#1 AND (#2 OR #3)"
    assert dialog.txt_expression.toPlainText() == "#1 AND (#2 OR #3)", f"Got: {dialog.txt_expression.toPlainText()}"
    assert dialog.btn_confirm.text() == "確認"
    assert and_item.visual_state == LogicNodeItem.STATE_NORMAL
    assert or_item.visual_state == LogicNodeItem.STATE_NORMAL

    # ------------------------------------------------------------------
    # 3. 測試幾何錯位與「快速修正」(Quick Fix)
    # ------------------------------------------------------------------
    # 將 Parent AND 節點硬性拉低至 Y=250 (低於 Child OR 節點 Y=220) 造成幾何錯位
    and_item.setPos(and_item.x(), 250.0)
    dialog._validate_geometry()

    # 驗證幾何檢查器抓出違規：and_item 為 STATE_INVALID，按鈕變成「快速修正」
    assert and_item.visual_state == LogicNodeItem.STATE_INVALID
    assert dialog.btn_confirm.text() == "快速修正"

    # 點擊「快速修正」按鈕
    dialog._on_confirm_clicked()

    # 驗證：
    # - 節點移動到修復後的正確座標 (and_item Y 應為 140.0, or_item Y 應為 220.0)
    assert and_item.y() == 140.0, f"Expected 140.0, got {and_item.y()}"
    assert or_item.y() == 220.0, f"Expected 220.0, got {or_item.y()}"
    # - 移除所有紅框警示 (STATE_NORMAL)
    assert and_item.visual_state == LogicNodeItem.STATE_NORMAL
    assert or_item.visual_state == LogicNodeItem.STATE_NORMAL
    # - 所有連線恢復正常連接 (連線數應為 4 條)
    assert len(dialog._line_items) == 4, f"Expected 4 lines, got {len(dialog._line_items)}"
    # - 「快速修正」按鈕變回「確認」
    assert dialog.btn_confirm.text() == "確認"

    print("All Phase 7 Auto Repair & Quick Fix tests passed successfully!")


if __name__ == "__main__":
    test_phase7_auto_repair_and_quick_fix()
