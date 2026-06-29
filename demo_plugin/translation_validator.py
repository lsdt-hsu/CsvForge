def validate_translation_inputs(parent, src_col: int, tgt_col: int) -> tuple[bool, dict]:
    """
    驗證翻譯面板「來源欄號」與「目標欄號」的值是否合法。
    因為已經改為下拉選單，欄位皆為有效的 0-based 整數，在此直接回傳。
    """
    return True, {
        "source_col": src_col,
        "target_col": tgt_col
    }
