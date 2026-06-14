from PyQt6.QtWidgets import QFrame

class BasePanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("grpFrame")

    def get_config(self) -> dict:
        return {}

    def set_config(self, config: dict):
        pass

    def get_start_button_text(self, state: str) -> str:
        if state == "critical":
            return "STOP"
        elif state == "disabled":
            return "正在停止..."
        return "開始"

    def handle_start_button_click(self, main_window, state: str):
        if state == "critical":
            main_window.cancel_task()
        else:
            main_window.start_task()
