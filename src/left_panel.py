import os
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QStackedWidget
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

from ui_constants import (
    SIDEBAR_FULL_WIDTH,
    SIDEBAR_MIN_WIDTH,
    SIDEBAR_WIDTH,
    ACTIVITY_BAR_WIDTH,
)
from settings_manager import SidePanelConfig, MainConfig


class LeftPanel(QFrame):

    def __init__(self, parent=None, context=None):
        super().__init__(parent)
        self.context = context
        self.setObjectName("leftContainer")
        self.setFixedWidth(SIDEBAR_FULL_WIDTH)
        self.init_ui()

    def create_ai_icon(self) -> QIcon:
        """
        在執行期使用 QPainter 動態繪製一個簡約、精美的高解析度 AI 文字圖標，
        避免依賴外部 PNG 資源，防範資源遺失造成的崩潰。
        """
        # 1. 繪製正常 (Inactive) 狀態
        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#7aa2f7"))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(2, 2, 36, 36, 6, 6)
        
        font = QFont("Arial")
        font.setPointSize(12)
        font.setBold(True)
        
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "AI")
        painter.end()

        # 2. 繪製 Active 狀態
        pixmap_active = QPixmap(40, 40)
        pixmap_active.fill(Qt.GlobalColor.transparent)
        
        painter_act = QPainter(pixmap_active)
        painter_act.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter_act.setPen(QColor("#2ac3de"))
        painter_act.setBrush(Qt.BrushStyle.NoBrush)
        painter_act.drawRoundedRect(2, 2, 36, 36, 6, 6)
        
        painter_act.setFont(font)
        painter_act.drawText(pixmap_active.rect(), Qt.AlignmentFlag.AlignCenter, "AI")
        painter_act.end()

        icon = QIcon()
        icon.addPixmap(pixmap, QIcon.Mode.Normal, QIcon.State.Off)
        icon.addPixmap(pixmap_active, QIcon.Mode.Normal, QIcon.State.On)
        icon.addPixmap(pixmap_active, QIcon.Mode.Active)
        return icon

    def init_ui(self):
        left_layout = QHBoxLayout(self)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # 1. 活動列 (QWidget)
        self.activity_bar = QWidget()
        self.activity_bar.setObjectName("activityBarWidget")
        self.activity_bar.setFixedWidth(ACTIVITY_BAR_WIDTH)

        activity_layout = QVBoxLayout(self.activity_bar)
        activity_layout.setContentsMargins(10, 15, 10, 15)
        activity_layout.setSpacing(10)
        activity_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 翻譯按鈕
        translate_icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "translate.png"
        )
        self.btn_translate = QPushButton()
        self.btn_translate.setObjectName("btnActivityTranslate")
        self.btn_translate.setFixedSize(40, 40)
        self.btn_translate.setIcon(QIcon(translate_icon_path))
        self.btn_translate.setIconSize(QSize(40, 40))
        self.btn_translate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_translate.clicked.connect(lambda: self.switch_sidebar_tab("translate"))
        self.btn_translate.setProperty("active", True)
        activity_layout.addWidget(self.btn_translate)

        # AI 按鈕
        self.btn_ai = QPushButton()
        self.btn_ai.setObjectName("btnActivityAi")
        self.btn_ai.setFixedSize(40, 40)
        self.btn_ai.setIcon(self.create_ai_icon())
        self.btn_ai.setIconSize(QSize(40, 40))
        self.btn_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ai.clicked.connect(lambda: self.switch_sidebar_tab("ai"))
        self.btn_ai.setProperty("active", False)
        activity_layout.addWidget(self.btn_ai)

        # 編輯按鈕
        edit_icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "edit.png"
        )
        self.btn_edit = QPushButton()
        self.btn_edit.setObjectName("btnActivityEdit")
        self.btn_edit.setFixedSize(40, 40)
        self.btn_edit.setIcon(QIcon(edit_icon_path))
        self.btn_edit.setIconSize(QSize(40, 40))
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit.clicked.connect(lambda: self.switch_sidebar_tab("edit"))
        self.btn_edit.setProperty("active", False)
        activity_layout.addWidget(self.btn_edit)

        # 過濾按鈕
        filter_icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "filter.png"
        )
        self.btn_filter = QPushButton()
        self.btn_filter.setObjectName("btnActivityFilter")
        self.btn_filter.setFixedSize(40, 40)
        self.btn_filter.setIcon(QIcon(filter_icon_path))
        self.btn_filter.setIconSize(QSize(40, 40))
        self.btn_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_filter.clicked.connect(lambda: self.switch_sidebar_tab("filter"))
        self.btn_filter.setProperty("active", False)
        activity_layout.addWidget(self.btn_filter)

        activity_layout.addStretch()
        left_layout.addWidget(self.activity_bar)

        # 2. 垂直分割線 (QWidget)
        self.v_line = QWidget()
        self.v_line.setObjectName("sidebarSeparator")
        self.v_line.setFixedWidth(1)
        left_layout.addWidget(self.v_line)

        # 3. 側邊欄 (QWidget)
        self.sidebar = QWidget()
        self.sidebar.setObjectName("leftSidebarWidget")
        self.sidebar.setFixedWidth(SIDEBAR_WIDTH)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 15, 15, 15)
        sidebar_layout.setSpacing(15)

        self.sidebar_stacked = QStackedWidget()
        sidebar_layout.addWidget(self.sidebar_stacked, stretch=1)
        left_layout.addWidget(self.sidebar)

        self._panels = {}

    def add_panel(self, name: str, panel: QWidget) -> None:
        self._panels[name] = panel
        self.sidebar_stacked.addWidget(panel)

    def switch_sidebar_tab(self, tab_name: str, force_expand: bool = False) -> None:
        # Check UI lock
        if getattr(self.parent(), "is_ui_locked", False):
            return

        is_task_running = getattr(self.parent(), "worker", None) is not None and self.parent().worker.isRunning()

        # 判斷點選的是否為當前活躍的分頁
        is_same_tab = False
        current_panel = self._panels.get(tab_name)
        if current_panel and self.sidebar_stacked.currentWidget() == current_panel:
            is_same_tab = True

        # 任務執行中禁止切換至其他功能面板
        if is_task_running and not is_same_tab:
            return

        if not force_expand and self.sidebar.isVisible() and is_same_tab:
            # 收合
            self.sidebar.setVisible(False)
            self.v_line.setVisible(False)
            self.setFixedWidth(SIDEBAR_MIN_WIDTH)
            self.btn_translate.setProperty("active", False)
            self.btn_ai.setProperty("active", False)
            self.btn_edit.setProperty("active", False)
            self.btn_filter.setProperty("active", False)
        else:
            # 展開並切換
            self.sidebar.setVisible(True)
            self.v_line.setVisible(True)
            self.setFixedWidth(SIDEBAR_FULL_WIDTH)

            if current_panel:
                self.sidebar_stacked.setCurrentWidget(current_panel)
            
            if tab_name == "translate":
                self.btn_translate.setProperty("active", True)
                self.btn_ai.setProperty("active", False)
                self.btn_edit.setProperty("active", False)
                self.btn_filter.setProperty("active", False)
            elif tab_name == "ai":
                self.btn_translate.setProperty("active", False)
                self.btn_ai.setProperty("active", True)
                self.btn_edit.setProperty("active", False)
                self.btn_filter.setProperty("active", False)
            elif tab_name == "edit":
                self.btn_translate.setProperty("active", False)
                self.btn_ai.setProperty("active", False)
                self.btn_edit.setProperty("active", True)
                self.btn_filter.setProperty("active", False)
            elif tab_name == "filter":
                self.btn_translate.setProperty("active", False)
                self.btn_ai.setProperty("active", False)
                self.btn_edit.setProperty("active", False)
                self.btn_filter.setProperty("active", True)

        # 刷新按鈕樣式
        self.btn_translate.style().polish(self.btn_translate)
        self.btn_ai.style().polish(self.btn_ai)
        self.btn_edit.style().polish(self.btn_edit)
        self.btn_filter.style().polish(self.btn_filter)

    def apply_config(self, side_cfg: SidePanelConfig, main_cfg: MainConfig) -> None:
        if side_cfg.collapsed:
            self.sidebar.setVisible(False)
            self.v_line.setVisible(False)
            self.setFixedWidth(SIDEBAR_MIN_WIDTH)
            self.btn_translate.setProperty("active", False)
            self.btn_ai.setProperty("active", False)
            self.btn_edit.setProperty("active", False)
            self.btn_filter.setProperty("active", False)
        else:
            self.switch_sidebar_tab(main_cfg.active_tab, force_expand=True)

    def update_config(self, side_cfg: SidePanelConfig, main_cfg: MainConfig) -> None:
        side_cfg.collapsed = not self.sidebar.isVisible()
        side_cfg.dirty = True

        current_widget = self.sidebar_stacked.currentWidget()
        if current_widget == self._panels.get("translate"):
            active_tab = "translate"
        elif current_widget == self._panels.get("ai"):
            active_tab = "ai"
        elif current_widget == self._panels.get("filter"):
            active_tab = "filter"
        else:
            active_tab = "edit"
        main_cfg.active_tab = active_tab
        main_cfg.dirty = True

    def set_enabled(self, enabled: bool) -> None:
        self.btn_translate.setEnabled(enabled)
        self.btn_ai.setEnabled(enabled)
        self.btn_edit.setEnabled(enabled)
        self.btn_filter.setEnabled(enabled)
        for panel in self._panels.values():
            if hasattr(panel, "set_enabled"):
                panel.set_enabled(enabled)
