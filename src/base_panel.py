from PyQt6.QtWidgets import QFrame

class BasePanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("grpFrame")
