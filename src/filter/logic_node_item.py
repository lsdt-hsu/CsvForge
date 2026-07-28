"""
logic_node_item.py — 邏輯運算節點圖形元件
繼承 QGraphicsItem 自訂 LogicNodeItem，負責呈現邏輯運算節點 (AND/OR/XOR)。
"""

from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont


class LogicNodeItem(QGraphicsItem):
    """
    邏輯運算節點 QGraphicsItem，專門顯示邏輯運算子 (AND / OR / XOR)。
    """

    def __init__(self, op_type: str, parent=None):
        super().__init__(parent)
        self.op_type = op_type.upper()
        self.width = 80.0
        self.height = 36.0

    def boundingRect(self) -> QRectF:
        return QRectF(-self.width / 2, -self.height / 2, self.width, self.height)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.boundingRect()

        # 根據邏輯運算子主題色彩配對
        if self.op_type == "AND":
            border_color = QColor("#bb9af7")
            bg_color = QColor("#2d2045")
            text_color = QColor("#bb9af7")
        elif self.op_type == "OR":
            border_color = QColor("#f7768e")
            bg_color = QColor("#412338")
            text_color = QColor("#f7768e")
        else:  # XOR
            border_color = QColor("#e0af68")
            bg_color = QColor("#3d3525")
            text_color = QColor("#e0af68")

        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1.5))
        painter.drawRoundedRect(rect, 8.0, 8.0)

        painter.setPen(text_color)
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.op_type)
