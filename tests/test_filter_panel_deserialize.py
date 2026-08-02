import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from PyQt6.QtWidgets import QApplication
from filter.filter_panel import FilterPanel
from settings_manager import SettingsManager

app = QApplication.instance() or QApplication(sys.argv)

def test_filter_panel_deserialize_preserves_expr_text():
    panel = FilterPanel()
    
    initial_data = {
        "rules": [
            {
                "compare_col": -1,
                "compare_method": 0,
                "invert": False,
                "compare_target": -1,
                "compare_value": "hello",
                "belong_value_idx": 0,
                "range_start": 0,
                "range_end": 0
            },
            {
                "compare_col": -1,
                "compare_method": 0,
                "invert": False,
                "compare_target": -1,
                "compare_value": "world",
                "belong_value_idx": 0,
                "range_start": 0,
                "range_end": 0
            }
        ],
        "logic_tree": {
            "type": "AND",
            "children": [
                {"type": "RULE", "index": 1},
                {"type": "RULE", "index": 2}
            ]
        },
        "expr_text": "#1 AND #2",
        "start_row": "1",
        "end_row": ""
    }

    panel._internal_deserialize_config(initial_data)

    # 驗證反序列化後 config 中的 expr_text 未被清空，且已動態解析成 logic_tree
    assert panel.config.expr_text == "#1 AND #2"
    assert panel.config.dirty is False
    assert panel.logic_tree is not None

    serialized = panel._internal_serialize_config()
    assert serialized["expr_text"] == "#1 AND #2"
    assert serialized["rules"] == initial_data["rules"]
    assert "logic_tree" not in serialized

if __name__ == "__main__":
    test_filter_panel_deserialize_preserves_expr_text()
    print("ALL TESTS PASSED SUCCESSFULLY!")
