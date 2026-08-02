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

    # 1. 測試 parse_expression 當 current_count == 0 時
    from filter.logic_tree import logic_tree
    try:
        logic_tree.parse_expression("#1", current_count=0)
        assert False, "應拋出 ValueError"
    except ValueError:
        pass
    assert logic_tree.parse_expression("", current_count=0) is None

    # 2. 測試當 expr_text 不合法且有 rules 時，回退至預設運算式
    panel = FilterPanel()
    invalid_data = {
        "rules": [{}, {}],
        "expr_text": "#1 AND #999", # 不合法規則序號
        "start_row": "1",
        "end_row": ""
    }
    panel._internal_deserialize_config(invalid_data)
    assert panel.config.expr_text == "#1 AND #2"
    assert panel.logic_tree is not None

    # 3. 測試當 rules 為空且有 expr_text 時，強制清空 expr_text 且 logic_tree 設為 None
    empty_rules_data = {
        "rules": [],
        "expr_text": "#1",
        "start_row": "1",
        "end_row": ""
    }
    panel._internal_deserialize_config(empty_rules_data)
    assert panel.config.expr_text == ""
    # 4. 測試 FilterWorker 若遇到不合法的 expr_text 依照 Fail-Fast 原則直拋例外
    from filter.filter_worker import FilterWorker
    worker = FilterWorker(
        all_rows=[["col1"]],
        filter_config={"rules": [{}], "expr_text": "#1 AND #999"},
        start_row=1,
        end_row=1,
        is_header=False
    )
    try:
        worker.run()
        assert False, "FilterWorker 在不合法 expr_text 下應遵照 Fail-Fast 直接崩潰/拋出 Exception"
    except Exception:
        pass

    print("ALL TESTS PASSED SUCCESSFULLY!")
