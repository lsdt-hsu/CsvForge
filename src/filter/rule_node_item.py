"""
rule_node_item.py — 規則節點圖形元件
繼承 QGraphicsItem 自訂 RuleNodeItem，負責呈現規則節點 (#n)。
"""

from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont


class RuleNodeItem(QGraphicsItem):
    """
    規則節點 QGraphicsItem，專門顯示規則編號 (例如 #1, #2)。
    """

    def __init__(self, rule_idx: int, parent=None):
        super().__init__(parent)
        self.rule_idx = rule_idx
        self.width = 70.0
        self.height = 36.0

    def boundingRect(self) -> QRectF:
        return QRectF(-self.width / 2, -self.height / 2, self.width, self.height)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.boundingRect()

        # 背景與邊框
        brush = QBrush(QColor("#24283b"))
        pen = QPen(QColor("#7aa2f7"), 1.5)
        painter.setBrush(brush)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 8.0, 8.0)

        # 文字繪製 (#1, #2, ...)
        painter.setPen(QColor("#c0caf5"))
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"#{self.rule_idx}")
