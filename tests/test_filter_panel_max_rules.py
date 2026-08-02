"""
test_filter_panel_max_rules.py — 測試 FilterPanel 規則數量上限
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

from filter.filter_panel import FilterPanel


def test_max_rules_limit():
    app = QApplication.instance() or QApplication(sys.argv)
    panel = FilterPanel()
    assert panel.MAX_RULES == 10
    
    # 測試新增規則至上限 10
    for i in range(10):
        assert len(panel.rules) == i
        assert not panel.btn_add_rule.isHidden()
        panel.add_rule()

    assert len(panel.rules) == 10
    # 達到上限 10 後，新增按鈕應隱藏
    assert panel.btn_add_rule.isHidden()

    # 超過 10 筆呼叫 add_rule 應不生效
    panel.add_rule()
    assert len(panel.rules) == 10

    # 刪除一筆後應為 9，且新增按鈕恢復顯示
    panel.delete_rule(10)
    assert len(panel.rules) == 9
    assert not panel.btn_add_rule.isHidden()

    print("FilterPanel max rules limit test passed successfully!")


if __name__ == "__main__":
    test_max_rules_limit()
