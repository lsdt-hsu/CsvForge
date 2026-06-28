from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor

def create_add_plugin_icon() -> QIcon:
    """動態繪製加載外掛（圓圈+）的圖示"""
    pixmap = QPixmap(40, 40)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # 畫圓圈
    painter.setPen(QColor("#565f89"))
    painter.setBrush(QColor("#24283b"))
    painter.drawEllipse(2, 2, 36, 36)
    
    # 畫加號
    painter.setPen(QColor("#7aa2f7"))
    painter.drawLine(12, 20, 28, 20)
    painter.drawLine(20, 12, 20, 28)
    painter.end()
    
    icon = QIcon()
    icon.addPixmap(pixmap)
    return icon

def create_remove_plugin_icon() -> QIcon:
    """動態繪製移除外掛（圓圈-）的小圖示"""
    pixmap = QPixmap(14, 14)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # 畫圓圈 (紅色)
    painter.setPen(QColor("#f7768e"))
    painter.setBrush(QColor("#f7768e"))
    painter.drawEllipse(0, 0, 13, 13)
    
    # 畫減號 (白色)
    painter.setPen(QColor("#ffffff"))
    painter.drawLine(3, 7, 10, 7)
    painter.end()
    
    icon = QIcon()
    icon.addPixmap(pixmap)
    return icon

def create_plugin_button(parent_widget, uuid_str: str, icon: QIcon, on_click, on_remove_click) -> QPushButton:
    """
    建立活動列的外掛按鈕，並於其上嵌入圓圈減移除按鈕。
    """
    btn = QPushButton(parent_widget)
    btn.setObjectName(f"btnActivity_{uuid_str}")
    btn.setProperty("type", "activity")
    btn.setFixedSize(40, 40)
    btn.setIcon(icon)
    btn.setIconSize(QSize(40, 40))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.clicked.connect(on_click)
    btn.setProperty("active", False)
    
    # 建立圓圈減移除按鈕
    btn_remove = QPushButton(btn)
    btn_remove.setFixedSize(14, 14)
    btn_remove.setIcon(create_remove_plugin_icon())
    btn_remove.setIconSize(QSize(14, 14))
    btn_remove.setStyleSheet("border: none; background: transparent;")
    btn_remove.move(0, 26)
    btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_remove.clicked.connect(on_remove_click)
    
    return btn
