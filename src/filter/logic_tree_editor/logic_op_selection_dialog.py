"""
logic_op_selection_dialog.py — 邏輯運算子選擇對話框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QRadioButton
)
from PyQt6.QtCore import Qt
from plugin_sdk import theme


class LogicOpSelectionDialog(QDialog):
    """
    編輯 Logic 運算子 (AND / OR / XOR) 之 Modal 對話框。
    """

    def __init__(self, current_op: str = "AND", parent=None):
        super().__init__(parent)
        self.setWindowTitle("選擇邏輯運算子")
        self.setModal(True)
        self.setFixedWidth(280)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1b26;
            }
            QLabel {
                color: #c0caf5;
                font-size: 13px;
                font-weight: bold;
            }
            QRadioButton {
                color: #c0caf5;
                font-size: 13px;
                padding: 4px;
            }
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
            }
        """)

        self.selected_op = current_op.upper()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        lbl_title = QLabel("請選擇邏輯運算子：")
        layout.addWidget(lbl_title)

        ops_layout = QVBoxLayout()
        ops_layout.setSpacing(8)

        self.rad_and = QRadioButton("AND  (兩者皆成立)")
        self.rad_or = QRadioButton("OR   (任一成立)")
        self.rad_xor = QRadioButton("XOR  (交替互斥)")

        if self.selected_op == "OR":
            self.rad_or.setChecked(True)
        elif self.selected_op == "XOR":
            self.rad_xor.setChecked(True)
        else:
            self.rad_and.setChecked(True)

        ops_layout.addWidget(self.rad_and)
        ops_layout.addWidget(self.rad_or)
        ops_layout.addWidget(self.rad_xor)
        layout.addLayout(ops_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("取消")
        theme.applyStandardButtonStyle(self.btn_cancel)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_confirm = QPushButton("確認")
        theme.applyPrimaryButtonStyle(self.btn_confirm, is_running=False)
        self.btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_confirm.clicked.connect(self._on_confirm)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_confirm)
        layout.addLayout(btn_layout)

    def _on_confirm(self):
        if self.rad_or.isChecked():
            self.selected_op = "OR"
        elif self.rad_xor.isChecked():
            self.selected_op = "XOR"
        else:
            self.selected_op = "AND"
        self.accept()

    def get_selected_op(self) -> str:
        return self.selected_op
