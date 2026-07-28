"""
editor_graphics_scene.py — 自訂 QGraphicsScene 事件轉發模組
"""

from PyQt6.QtWidgets import QGraphicsScene


class EditorGraphicsScene(QGraphicsScene):
    """
    自訂 QGraphicsScene，負責將滑鼠與鍵盤事件轉發至 LogicTreeEditorDialog。
    """

    def __init__(self, dialog: "LogicTreeEditorDialog", parent=None):
        super().__init__(parent)
        self.dialog = dialog

    def mousePressEvent(self, event):
        if self.dialog.handle_scene_mouse_press(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dialog.handle_scene_mouse_move(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dialog.handle_scene_mouse_release(event):
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.dialog.handle_scene_mouse_double_click(event):
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        if self.dialog.handle_scene_key_press(event):
            return
        super().keyPressEvent(event)
