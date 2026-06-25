import os
from PyQt6.QtWidgets import QMessageBox

def validate_paths_not_equal(parent, source_path: str, output_path: str, mode: str = "task") -> bool:
    """
    驗證來源 CSV 與輸出 CSV 路徑是否相同。
    若相同，彈出對話框並回傳 False；否則回傳 True。
    """
    if not source_path or not output_path:
        return True

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
    source_path: str,
    output_path: str,
    require_source_path: bool = True,
    require_output_path: bool = False,
) -> tuple[bool, dict]:
    """
    通用驗證模組：驗證各輸入路徑是否合法。不依賴 AppContext。
    """
    parsed = {}

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
        # 呼叫重複檢查
        if require_source_path and not validate_paths_not_equal(parent, source_path, output_path, mode="task"):
            return False, {}

    return True, parsed
