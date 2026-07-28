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
    from filter import logic_tree
    from filter.logic_node import RuleNode, LogicOpNode
    from filter.rule_node_item import RuleNodeItem
    from filter.logic_node_item import LogicNodeItem
except ImportError:
    import logic_tree
    from logic_node import RuleNode, LogicOpNode
    from rule_node_item import RuleNodeItem
    from logic_node_item import LogicNodeItem


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

    def keyPressEvent(self, event):
        if self.dialog.handle_scene_key_press(event):
            return
        super().keyPressEvent(event)


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
        self._spacing_x = spacing_x
        self._base_y = base_y

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

        self._tree_root = tree_root
        self._node_to_item = {}

        # 4. 繪製節點 (RuleNodeItem & LogicNodeItem)
        rule_items_by_leaf = {}
        logic_items = []

        def draw_nodes(node):
            pos = pos_map[node]
            if isinstance(node, RuleNode) or node.op_type == "LEAF":
                item = RuleNodeItem(node.leaf_idx)
                rule_items_by_leaf[node] = item
            else:
                item = LogicNodeItem(node.op_type)
                logic_items.append(item)

            self._node_to_item[node] = item
            item.setPos(pos)
            item.setZValue(0)
            self.graphics_scene.addItem(item)

            if not (isinstance(node, RuleNode) or node.op_type == "LEAF"):
                for child in node.children:
                    draw_nodes(child)

        draw_nodes(tree_root)

        # 記錄 Slot 座標與 Initial Rule 節點列表
        self._slot_positions = [QPointF(i * spacing_x, base_y) for i in range(len(leaf_nodes))]
        self._initial_rule_items = [rule_items_by_leaf[leaf] for leaf in leaf_nodes if leaf in rule_items_by_leaf]
        self._initial_slot_map = {item: i for i, item in enumerate(self._initial_rule_items)}
        self._current_slot_order = list(self._initial_rule_items)

        # 建立離散高度層級 (n 個 Rule -> n-1 個離散高度層級)
        num_layers = max(0, len(leaf_nodes) - 1)
        self._layer_positions_y = [base_y - (i + 1) * level_height for i in range(num_layers)]

        # 依初始 Y 座標由低到高（Level 1 至 Level n-1）排序 Logic 節點，並指派至對應離散層級
        logic_items.sort(key=lambda item: (base_y - item.pos().y(), item.pos().x()))
        for i in range(min(num_layers, len(logic_items))):
            logic_items[i].setPos(logic_items[i].x(), self._layer_positions_y[i])

        self._initial_logic_items = list(logic_items)
        self._current_logic_layer_order = list(logic_items)

        # 5. 執行初始幾何合法性檢查
        self._validate_geometry()

        # 6. 調整 Scene 範圍與 View 縮放視角
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

    # ----------------------------------------------------------------------
    # 拖曳與 Slot Preview 事件處理
    # ----------------------------------------------------------------------

    def _calc_slot_idx(self, x_pos: float) -> int:
        if not self._slot_positions:
            return 0
        idx = int(round(x_pos / self._spacing_x))
        return max(0, min(len(self._slot_positions) - 1, idx))

    def _calc_layer_idx(self, y_pos: float) -> int:
        if not self._layer_positions_y:
            return 0
        best_idx = 0
        min_dist = float("inf")
        for i, layer_y in enumerate(self._layer_positions_y):
            dist = abs(y_pos - layer_y)
            if dist < min_dist:
                min_dist = dist
                best_idx = i
        return best_idx

    def handle_scene_mouse_press(self, event) -> bool:
        if event.button() == Qt.MouseButton.LeftButton:
            items = self.graphics_scene.items(event.scenePos())
            target_rule = None
            target_logic = None
            for it in items:
                if isinstance(it, LogicNodeItem) and it != self._ghost_logic_item:
                    target_logic = it
                    break
                elif isinstance(it, RuleNodeItem) and it != self._ghost_item:
                    target_rule = it
                    break

            if target_logic and target_logic in self._initial_logic_items:
                self._start_drag_logic(target_logic, event.scenePos())
                return True
            elif target_rule and target_rule in self._initial_rule_items:
                self._start_drag(target_rule, event.scenePos())
                return True

        elif (self._is_dragging or self._is_dragging_logic) and event.button() in (
            Qt.MouseButton.RightButton,
            Qt.MouseButton.MiddleButton,
        ):
            if self._is_dragging_logic:
                self._cancel_logic_drag()
            if self._is_dragging:
                self._cancel_drag()
            return True

        return False

    def _start_drag(self, item: RuleNodeItem, scene_pos: QPointF):
        self._is_dragging = True
        self._dragged_item = item

        # 記錄本次拖曳開始前的順序與 Slot 映射基準
        self._drag_start_order = list(self._current_slot_order)
        self._drag_start_slot_map = {it: i for i, it in enumerate(self._drag_start_order)}

        # 建立半透明預覽圖示跟隨游標
        self._ghost_item = RuleNodeItem(item.rule_idx)
        self._ghost_item.setOpacity(0.6)
        self._ghost_item.setZValue(100)
        self.graphics_scene.addItem(self._ghost_item)
        self._ghost_item.setPos(scene_pos)

        slot_idx = self._calc_slot_idx(scene_pos.x())
        self._pending_slot_idx = slot_idx
        self._hover_timer.start(200)

    def _start_drag_logic(self, item: LogicNodeItem, scene_pos: QPointF):
        self._is_dragging_logic = True
        self._dragged_logic_item = item

        # 記錄本次拖曳開始前的層級順序與映射基準
        self._drag_start_logic_order = list(self._current_logic_layer_order)
        self._drag_start_logic_layer_map = {it: i for i, it in enumerate(self._drag_start_logic_order)}

        # 建立半透明預覽圖示跟隨游標 (鎖定 X 軸，僅隨 Y 軸移動)
        self._ghost_logic_item = LogicNodeItem(item.op_type)
        self._ghost_logic_item.setOpacity(0.6)
        self._ghost_logic_item.setZValue(100)
        self.graphics_scene.addItem(self._ghost_logic_item)
        self._ghost_logic_item.setPos(QPointF(item.x(), scene_pos.y()))

        layer_idx = self._calc_layer_idx(scene_pos.y())
        self._pending_logic_layer_idx = layer_idx
        self._logic_hover_timer.start(200)

    def handle_scene_mouse_move(self, event) -> bool:
        if self._is_dragging_logic:
            scene_pos = event.scenePos()
            if self._ghost_logic_item and self._dragged_logic_item:
                self._ghost_logic_item.setPos(QPointF(self._dragged_logic_item.x(), scene_pos.y()))

            layer_idx = self._calc_layer_idx(scene_pos.y())
            if layer_idx != self._pending_logic_layer_idx:
                self._pending_logic_layer_idx = layer_idx
                self._logic_hover_timer.start(200)

            return True

        if self._is_dragging:
            scene_pos = event.scenePos()
            if self._ghost_item:
                self._ghost_item.setPos(scene_pos)

            slot_idx = self._calc_slot_idx(scene_pos.x())
            if slot_idx != self._pending_slot_idx:
                self._pending_slot_idx = slot_idx
                self._hover_timer.start(200)

            return True
        return False

    def _on_hover_timeout(self):
        if not self._is_dragging or self._pending_slot_idx is None or self._dragged_item is None:
            return

        target_slot = self._pending_slot_idx

        # 計算預覽 Slot 排列 (將 dragged_item 插入 target_slot，其餘順移)
        new_order = [item for item in self._drag_start_order if item != self._dragged_item]
        target_slot = max(0, min(len(new_order), target_slot))
        new_order.insert(target_slot, self._dragged_item)

        # 更新卡片位置與視覺狀態回饋 (相對拖曳前狀態 _drag_start_slot_map)
        for i, item in enumerate(new_order):
            item.setPos(self._slot_positions[i])
            if item == self._dragged_item:
                item.set_visual_state(RuleNodeItem.STATE_DRAGGING)
            elif self._drag_start_slot_map.get(item) != i:
                item.set_visual_state(RuleNodeItem.STATE_DISPLACED)
            else:
                item.set_visual_state(RuleNodeItem.STATE_NORMAL)

        self._current_slot_order = new_order
        self._sync_ast_and_update_expression()
        self._validate_geometry()

    def _on_logic_hover_timeout(self):
        if not self._is_dragging_logic or self._pending_logic_layer_idx is None or self._dragged_logic_item is None:
            return

        target_layer = self._pending_logic_layer_idx

        # 計算預覽 Logic 層級排列 (將 dragged_logic_item 插入 target_layer，其餘順移)
        new_order = [item for item in self._drag_start_logic_order if item != self._dragged_logic_item]
        target_layer = max(0, min(len(new_order), target_layer))
        new_order.insert(target_layer, self._dragged_logic_item)

        # 更新 Logic 節點高度與視覺狀態回饋
        for i, item in enumerate(new_order):
            item.setPos(item.x(), self._layer_positions_y[i])
            if item == self._dragged_logic_item:
                item.set_visual_state(LogicNodeItem.STATE_DRAGGING)
            elif self._drag_start_logic_layer_map.get(item) != i:
                item.set_visual_state(LogicNodeItem.STATE_DISPLACED)
            else:
                item.set_visual_state(LogicNodeItem.STATE_NORMAL)

        self._current_logic_layer_order = new_order
        self._validate_geometry()

    def _sync_ast_and_update_expression(self):
        """
        將目前 Slot 順序中的 RuleNodeItem 同步至 AST 葉節點，並動態重構運算式文字。
        """
        if not hasattr(self, "_tree_root") or not self._tree_root or not getattr(self, "_current_slot_order", None):
            return

        leaf_nodes = []

        def collect_leaves(node):
            if isinstance(node, RuleNode) or node.op_type == "LEAF":
                leaf_nodes.append(node)
            else:
                for child in node.children:
                    collect_leaves(child)

        collect_leaves(self._tree_root)

        for i, leaf in enumerate(leaf_nodes):
            if i < len(self._current_slot_order):
                item = self._current_slot_order[i]
                leaf.leaf_idx = item.rule_idx

        new_expr = logic_tree.to_string(self._tree_root)
        self.txt_expression.setPlainText(new_expr)

    def _cancel_drag(self):
        if not self._is_dragging:
            return

        self._hover_timer.stop()

        if self._ghost_item and self._ghost_item.scene() == self.graphics_scene:
            self.graphics_scene.removeItem(self._ghost_item)
            self._ghost_item = None

        # 還原至該次拖曳開始前順序與一般視覺狀態
        for i, item in enumerate(self._drag_start_order):
            item.setPos(self._slot_positions[i])
            item.set_visual_state(RuleNodeItem.STATE_NORMAL)

        self._current_slot_order = list(self._drag_start_order)
        self._is_dragging = False
        self._dragged_item = None
        self._pending_slot_idx = None
        self._sync_ast_and_update_expression()
        self._validate_geometry()

    def _cancel_logic_drag(self):
        if not self._is_dragging_logic:
            return

        self._logic_hover_timer.stop()

        if self._ghost_logic_item and self._ghost_logic_item.scene() == self.graphics_scene:
            self.graphics_scene.removeItem(self._ghost_logic_item)
            self._ghost_logic_item = None

        # 還原至該次拖曳開始前的層級順序與一般視覺狀態
        for i, item in enumerate(self._drag_start_logic_order):
            item.setPos(item.x(), self._layer_positions_y[i])
            item.set_visual_state(LogicNodeItem.STATE_NORMAL)

        self._current_logic_layer_order = list(self._drag_start_logic_order)
        self._is_dragging_logic = False
        self._dragged_logic_item = None
        self._pending_logic_layer_idx = None
        self._validate_geometry()

    def handle_scene_mouse_release(self, event) -> bool:
        if self._is_dragging_logic and event.button() == Qt.MouseButton.LeftButton:
            self._logic_hover_timer.stop()

            if self._ghost_logic_item and self._ghost_logic_item.scene() == self.graphics_scene:
                self.graphics_scene.removeItem(self._ghost_logic_item)
                self._ghost_logic_item = None

            target_layer = self._calc_layer_idx(event.scenePos().y())
            candidate_order = [item for item in self._drag_start_logic_order if item != self._dragged_logic_item]
            target_layer = max(0, min(len(candidate_order), target_layer))
            candidate_order.insert(target_layer, self._dragged_logic_item)

            apply_order = candidate_order

            # 拖曳結束：套用最終位置，且所有 Logic 視覺狀態設為一般狀態 (STATE_NORMAL)
            for i, item in enumerate(apply_order):
                item.setPos(item.x(), self._layer_positions_y[i])
                item.set_visual_state(LogicNodeItem.STATE_NORMAL)

            self._current_logic_layer_order = list(apply_order)
            self._is_dragging_logic = False
            self._dragged_logic_item = None
            self._pending_logic_layer_idx = None
            self._validate_geometry()
            return True

        if self._is_dragging and event.button() == Qt.MouseButton.LeftButton:
            self._hover_timer.stop()

            if self._ghost_item and self._ghost_item.scene() == self.graphics_scene:
                self.graphics_scene.removeItem(self._ghost_item)
                self._ghost_item = None

            target_slot = self._calc_slot_idx(event.scenePos().x())
            candidate_order = [item for item in self._drag_start_order if item != self._dragged_item]
            target_slot = max(0, min(len(candidate_order), target_slot))
            candidate_order.insert(target_slot, self._dragged_item)

            apply_order = candidate_order

            # 拖曳結束：套用最終位置，且所有 Rule 視覺狀態設為一般狀態 (STATE_NORMAL)
            for i, item in enumerate(apply_order):
                item.setPos(self._slot_positions[i])
                item.set_visual_state(RuleNodeItem.STATE_NORMAL)

            self._current_slot_order = list(apply_order)
            self._is_dragging = False
            self._dragged_item = None
            self._pending_slot_idx = None
            self._sync_ast_and_update_expression()
            self._validate_geometry()
            return True

        return False

    def _on_confirm_clicked(self):
        """按鈕點擊事件：若為「快速修正」則修改回「確認」；若為「確認」則觸發 accept()。"""
        if self.btn_confirm.text() == "快速修正":
            self.btn_confirm.setText("確認")
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
        for node, item in self._node_to_item.items():
            if isinstance(item, LogicNodeItem):
                if node in invalid_nodes:
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


