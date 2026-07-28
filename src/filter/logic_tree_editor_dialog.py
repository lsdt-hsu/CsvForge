"""
logic_tree_editor_dialog.py — 邏輯樹編輯器對話框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QGraphicsView,
    QGraphicsScene, QPushButton, QWidget
)
from PyQt6.QtCore import Qt
from plugin_sdk import theme


class LogicTreeEditorDialog(QDialog):
    """
    邏輯樹編輯器 Modal 對話框。
    佈局分為三層：
    - 頂部：唯讀 QTextEdit，固定高度顯示邏輯運算式。
    - 中間：QGraphicsView / QGraphicsScene，透明背景，佔據剩餘空間。
    - 底部：靠右對齊的「確認」與「取消」按鈕。
    """

    def __init__(self, expression_text: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("邏輯樹編輯器")
        self.resize(700, 500)
        self.setModal(True)
        self.setStyleSheet("QDialog { background-color: #1a1b26; }")

        self._init_ui(expression_text)

    def _init_ui(self, expression_text: str):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # 1. 頂部區域：唯讀文字顯示區 (固定高度約三行)
        self.txt_expression = QTextEdit()
        theme.applyStandardLineEditStyle(self.txt_expression)
        self.txt_expression.setReadOnly(True)
        self.txt_expression.setPlainText(expression_text)
        self.txt_expression.setFixedHeight(65)
        self.txt_expression.setAcceptRichText(False)
        main_layout.addWidget(self.txt_expression)

        # 2. 中間區域：圖形化編輯區 (QGraphicsView & QGraphicsScene，佔用剩餘空間)
        self.graphics_scene = QGraphicsScene(self)
        self.graphics_scene.setBackgroundBrush(Qt.GlobalColor.transparent)

        self.graphics_view = QGraphicsView(self.graphics_scene)
        self.graphics_view.setStyleSheet(
            "QGraphicsView { background: transparent; border: 1px solid #2f3047; border-radius: 6px; }"
        )
        main_layout.addWidget(self.graphics_view, stretch=1)

        # 3. 底部區域：按鈕區 (靠右對齊，僅保留按鈕高度)
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("取消")
        theme.applyStandardButtonStyle(self.btn_cancel)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_confirm = QPushButton("確認")
        theme.applyPrimaryButtonStyle(self.btn_confirm, is_running=False)
        self.btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_confirm.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_confirm)

        main_layout.addWidget(btn_widget)

    def get_expression_text(self) -> str:
        """取得頂部唯讀運算式文字區內容。"""
        return self.txt_expression.toPlainText()
