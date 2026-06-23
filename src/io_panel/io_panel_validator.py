import os
from PyQt6.QtWidgets import QMessageBox

def validate_paths_not_equal(parent, source_path: str, output_path: str, mode: str = "task") -> bool:
    """
    驗證來源 CSV 與輸出 CSV 路徑是否相同。
    若相同，彈出對話框並回傳 False；否則回傳 True。
    mode 可以是:
      - "task": "來源 CSV 與輸出 CSV 路徑相同，無法開始任務！請變更輸出路徑。"
      - "save": "來源 CSV 與輸出 CSV 路徑相同，無法存檔！請變更輸出路徑。"
      - "browse_src": "選擇的來源 CSV 檔案不能與輸出 CSV 檔案路徑相同！請重新選擇。"
      - "browse_out": "選擇的輸出 CSV 檔案不能與來源 CSV 檔案路徑相同！請重新選擇。"
      - "config": "偵測到儲存的來源 CSV 與輸出 CSV 路徑相同！已自動清空輸出路徑以防檔案毀損。"
    """
    if not source_path or not output_path:
        return True

    # 正規化路徑以進行 Windows 不區分大小寫之精準比較
    norm_src = os.path.normpath(source_path.strip()).lower()
    norm_out = os.path.normpath(output_path.strip()).lower()

    if norm_src == norm_out:
        if mode == "save":
            msg = "來源 CSV 與輸出 CSV 路徑相同，無法存檔！請變更輸出路徑。"
            title = "路徑重複"
        elif mode == "browse_src":
            msg = "選擇的來源 CSV 檔案不能與輸出 CSV 檔案路徑相同！請重新選擇。"
            title = "路徑重複"
        elif mode == "browse_out":
            msg = "選擇的輸出 CSV 檔案不能與來源 CSV 檔案路徑相同！請重新選擇。"
            title = "路徑重複"
        elif mode == "config":
            msg = "偵測到儲存的來源 CSV 與輸出 CSV 路徑相同！已自動清空輸出路徑以防檔案毀損。"
            title = "路徑重複"
        else: # "task"
            msg = "來源 CSV 與輸出 CSV 路徑相同，無法開始任務！請變更輸出路徑。"
            title = "路徑重複"

        QMessageBox.warning(parent, title, msg)
        return False

    return True

def validate_io_panel_inputs(
    parent,
    context,
    require_source_path: bool = True,
    require_output_path: bool = False,
    require_source_col: bool = False,
    require_target_col: bool = False,
) -> tuple[bool, dict]:
    """
    通用驗證模組：驗證 io_panel 各輸入欄位的值是否合法。
    若驗證失敗，會直接以 QMessageBox.warning 彈出對話框告知使用者，並回傳 (False, {})。
    若驗證成功，回傳 (True, parsed_dict)。
    """
    parsed = {}

    source_path = context.source_path
    output_path = context.output_path
    start_row = context.start_row
    end_row = context.end_row
    source_col = context.source_col
    target_col = context.target_col

    # 1. 來源 CSV 路徑驗證
    if require_source_path:
        if not source_path or not os.path.exists(source_path):
            QMessageBox.warning(parent, "輸入錯誤", "請選擇正確的來源 CSV 檔案路徑")
            return False, {}

    # 2. 輸出 CSV 路徑驗證
    if require_output_path:
        if not output_path:
            QMessageBox.warning(parent, "輸入錯誤", "請指定輸出檔案路徑")
            return False, {}
        # 呼叫獨立的重複檢查函式
        if require_source_path and not validate_paths_not_equal(parent, source_path, output_path, mode="task"):
            return False, {}

    # 3. 起始行號驗證
    start_row_str = str(start_row).strip() if start_row is not None else ""
    if start_row_str == "":
        start_row_val = 1
    else:
        try:
            start_row_val = int(start_row_str)
            if start_row_val < 1:
                QMessageBox.warning(parent, "輸入錯誤", "起始行號必須是大於或等於 1 的正整數")
                return False, {}
        except (ValueError, TypeError):
            QMessageBox.warning(parent, "輸入錯誤", "起始行號必須是大於或等於 1 的正整數")
            return False, {}
    parsed["start_row"] = start_row_val

    # 4. 結束行號驗證
    end_row_str = str(end_row).strip() if end_row is not None else ""
    if end_row_str != "":
        try:
            end_row_val = int(end_row_str)
            if end_row_val < start_row_val:
                QMessageBox.warning(parent, "輸入錯誤", "結束行號不能小於起始行號")
                return False, {}
        except (ValueError, TypeError):
            QMessageBox.warning(parent, "輸入錯誤", "結束行號必須是正整數")
            return False, {}
    else:
        end_row_val = None
    parsed["end_row"] = end_row_val

    # 5. 欄號驗證 (合併與原本 Translator 相同的錯誤訊息)
    if require_source_col or require_target_col:
        sc_ok = False
        if require_source_col:
            try:
                sc_val = int(str(source_col).strip())
                if sc_val >= 1:
                    parsed["source_col"] = sc_val
                    sc_ok = True
            except Exception:
                pass
        else:
            sc_ok = True

        tc_ok = False
        if require_target_col:
            try:
                tc_val = int(str(target_col).strip())
                if tc_val >= 1:
                    parsed["target_col"] = tc_val
                    tc_ok = True
            except Exception:
                pass
        else:
            tc_ok = True

        if not sc_ok or not tc_ok:
            QMessageBox.warning(parent, "輸入錯誤", "來源欄號與目標欄號必須是大於或等於 1 的正整數")
            return False, {}

    return True, parsed
