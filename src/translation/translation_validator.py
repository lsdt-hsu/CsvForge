from PyQt6.QtWidgets import QMessageBox

def validate_translation_inputs(parent, src_col: str, tgt_col: str) -> tuple[bool, dict]:
    """
    驗證翻譯面板「來源欄號」與「目標欄號」的值是否合法。
    若驗證失敗，會直接以 QMessageBox.warning 彈出對話框告知使用者，並回傳 (False, {})。
    若驗證成功，將欄號轉換為正整數並回傳 (True, parsed_dict)。
    """
    parsed = {}
    sc_ok = False
    tc_ok = False

    try:
        sc_val = int(str(src_col).strip())
        if sc_val >= 1:
            parsed["source_col"] = sc_val
            sc_ok = True
    except Exception:
        pass

    try:
        tc_val = int(str(tgt_col).strip())
        if tc_val >= 1:
            parsed["target_col"] = tc_val
            tc_ok = True
    except Exception:
        pass

    if not sc_ok or not tc_ok:
        QMessageBox.warning(parent, "輸入錯誤", "來源欄號與目標欄號必須是大於或等於 1 的正整數")
        return False, {}

    return True, parsed
