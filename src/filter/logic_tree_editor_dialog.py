"""
logic_tree_editor_dialog.py — 邏輯樹編輯器對話框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QGraphicsView,
    QGraphicsScene, QGraphicsLineItem, QPushButton, QWidget
)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPen, QColor, QPainter
from plugin_sdk import theme

try:
    from filter import logic_tree
    from filter.logic_node import RuleNode, LogicOpNode
    from filter.rule_node_item import RuleNodeItem
    from filter.logic_node_item import LogicNodeItem
except ImportError:
    import logic_tree
    from logic_node import RuleNode, LogicOpNode
    from rule_node_item import RuleNodeItem
    from logic_node_item import LogicNodeItem


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
        self._build_tree_graph()

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
        self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing)
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

    def _build_tree_graph(self):
        """解析頂部運算式文字並在 QGraphicsScene 繪製節點與相連直線。"""
        self.graphics_scene.clear()
        expr_str = self.get_expression_text().strip()
        if not expr_str:
            return

        try:
            tree_root = logic_tree.parse_expression(expr_str)
        except Exception:
            return

        if not tree_root:
            return

        # 1. 蒐集規則葉節點 (由左至右)
        leaf_nodes = []

        def collect_leaves(node):
            if isinstance(node, RuleNode) or node.op_type == "LEAF":
                leaf_nodes.append(node)
            else:
                for child in node.children:
                    collect_leaves(child)

        collect_leaves(tree_root)

        # 2. 計算節點層級與座標 (pos_x, pos_y)
        pos_map = {}
        level_map = {}

        spacing_x = 110.0
        base_y = 300.0
        level_height = 80.0

        for i, leaf in enumerate(leaf_nodes):
            level_map[leaf] = 0
            pos_map[leaf] = QPointF(i * spacing_x, base_y)

        def calculate_node_metrics(node):
            if isinstance(node, RuleNode) or node.op_type == "LEAF":
                return level_map[node], pos_map[node].x()

            child_levels = []
            child_xs = []
            for child in node.children:
                c_lvl, c_x = calculate_node_metrics(child)
                child_levels.append(c_lvl)
                child_xs.append(c_x)

            node_lvl = 1 + (max(child_levels) if child_levels else 0)
            node_x = sum(child_xs) / len(child_xs) if child_xs else 0.0

            level_map[node] = node_lvl
            node_y = base_y - node_lvl * level_height
            pos_map[node] = QPointF(node_x, node_y)

            return node_lvl, node_x

        calculate_node_metrics(tree_root)

        # 3. 繪製相連直線 (QGraphicsLineItem)
        line_pen = QPen(QColor("#565f89"), 2.0)
        line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        def draw_connections(node):
            if isinstance(node, RuleNode) or node.op_type == "LEAF":
                return
            p_pos = pos_map[node]
            for child in node.children:
                c_pos = pos_map[child]
                line = QGraphicsLineItem(p_pos.x(), p_pos.y(), c_pos.x(), c_pos.y())
                line.setPen(line_pen)
                line.setZValue(-1)
                self.graphics_scene.addItem(line)
                draw_connections(child)

        draw_connections(tree_root)

        # 4. 繪製節點 (RuleNodeItem & LogicNodeItem)
        def draw_nodes(node):
            pos = pos_map[node]
            if isinstance(node, RuleNode) or node.op_type == "LEAF":
                item = RuleNodeItem(node.leaf_idx)
            else:
                item = LogicNodeItem(node.op_type)

            item.setPos(pos)
            item.setZValue(0)
            self.graphics_scene.addItem(item)

            if not (isinstance(node, RuleNode) or node.op_type == "LEAF"):
                for child in node.children:
                    draw_nodes(child)

        draw_nodes(tree_root)

        # 5. 調整 Scene 範圍與 View 縮放視角
        boundingRect = self.graphics_scene.itemsBoundingRect()
        if not boundingRect.isEmpty():
            padded_rect = boundingRect.adjusted(-60, -60, 60, 60)
            self.graphics_scene.setSceneRect(padded_rect)
            self.graphics_view.fitInView(padded_rect, Qt.AspectRatioMode.KeepAspectRatio)

    def showEvent(self, event):
        super().showEvent(event)
        boundingRect = self.graphics_scene.itemsBoundingRect()
        if not boundingRect.isEmpty():
            self.graphics_view.fitInView(
                boundingRect.adjusted(-60, -60, 60, 60), Qt.AspectRatioMode.KeepAspectRatio
            )
