"""
drag_controller.py — 邏輯樹節點拖曳狀態與互動控制器模組
"""

from PyQt6.QtCore import Qt, QPointF
try:
    from filter.logic_tree import logic_tree
    from filter.logic_tree_editor.rule_node_item import RuleNodeItem
    from filter.logic_tree_editor.logic_node_item import LogicNodeItem
    from filter.logic_tree_editor.logic_op_selection_dialog import LogicOpSelectionDialog
except ImportError:
    from filter.logic_tree import logic_tree
    from rule_node_item import RuleNodeItem
    from logic_node_item import LogicNodeItem
    from logic_op_selection_dialog import LogicOpSelectionDialog


class TreeDragController:
    """
    負責 Rule 節點 (Slot 水平) 與 Logic 節點 (Layer 垂直) 的拖曳狀態機、
    Hover 預覽定時器、Ghost Item 生命週期以及事件處理。
    """

    def __init__(self, dialog):
        self.dialog = dialog

    def calc_slot_idx(self, x_pos: float) -> int:
        positions = getattr(self.dialog, "_slot_positions", [])
        spacing_x = getattr(self.dialog, "_spacing_x", 110.0)
        if not positions:
            return 0
        idx = int(round(x_pos / spacing_x))
        return max(0, min(len(positions) - 1, idx))

    def calc_layer_idx(self, y_pos: float) -> int:
        positions_y = getattr(self.dialog, "_layer_positions_y", [])
        if not positions_y:
            return 0
        best_idx = 0
        min_dist = float("inf")
        for i, layer_y in enumerate(positions_y):
            dist = abs(y_pos - layer_y)
            if dist < min_dist:
                min_dist = dist
                best_idx = i
        return best_idx

    def handle_mouse_double_click(self, event) -> bool:
        if event.button() == Qt.MouseButton.LeftButton:
            items = self.dialog.graphics_scene.items(event.scenePos())
            target_logic = None
            for it in items:
                if isinstance(it, LogicNodeItem) and it != getattr(self.dialog, "_ghost_logic_item", None):
                    target_logic = it
                    break

            initial_logics = getattr(self.dialog, "_initial_logic_items", [])
            if target_logic and target_logic in initial_logics:
                dlg = LogicOpSelectionDialog(target_logic.op_type, self.dialog)
                if dlg.exec() == LogicOpSelectionDialog.DialogCode.Accepted:
                    new_op = dlg.get_selected_op()
                    if new_op and new_op != target_logic.op_type:
                        target_logic.set_op_type(new_op)
                        self.dialog._rebuild_tree_from_heights()
                        self.dialog.txt_expression.setPlainText(logic_tree.to_string(self.dialog._tree_root))
                        self.dialog._refresh_display()
                return True
        return False

    def handle_mouse_press(self, event) -> bool:
        if event.button() == Qt.MouseButton.LeftButton:
            items = self.dialog.graphics_scene.items(event.scenePos())
            target_rule = None
            target_logic = None
            for it in items:
                if isinstance(it, LogicNodeItem) and it != getattr(self.dialog, "_ghost_logic_item", None):
                    target_logic = it
                    break
                elif isinstance(it, RuleNodeItem) and it != getattr(self.dialog, "_ghost_item", None):
                    target_rule = it
                    break

            initial_logics = getattr(self.dialog, "_initial_logic_items", [])
            initial_rules = getattr(self.dialog, "_initial_rule_items", [])

            if target_logic and target_logic in initial_logics:
                self.start_drag_logic(target_logic, event.scenePos())
                return True
            elif target_rule and target_rule in initial_rules:
                self.start_drag(target_rule, event.scenePos())
                return True

        elif (self.dialog._is_dragging or self.dialog._is_dragging_logic) and event.button() in (
            Qt.MouseButton.RightButton,
            Qt.MouseButton.MiddleButton,
        ):
            if self.dialog._is_dragging_logic:
                self.cancel_logic_drag()
            if self.dialog._is_dragging:
                self.cancel_drag()
            return True

        return False

    def start_drag(self, item: RuleNodeItem, scene_pos: QPointF):
        self.dialog._is_dragging = True
        self.dialog._dragged_item = item
        item.set_visual_state(RuleNodeItem.STATE_DRAGGING)

        self.dialog._drag_start_order = list(getattr(self.dialog, "_current_slot_order", []))
        self.dialog._drag_start_slot_map = {it: i for i, it in enumerate(self.dialog._drag_start_order)}

        self.dialog._ghost_item = RuleNodeItem(item.rule_idx)
        self.dialog._ghost_item.setOpacity(0.6)
        self.dialog._ghost_item.setZValue(100)
        self.dialog.graphics_scene.addItem(self.dialog._ghost_item)
        self.dialog._ghost_item.setPos(QPointF(scene_pos.x(), item.y()))

        slot_idx = self.calc_slot_idx(scene_pos.x())
        self.dialog._pending_slot_idx = slot_idx
        self.dialog._hover_timer.start(200)

    def start_drag_logic(self, item: LogicNodeItem, scene_pos: QPointF):
        self.dialog._is_dragging_logic = True
        self.dialog._dragged_logic_item = item
        item.set_visual_state(LogicNodeItem.STATE_DRAGGING)

        self.dialog._drag_start_logic_order = list(getattr(self.dialog, "_current_logic_layer_order", []))
        self.dialog._drag_start_logic_layer_map = {it: i for i, it in enumerate(self.dialog._drag_start_logic_order)}

        self.dialog._ghost_logic_item = LogicNodeItem(item.op_type)
        self.dialog._ghost_logic_item.setOpacity(0.6)
        self.dialog._ghost_logic_item.setZValue(100)
        self.dialog.graphics_scene.addItem(self.dialog._ghost_logic_item)
        # [設計不可變] Ghost 的 X 軸鎖定為拖曳前節點的原始 X，禁止水平偏移。
        # Logic 節點 X 是由 AST 計算出的子樹葉節點相鄰中點；若 X 改變，
        # rebuild_tree_from_heights 的 X 排序 → gap-index 對應關係將失效，
        # 導致 build_subtree 以錯誤的切割點重建 AST，造成運算子語意錯誤。
        self.dialog._ghost_logic_item.setPos(QPointF(item.x(), scene_pos.y()))

        layer_idx = self.calc_layer_idx(scene_pos.y())
        self.dialog._pending_logic_layer_idx = layer_idx
        self.dialog._logic_hover_timer.start(200)

    def handle_mouse_move(self, event) -> bool:
        if self.dialog._is_dragging_logic:
            scene_pos = event.scenePos()
            if self.dialog._ghost_logic_item and self.dialog._dragged_logic_item:
                # [設計不可變] 拖曳中 Ghost 僅允許 Y 軸跟隨滑鼠，X 鎖定為拖曳目標的原始 X。
                # 保持 X 不變是確保 rebuild_tree_from_heights 能正確重建 AST 的前提。
                self.dialog._ghost_logic_item.setPos(QPointF(self.dialog._dragged_logic_item.x(), scene_pos.y()))

            layer_idx = self.calc_layer_idx(scene_pos.y())
            if layer_idx != self.dialog._pending_logic_layer_idx:
                self.dialog._pending_logic_layer_idx = layer_idx
                self.dialog._logic_hover_timer.start(200)

            return True

        if self.dialog._is_dragging:
            scene_pos = event.scenePos()
            if self.dialog._ghost_item and self.dialog._dragged_item:
                self.dialog._ghost_item.setPos(QPointF(scene_pos.x(), self.dialog._dragged_item.y()))

            slot_idx = self.calc_slot_idx(scene_pos.x())
            if slot_idx != self.dialog._pending_slot_idx:
                self.dialog._pending_slot_idx = slot_idx
                self.dialog._hover_timer.start(200)

            return True

        return False

    def on_hover_timeout(self):
        if not self.dialog._is_dragging or self.dialog._pending_slot_idx is None or self.dialog._dragged_item is None:
            return

        # [設計不可變] Rule 節點拖曳只更新 _current_slot_order（葉節點的排列順序）。
        # Logic 節點的 X、Y 座標完全不受影響，因此 rebuild_tree_from_heights 中
        # build_subtree 的 min-Y 選根邏輯不變，AST 拓撲結構（運算子父子關係）保持不變。
        # 只有葉節點的「內容」（rule_idx）隨 slot 順序改變，不影響運算結構。
        target_slot = self.dialog._pending_slot_idx
        drag_start_order = getattr(self.dialog, "_drag_start_order", [])

        new_order = [item for item in drag_start_order if item != self.dialog._dragged_item]
        target_slot = max(0, min(len(new_order), target_slot))
        new_order.insert(target_slot, self.dialog._dragged_item)

        slot_positions = getattr(self.dialog, "_slot_positions", [])
        drag_start_slot_map = getattr(self.dialog, "_drag_start_slot_map", {})

        for i, item in enumerate(new_order):
            if i < len(slot_positions):
                item.setPos(slot_positions[i])
            if item == self.dialog._dragged_item:
                item.set_visual_state(RuleNodeItem.STATE_DRAGGING)
            elif drag_start_slot_map.get(item) != i:
                item.set_visual_state(RuleNodeItem.STATE_DISPLACED)
            else:
                item.set_visual_state(RuleNodeItem.STATE_NORMAL)

        self.dialog._current_slot_order = new_order
        self.dialog._rebuild_tree_from_heights()
        self.dialog.txt_expression.setPlainText(logic_tree.to_string(self.dialog._tree_root))
        self.dialog._refresh_display()

    def on_logic_hover_timeout(self):
        if not self.dialog._is_dragging_logic or self.dialog._pending_logic_layer_idx is None or self.dialog._dragged_logic_item is None:
            return

        target_layer = self.dialog._pending_logic_layer_idx
        drag_start_order = getattr(self.dialog, "_drag_start_logic_order", [])

        new_order = [item for item in drag_start_order if item != self.dialog._dragged_logic_item]
        target_layer = max(0, min(len(new_order), target_layer))
        new_order.insert(target_layer, self.dialog._dragged_logic_item)

        layer_positions_y = getattr(self.dialog, "_layer_positions_y", [])
        drag_start_layer_map = getattr(self.dialog, "_drag_start_logic_layer_map", {})

        for i, item in enumerate(new_order):
            if i < len(layer_positions_y):
                # [設計不可變] 僅更新 Y 軸（Layer 高度），X 永不改變。
                # Y 的離散層級決定 build_subtree 的 min-Y 選根順序（運算子的父子層級關係）；
                # X 的固定確保 gap-index 對應關係持續成立。
                item.setPos(item.x(), layer_positions_y[i])
            if item == self.dialog._dragged_logic_item:
                item.set_visual_state(LogicNodeItem.STATE_DRAGGING)
            elif drag_start_layer_map.get(item) != i:
                item.set_visual_state(LogicNodeItem.STATE_DISPLACED)
            else:
                item.set_visual_state(LogicNodeItem.STATE_NORMAL)

        self.dialog._current_logic_layer_order = new_order
        self.dialog._rebuild_tree_from_heights()
        self.dialog.txt_expression.setPlainText(logic_tree.to_string(self.dialog._tree_root))
        self.dialog._refresh_display()

    def cancel_drag(self):
        if not self.dialog._is_dragging:
            return

        self.dialog._hover_timer.stop()

        if self.dialog._ghost_item and self.dialog._ghost_item.scene() == self.dialog.graphics_scene:
            self.dialog.graphics_scene.removeItem(self.dialog._ghost_item)
            self.dialog._ghost_item = None

        drag_start_order = getattr(self.dialog, "_drag_start_order", [])
        slot_positions = getattr(self.dialog, "_slot_positions", [])

        for i, item in enumerate(drag_start_order):
            if i < len(slot_positions):
                item.setPos(slot_positions[i])
            item.set_visual_state(RuleNodeItem.STATE_NORMAL)

        self.dialog._current_slot_order = list(drag_start_order)
        self.dialog._is_dragging = False
        self.dialog._dragged_item = None
        self.dialog._pending_slot_idx = None
        self.dialog._rebuild_tree_from_heights()
        self.dialog.txt_expression.setPlainText(logic_tree.to_string(self.dialog._tree_root))
        self.dialog._refresh_display()

    def cancel_logic_drag(self):
        if not self.dialog._is_dragging_logic:
            return

        self.dialog._logic_hover_timer.stop()

        if self.dialog._ghost_logic_item and self.dialog._ghost_logic_item.scene() == self.dialog.graphics_scene:
            self.dialog.graphics_scene.removeItem(self.dialog._ghost_logic_item)
            self.dialog._ghost_logic_item = None

        drag_start_order = getattr(self.dialog, "_drag_start_logic_order", [])
        layer_positions_y = getattr(self.dialog, "_layer_positions_y", [])

        for i, item in enumerate(drag_start_order):
            if i < len(layer_positions_y):
                item.setPos(item.x(), layer_positions_y[i])
            item.set_visual_state(LogicNodeItem.STATE_NORMAL)

        self.dialog._current_logic_layer_order = list(drag_start_order)
        self.dialog._is_dragging_logic = False
        self.dialog._dragged_logic_item = None
        self.dialog._pending_logic_layer_idx = None
        self.dialog._rebuild_tree_from_heights()
        self.dialog.txt_expression.setPlainText(logic_tree.to_string(self.dialog._tree_root))
        self.dialog._refresh_display()

    def handle_mouse_release(self, event) -> bool:
        if self.dialog._is_dragging_logic and event.button() == Qt.MouseButton.LeftButton:
            self.dialog._logic_hover_timer.stop()

            if self.dialog._ghost_logic_item and self.dialog._ghost_logic_item.scene() == self.dialog.graphics_scene:
                self.dialog.graphics_scene.removeItem(self.dialog._ghost_logic_item)
                self.dialog._ghost_logic_item = None

            target_layer = self.calc_layer_idx(event.scenePos().y())
            drag_start_order = getattr(self.dialog, "_drag_start_logic_order", [])
            candidate_order = [item for item in drag_start_order if item != self.dialog._dragged_logic_item]
            target_layer = max(0, min(len(candidate_order), target_layer))
            candidate_order.insert(target_layer, self.dialog._dragged_logic_item)

            apply_order = candidate_order
            layer_positions_y = getattr(self.dialog, "_layer_positions_y", [])

            for i, item in enumerate(apply_order):
                if i < len(layer_positions_y):
                    # [設計不可變] 放開後的最終位置只更新 Y，X 保持不變。
                    item.setPos(item.x(), layer_positions_y[i])
                item.set_visual_state(LogicNodeItem.STATE_NORMAL)

            self.dialog._current_logic_layer_order = list(apply_order)
            self.dialog._is_dragging_logic = False
            self.dialog._dragged_logic_item = None
            self.dialog._pending_logic_layer_idx = None
            self.dialog._rebuild_tree_from_heights()
            self.dialog.txt_expression.setPlainText(logic_tree.to_string(self.dialog._tree_root))
            self.dialog._refresh_display()
            return True

        if self.dialog._is_dragging and event.button() == Qt.MouseButton.LeftButton:
            self.dialog._hover_timer.stop()

            if self.dialog._ghost_item and self.dialog._ghost_item.scene() == self.dialog.graphics_scene:
                self.dialog.graphics_scene.removeItem(self.dialog._ghost_item)
                self.dialog._ghost_item = None

            # [設計不可變] Rule 放開只更新 slot 排列，不改變 Logic 節點位置，AST 拓撲不變。
            target_slot = self.calc_slot_idx(event.scenePos().x())
            drag_start_order = getattr(self.dialog, "_drag_start_order", [])
            candidate_order = [item for item in drag_start_order if item != self.dialog._dragged_item]
            target_slot = max(0, min(len(candidate_order), target_slot))
            candidate_order.insert(target_slot, self.dialog._dragged_item)

            apply_order = candidate_order
            slot_positions = getattr(self.dialog, "_slot_positions", [])

            for i, item in enumerate(apply_order):
                if i < len(slot_positions):
                    item.setPos(slot_positions[i])
                item.set_visual_state(RuleNodeItem.STATE_NORMAL)

            self.dialog._current_slot_order = list(apply_order)
            self.dialog._is_dragging = False
            self.dialog._dragged_item = None
            self.dialog._pending_slot_idx = None
            self.dialog._rebuild_tree_from_heights()
            self.dialog.txt_expression.setPlainText(logic_tree.to_string(self.dialog._tree_root))
            self.dialog._refresh_display()
            return True

        return False

    def handle_key_press(self, event) -> bool:
        if event.key() == Qt.Key.Key_Escape:
            if self.dialog._is_dragging_logic:
                self.cancel_logic_drag()
                return True
            if self.dialog._is_dragging:
                self.cancel_drag()
                return True
        return False
