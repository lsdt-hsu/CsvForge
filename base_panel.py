import os
from PyQt6.QtWidgets import QFrame

class BasePanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("grpFrame")

    def validate(self, ui_instance):
        """
        驗證通用與面板專屬欄位。
        回傳: (is_valid, title, error_message)
        """
        src_path = ui_instance.txt_src_path.text().strip()
        out_path = ui_instance.txt_out_path.text().strip()
        
        if not src_path or not os.path.exists(src_path):
            return False, "輸入錯誤", "請選擇正確的來源 CSV 檔案路徑"
        if not out_path:
            return False, "輸入錯誤", "請指定輸出檔案路徑"
        
        try:
            start_row = int(ui_instance.txt_start_row.text())
            if start_row < 1:
                raise ValueError()
        except ValueError:
            return False, "輸入錯誤", "起始行號必須是大於或等於 1 的正整數"

        if ui_instance.txt_end_row.text().strip():
            try:
                end_row = int(ui_instance.txt_end_row.text())
                if end_row < start_row:
                    return False, "輸入錯誤", "結束行號不能小於起始行號"
            except ValueError:
                return False, "輸入錯誤", "結束行號必須是正整數"

        # 呼叫面板自訂驗證
        is_valid, err_msg = self.validate_additional_inputs(ui_instance)
        if not is_valid:
            return False, "輸入錯誤", err_msg

        return True, "", ""

    def validate_additional_inputs(self, ui_instance):
        """
        子面板可覆寫此方法以進行額外的欄位驗證。
        """
        return True, ""
