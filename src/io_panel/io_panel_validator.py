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
) -> tuple[bool, dict]:
    """
    通用驗證模組：驗證 io_panel 各輸入欄位的值是否合法。
    若驗證失敗，會直接以 QMessageBox.warning 彈出對話框告知使用者，並回傳 (False, {}）。
    若驗證成功，回傳 (True, parsed_dict)。
    """
    parsed = {}

    source_path = context.source_path
    output_path = context.output_path

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

    return True, parsed
