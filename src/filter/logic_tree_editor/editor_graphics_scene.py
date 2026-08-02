"""
editor_graphics_scene.py — 自訂 QGraphicsScene 事件轉發模組
"""

import weakref
from PyQt6.QtWidgets import QGraphicsScene


class EditorGraphicsScene(QGraphicsScene):
    """
    自訂 QGraphicsScene，負責將滑鼠與鍵盤事件轉發至 LogicTreeEditorDialog。
    使用 weakref 持有 dialog 弱引用，避免強引用循環造成記憶體洩漏。
    """

    def __init__(self, dialog: "LogicTreeEditorDialog", parent=None):
        super().__init__(parent)
        self._dialog_ref = weakref.ref(dialog)

    @property
    def dialog(self):
        return self._dialog_ref()

    def mousePressEvent(self, event):
        dlg = self.dialog
        if dlg and dlg.handle_scene_mouse_press(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        dlg = self.dialog
        if dlg and dlg.handle_scene_mouse_move(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        dlg = self.dialog
        if dlg and dlg.handle_scene_mouse_release(event):
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        dlg = self.dialog
        if dlg and dlg.handle_scene_mouse_double_click(event):
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        dlg = self.dialog
        if dlg and dlg.handle_scene_key_press(event):
            return
        super().keyPressEvent(event)
