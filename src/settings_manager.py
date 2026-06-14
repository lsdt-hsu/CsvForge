import json
import os

class SettingsManager:
    def __init__(self, filepath):
        self.filepath = filepath

    def load(self) -> dict:
        """
        讀取並解析設定檔，若檔案不存在或出錯則回傳空字典。
        """
        if not os.path.exists(self.filepath):
            return {}
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save(self, data: dict) -> bool:
        """
        將組態字典以 JSON 格式序列化儲存，回傳是否成功。
        """
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False
