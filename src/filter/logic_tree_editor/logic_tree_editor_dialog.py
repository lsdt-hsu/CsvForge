"""
logic_tree_editor_dialog.py — 邏輯樹編輯器對話框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QGraphicsView,
    QGraphicsScene, QGraphicsLineItem, QPushButton, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QPointF, QTimer
from PyQt6.QtGui import QPen, QColor, QPainter
from plugin_sdk import theme

try:
    from filter.logic_tree import logic_tree
    from filter.logic_tree.logic_node import RuleNode, LogicOpNode
    from filter.logic_tree_editor.rule_node_item import RuleNodeItem
    from filter.logic_tree_editor.logic_node_item import LogicNodeItem
    from filter.logic_tree_editor.logic_op_selection_dialog import LogicOpSelectionDialog
    from filter.logic_tree_editor.editor_graphics_scene import EditorGraphicsScene
    from filter.logic_tree_editor.layout_engine import TreeLayoutEngine
    from filter.logic_tree_editor.drag_controller import TreeDragController
except ImportError:
    from filter.logic_tree import logic_tree
    from logic_node import RuleNode, LogicOpNode
    from rule_node_item import RuleNodeItem
    from logic_node_item import LogicNodeItem
    from logic_op_selection_dialog import LogicOpSelectionDialog
    from editor_graphics_scene import EditorGraphicsScene
    from layout_engine import TreeLayoutEngine
    from drag_controller import TreeDragController


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

        self.drag_controller = TreeDragController(self)

        # 拖曳與 Slot preview 控制變數 (Rule 節點)
        self._slot_positions = []
        self._initial_rule_items = []
        self._initial_slot_map = {}
        self._spacing_x = 110.0
        self._base_y = 300.0

        self._is_dragging = False
        self._dragged_item = None
        self._ghost_item = None
        self._pending_slot_idx = None
        self._current_slot_order = []

        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(200)
        self._hover_timer.timeout.connect(self._on_hover_timeout)

        # 拖曳與離散高度層級 (Discrete Layers) 控制變數 (Logic 節點)
        self._layer_positions_y = []
        self._initial_logic_items = []
        self._current_logic_layer_order = []
        self._is_dragging_logic = False
        self._dragged_logic_item = None
        self._ghost_logic_item = None
        self._pending_logic_layer_idx = None

        self._tree_root = None
        self._node_to_item = {}
        self._line_items = []

        self._logic_hover_timer = QTimer(self)
        self._logic_hover_timer.setSingleShot(True)
        self._logic_hover_timer.setInterval(200)
        self._logic_hover_timer.timeout.connect(self._on_logic_hover_timeout)

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

        # 2. 中間區域：圖形化編輯區 (QGraphicsView & EditorGraphicsScene，佔用剩餘空間)
        self.graphics_scene = EditorGraphicsScene(self, self)
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
        self.btn_confirm.clicked.connect(self._on_confirm_clicked)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_confirm)

        main_layout.addWidget(btn_widget)

    def get_expression_text(self) -> str:
        """取得頂部唯讀運算式文字區內容。"""
        return self.txt_expression.toPlainText()

    def _build_tree_graph(self):
        """解析頂部運算式文字並在 QGraphicsScene 繪製節點與相連直線。"""
        res = TreeLayoutEngine.build_tree_graph(self, self.get_expression_text())
        (
            self._tree_root,
            self._node_to_item,
            leaf_nodes,
            self._slot_positions,
            self._initial_rule_items,
            self._initial_slot_map,
            self._current_slot_order,
            self._layer_positions_y,
            self._initial_logic_items,
            self._current_logic_layer_order,
        ) = res
        if self._tree_root:
            self._validate_geometry()

    def showEvent(self, event):
        super().showEvent(event)
        boundingRect = self.graphics_scene.itemsBoundingRect()
        if not boundingRect.isEmpty():
            self.graphics_view.fitInView(
                boundingRect.adjusted(-60, -60, 60, 60), Qt.AspectRatioMode.KeepAspectRatio
            )

    # ----------------------------------------------------------------------
    # 拖曳與 Slot Preview 事件處理 (委派至 TreeDragController)
    # ----------------------------------------------------------------------

    def _calc_slot_idx(self, x_pos: float) -> int:
        return self.drag_controller.calc_slot_idx(x_pos)

    def _calc_layer_idx(self, y_pos: float) -> int:
        return self.drag_controller.calc_layer_idx(y_pos)

    def handle_scene_mouse_double_click(self, event) -> bool:
        return self.drag_controller.handle_mouse_double_click(event)

    def handle_scene_mouse_press(self, event) -> bool:
        return self.drag_controller.handle_mouse_press(event)

    def _start_drag(self, item: RuleNodeItem, scene_pos: QPointF):
        self.drag_controller.start_drag(item, scene_pos)

    def _start_drag_logic(self, item: LogicNodeItem, scene_pos: QPointF):
        self.drag_controller.start_drag_logic(item, scene_pos)

    def handle_scene_mouse_move(self, event) -> bool:
        return self.drag_controller.handle_mouse_move(event)

    def _on_hover_timeout(self):
        self.drag_controller.on_hover_timeout()

    def _on_logic_hover_timeout(self):
        self.drag_controller.on_logic_hover_timeout()

    def _cancel_drag(self):
        self.drag_controller.cancel_drag()

    def _cancel_logic_drag(self):
        self.drag_controller.cancel_logic_drag()

    def handle_scene_mouse_release(self, event) -> bool:
        return self.drag_controller.handle_mouse_release(event)

    def handle_scene_key_press(self, event) -> bool:
        return self.drag_controller.handle_key_press(event)

    def _rebuild_tree_from_heights(self):
        """
        自動修正：依照當前 Rule 節點順序與 Logic 節點的高度 (Y 座標)，動態重新建立邏輯樹 (AST)。
        """
        initial_rules = getattr(self, "_initial_rule_items", [])
        current_slots = getattr(self, "_current_slot_order", initial_rules)
        initial_logics = getattr(self, "_initial_logic_items", [])
        self._tree_root, self._node_to_item = TreeLayoutEngine.rebuild_tree_from_heights(
            initial_rules, current_slots, initial_logics
        )

    def _sync_ast_and_update_expression(self):
        """
        將目前 Slot 順序中的 RuleNodeItem 同步至 AST 葉節點，並動態重構運算式文字。
        """
        self._rebuild_tree_from_heights()
        if hasattr(self, "_tree_root") and self._tree_root:
            new_expr = logic_tree.to_string(self._tree_root)
            self.txt_expression.setPlainText(new_expr)

    def _quick_fix_geometry(self):
        """
        快速修正：檢查所有邏輯節點之間的拓撲依賴關係，重新分配它們的高度層級。
        最內層運算的邏輯節點分配在最低高度層級，最外層分配在最高層級，消除幾何錯位。
        """
        tree_root = getattr(self, "_tree_root", None)
        node_to_item = getattr(self, "_node_to_item", None)
        initial_logics = getattr(self, "_initial_logic_items", [])
        spacing_x = getattr(self, "_spacing_x", 110.0)
        base_y = getattr(self, "_base_y", 300.0)

        if tree_root and node_to_item:
            self._current_logic_layer_order = TreeLayoutEngine.quick_fix_geometry(
                tree_root, node_to_item, initial_logics, spacing_x, base_y
            )
            self._validate_geometry()

    def _on_confirm_clicked(self):
        """按鈕點擊事件：若為「快速修正」則觸發 _quick_fix_geometry；若為「確認」則觸發 accept()。"""
        if self.btn_confirm.text() == "快速修正":
            self._quick_fix_geometry()
        else:
            self.accept()

    def _validate_geometry(self):
        """
        幾何合法性檢查器 (Geometry Validator)。
        由底層向上 (Post-Order) 掃描邏輯樹拓撲結構與 QGraphicsItem 幾何位置。
        - 檢查條件 1：父邏輯節點 Y 軸高度等於或低於子節點 Height (parent.y() >= child.y())
        """
        if not hasattr(self, "_tree_root") or not self._tree_root or not getattr(self, "_node_to_item", None):
            return

        invalid_nodes = set()

        # 建立 AST Leaf 節點與當前 Slot Item 之對應 (第 i 個 Leaf -> Slot i 上的 Item)
        ast_leaves = []
        def collect_leaves(node):
            if isinstance(node, RuleNode) or node.op_type == "LEAF":
                ast_leaves.append(node)
            else:
                for child in node.children:
                    collect_leaves(child)
        collect_leaves(self._tree_root)

        slot_item_map = {}
        for i, leaf in enumerate(ast_leaves):
            if i < len(getattr(self, "_current_slot_order", [])):
                slot_item_map[leaf] = self._current_slot_order[i]

        def get_item_for_node(node):
            if isinstance(node, RuleNode) or node.op_type == "LEAF":
                return slot_item_map.get(node)
            return self._node_to_item.get(node)

        def scan_node(node):
            if isinstance(node, RuleNode) or node.op_type == "LEAF":
                return

            # 由底層向上 (Post-Order) 掃描
            for child in node.children:
                scan_node(child)

            parent_item = self._node_to_item.get(node)
            if not parent_item:
                return

            # 1. Y 軸高度檢查 (parent.y() >= child.y())
            for child in node.children:
                child_item = get_item_for_node(child)
                if child_item and parent_item.y() >= child_item.y():
                    invalid_nodes.add(node)
                    break

        scan_node(self._tree_root)

        # 更新 LogicNodeItem 視覺狀態
        for item in getattr(self, "_initial_logic_items", []):
            node = next((n for n, it in self._node_to_item.items() if it == item), None)
            if self._is_dragging_logic and item == self._dragged_logic_item:
                item.set_visual_state(LogicNodeItem.STATE_DRAGGING)
            elif (
                self._is_dragging_logic
                and item in getattr(self, "_drag_start_logic_layer_map", {})
                and item in getattr(self, "_current_logic_layer_order", [])
                and self._current_logic_layer_order.index(item) != self._drag_start_logic_layer_map.get(item)
            ):
                item.set_visual_state(LogicNodeItem.STATE_DISPLACED)
            elif node and node in invalid_nodes:
                item.set_visual_state(LogicNodeItem.STATE_INVALID)
            else:
                item.set_visual_state(LogicNodeItem.STATE_NORMAL)

        # 依據檢查結果切換按鈕文字
        if invalid_nodes:
            self.btn_confirm.setText("快速修正")
        else:
            self.btn_confirm.setText("確認")

        # 重新計算並繪製動態連線 (Slot-bound 連線)
        self._update_connection_lines()

    def _update_connection_lines(self):
        """
        即時重新計算並繪製所有節點間的連接線 (Slot-bound Model)。
        - 採 Post-Order (由下往上) 遞迴檢查與繪製。
        - 邏輯樹之第 i 個 Leaf 節點永遠指向 Slot i (即 self._current_slot_order[i])。
        - 確保連線永遠留在固定 Slot，卡片置換時連線完全不交叉、不跑位。
        """
        if not hasattr(self, "_tree_root") or not self._tree_root or not getattr(self, "_node_to_item", None):
            return

        # 1. 清理現有連線
        for line_item in getattr(self, "_line_items", []):
            if line_item.scene() == self.graphics_scene:
                self.graphics_scene.removeItem(line_item)
        self._line_items = []

        line_pen = QPen(QColor("#565f89"), 2.0)
        line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        # 2. 建立 AST Leaf 節點與當前 Slot Item 之對應 (第 i 個 Leaf -> Slot i 上的 Item)
        ast_leaves = []
        def collect_leaves(node):
            if isinstance(node, RuleNode) or node.op_type == "LEAF":
                ast_leaves.append(node)
            else:
                for child in node.children:
                    collect_leaves(child)
        collect_leaves(self._tree_root)

        slot_item_map = {}
        for i, leaf in enumerate(ast_leaves):
            if i < len(getattr(self, "_current_slot_order", [])):
                slot_item_map[leaf] = self._current_slot_order[i]

        def get_item_for_node(node):
            if isinstance(node, RuleNode) or node.op_type == "LEAF":
                return slot_item_map.get(node)
            return self._node_to_item.get(node)

        def process_node_connections(node):
            if isinstance(node, RuleNode) or node.op_type == "LEAF":
                return

            for child in node.children:
                process_node_connections(child)

            parent_item = get_item_for_node(node)
            if not parent_item:
                return

            for child in node.children:
                child_item = get_item_for_node(child)
                if not child_item:
                    continue

                # 高度檢查：若父節點 Y >= 子節點 Y，則不繪製
                if parent_item.y() >= child_item.y():
                    continue

                line = QGraphicsLineItem(
                    parent_item.x(), parent_item.y(),
                    child_item.x(), child_item.y()
                )
                line.setPen(line_pen)
                line.setZValue(-1)
                self.graphics_scene.addItem(line)
                self._line_items.append(line)

        process_node_connections(self._tree_root)

    def handle_scene_key_press(self, event) -> bool:
        if event.key() == Qt.Key.Key_Escape:
            if self._is_dragging_logic:
                self._cancel_logic_drag()
                return True
            if self._is_dragging:
                self._cancel_drag()
                return True
        return False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self._is_dragging_logic:
                self._cancel_logic_drag()
                event.accept()
                return
            if self._is_dragging:
                self._cancel_drag()
                event.accept()
                return
        super().keyPressEvent(event)


