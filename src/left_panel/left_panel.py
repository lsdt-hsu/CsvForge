import os
import sys
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QWidget, QPushButton,
    QStackedWidget, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

from ui_constants import (
    SIDEBAR_FULL_WIDTH,
    SIDEBAR_MIN_WIDTH,
    SIDEBAR_WIDTH,
    ACTIVITY_BAR_WIDTH,
)
from settings_manager import SidePanelConfig, MainConfig
from translation import PanelClass as TranslationPanel
from ai import PanelClass as AiPanel
from edit import PanelClass as EditPanel
from filter import PanelClass as FilterPanel

from .plugin_manager import PluginManager, PluginWarning, PluginError
from .plugin_ui import create_add_plugin_icon, create_plugin_button
from plugin_sdk import PluginContext, BasePluginPanel
from plugin_sdk.host_adapter import PluginHostAdapter

# 內建面板的 UUID 集合
BUILTIN_UUIDS = {
    "c7a10787-8df1-4340-974a-4e6f47721867",  # translate
    "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",  # filter
    "4e47a9e3-8287-48f8-b39f-26b669fcf72a",  # edit
    "8f521c7d-3047-4929-873b-eb8df0b5c1a7"   # ai
}


class LeftPanel(QFrame):
    plugin_removed = pyqtSignal(str)
    settings_save_requested = pyqtSignal()

    def __init__(self, parent=None, context=None):
        super().__init__(parent)
        self.main_window = parent
        self.context = context
        self.plugin_context = PluginContext(self.context.csv_data) if self.context else None
        self.plugin_manager = PluginManager(context=self.plugin_context)
        self._plugin_buttons = {}
        self._loaded_plugins = []  # 儲存 (plugin_key, path) 元組，維護外掛載入順序
        self.setObjectName("leftContainer")
        self.setFixedWidth(SIDEBAR_FULL_WIDTH)
        self.init_ui()

    def create_ai_icon(self) -> QIcon:
        """
        在執行期使用 QPainter 動態繪製一個簡約、精美的高解析度 AI 文字圖標，
        避免依賴外部 PNG 資源，防範資源遺失造成的崩潰。
        """
        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        font = QFont("Arial")
        font.setPointSize(16)
        font.setBold(True)
        
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "AI")
        painter.end()

        icon = QIcon()
        icon.addPixmap(pixmap, QIcon.Mode.Normal, QIcon.State.Off)
        icon.addPixmap(pixmap, QIcon.Mode.Normal, QIcon.State.On)
        icon.addPixmap(pixmap, QIcon.Mode.Active)
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

        # 註解：過濾面板是第一個功能，不得任意變更。
        # 過濾按鈕
        filter_icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "filter.png"
        )
        self.btn_filter = QPushButton()
        self.btn_filter.setObjectName("btnActivityFilter")
        self.btn_filter.setProperty("type", "activity")
        self.btn_filter.setFixedSize(40, 40)
        self.btn_filter.setIcon(QIcon(filter_icon_path))
        self.btn_filter.setIconSize(QSize(40, 40))
        self.btn_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_filter.clicked.connect(lambda: self.switch_sidebar_tab("filter"))
        self.btn_filter.setProperty("active", True)
        activity_layout.addWidget(self.btn_filter)

        # 翻譯按鈕
        translate_icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "translate.png"
        )
        self.btn_translate = QPushButton()
        self.btn_translate.setObjectName("btnActivityTranslate")
        self.btn_translate.setProperty("type", "activity")
        self.btn_translate.setFixedSize(40, 40)
        self.btn_translate.setIcon(QIcon(translate_icon_path))
        self.btn_translate.setIconSize(QSize(40, 40))
        self.btn_translate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_translate.clicked.connect(lambda: self.switch_sidebar_tab("translate"))
        self.btn_translate.setProperty("active", False)
        activity_layout.addWidget(self.btn_translate)

        # AI 按鈕
        self.btn_ai = QPushButton()
        self.btn_ai.setObjectName("btnActivityAi")
        self.btn_ai.setProperty("type", "activity")
        self.btn_ai.setFixedSize(40, 40)
        self.btn_ai.setIcon(self.create_ai_icon())
        self.btn_ai.setIconSize(QSize(40, 40))
        self.btn_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ai.clicked.connect(lambda: self.switch_sidebar_tab("ai"))
        self.btn_ai.setProperty("active", False)
        activity_layout.addWidget(self.btn_ai)

        # 編輯按鈕
        edit_icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "edit.png"
        )
        self.btn_edit = QPushButton()
        self.btn_edit.setObjectName("btnActivityEdit")
        self.btn_edit.setProperty("type", "activity")
        self.btn_edit.setFixedSize(40, 40)
        self.btn_edit.setIcon(QIcon(edit_icon_path))
        self.btn_edit.setIconSize(QSize(40, 40))
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit.clicked.connect(lambda: self.switch_sidebar_tab("edit"))
        self.btn_edit.setProperty("active", False)
        activity_layout.addWidget(self.btn_edit)

        # 添加外掛 (圓圈+) 按鈕
        self.btn_add_plugin = QPushButton()
        self.btn_add_plugin.setObjectName("btnActivityAddPlugin")
        self.btn_add_plugin.setProperty("type", "activity")
        self.btn_add_plugin.setFixedSize(40, 40)
        self.btn_add_plugin.setIcon(create_add_plugin_icon())
        self.btn_add_plugin.setIconSize(QSize(40, 40))
        self.btn_add_plugin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_plugin.clicked.connect(self.on_add_plugin_clicked)
        activity_layout.addWidget(self.btn_add_plugin)

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
        
        # 註解：過濾面板是第一個功能，不得任意變更。
        # 實例化各個 Package 的 Panel 並註冊 (側面板按鈕對應關係)
        self.add_panel("filter", FilterPanel(context=self.plugin_context))
        self.add_panel("translate", TranslationPanel(context=self.plugin_context))
        self.add_panel("ai", AiPanel(context=self.plugin_context))
        self.add_panel("edit", EditPanel(context=self.plugin_context))

    def add_panel(self, name: str, panel: BasePluginPanel) -> None:
        """接受實體 Panel，立刻封裝為 PluginHostAdapter 再存入 _panels。"""
        adapter = PluginHostAdapter(panel)
        self._panels[name] = adapter
        self.sidebar_stacked.addWidget(adapter.get_widget())
        self._connect_panel_signals(adapter)
        adapter.initialize()

    def _connect_panel_signals(self, adapter: PluginHostAdapter) -> None:
        """從 Adapter 取得內部實體面板，整批連接私有通訊信號到主程式對應槽函數。
        此處呼叫 adapter.get_panel() 是系統中唯一合法的使用點。"""
        if self.main_window:
            panel = adapter.get_panel()
            panel._request_lock_ui.connect(self.main_window.lock_ui_from_panel)
            panel._progress_updated.connect(self.main_window.on_panel_progress)
            panel._status_updated.connect(self.main_window.on_panel_status)
            panel._log_emitted.connect(self.main_window.on_panel_log)
            panel._task_started.connect(self.main_window.on_task_started)
            panel._task_finished.connect(self.main_window.on_task_finished)
            panel._request_silent_save.connect(self.main_window.silent_save_edit_data)
            # Worker 生命週期委託：面板的 api.run_worker() 呼叫將觸發此信號，
            # 由 Adapter 統一建立 QThread 並管理 Worker GC
            panel._request_run_worker.connect(adapter._on_run_worker_requested)

    def get_active_plugin(self) -> PluginHostAdapter:
        """
        公開方法：取得當前活躍的外掛/功能面板的 PluginHostAdapter。
        主程式與其他模組僅能透過此方法取得當前 active plugin，嚴禁直接存取 _panels 或 sidebar_stacked。
        回傳值為 PluginHostAdapter，徹底阻斷主程式直接存取實體 Panel 的可能。
        """
        widget = self.sidebar_stacked.currentWidget()
        for adapter in self._panels.values():
            if adapter.get_widget() is widget:
                return adapter
        return None

    def get_plugin(self, name: str) -> PluginHostAdapter:
        """
        公開方法：根據名稱取得對應面板的 PluginHostAdapter。
        """
        return self._panels.get(name)

    def restore_panel_states(self, configs: dict) -> None:
        """
        公開方法：還原所有面板的 UI 設定。
        """
        for name, adapter in self._panels.items():
            try:
                uuid_str = adapter.get_uuid()
                if uuid_str in BUILTIN_UUIDS:
                    pkg_name = adapter.get_package_name()
                else:
                    pkg_name = f"PLUGIN-{uuid_str}"
            except Exception:
                pkg_name = adapter.get_package_name()

            if pkg_name in configs:
                try:
                    adapter.deserialize_config(configs[pkg_name])
                except Exception:
                    pass

    def save_panel_states(self, configs: dict) -> None:
        """
        公開方法：保存所有面板的最新設定到 configs。
        """
        for name, adapter in self._panels.items():
            try:
                uuid_str = adapter.get_uuid()
                if uuid_str in BUILTIN_UUIDS:
                    pkg_name = adapter.get_package_name()
                else:
                    pkg_name = f"PLUGIN-{uuid_str}"
            except Exception:
                pkg_name = adapter.get_package_name()

            try:
                configs[pkg_name] = adapter.serialize_config()
            except Exception:
                pass

    def switch_sidebar_tab(self, tab_name: str, force_expand: bool = False) -> None:
        current_panel = self._panels.get(tab_name)
        is_same_tab = False
        if current_panel and self.sidebar_stacked.currentWidget() == current_panel.get_widget():
            is_same_tab = True

        # Check UI lock
        if not force_expand:
            if self.main_window and self.main_window.is_ui_locked:
                return

            is_task_running = self.main_window and self.main_window.is_any_task_running()

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
            for btn in self._plugin_buttons.values():
                btn.setProperty("active", False)
        else:
            # 展開並切換
            self.sidebar.setVisible(True)
            self.v_line.setVisible(True)
            self.setFixedWidth(SIDEBAR_FULL_WIDTH)

            if current_panel:
                self.sidebar_stacked.setCurrentWidget(current_panel.get_widget())
            
            # 設定按鈕 active 狀態
            self.btn_filter.setProperty("active", tab_name == "filter")
            self.btn_translate.setProperty("active", tab_name == "translate")
            self.btn_ai.setProperty("active", tab_name == "ai")
            self.btn_edit.setProperty("active", tab_name == "edit")
            for p_key, btn in self._plugin_buttons.items():
                btn.setProperty("active", tab_name == p_key)

        # 刷新按鈕樣式
        self.btn_translate.style().polish(self.btn_translate)
        self.btn_ai.style().polish(self.btn_ai)
        self.btn_edit.style().polish(self.btn_edit)
        self.btn_filter.style().polish(self.btn_filter)
        for btn in self._plugin_buttons.values():
            btn.style().polish(btn)

    def apply_config(self, side_cfg: SidePanelConfig, main_cfg: MainConfig) -> None:
        # 啟動時先依序載入外掛
        if hasattr(side_cfg, "plugins") and side_cfg.plugins:
            for path in side_cfg.plugins:
                self.load_plugin_by_path(path, auto_save=False)

        if side_cfg.collapsed:
            self.sidebar.setVisible(False)
            self.v_line.setVisible(False)
            self.setFixedWidth(SIDEBAR_MIN_WIDTH)
            self.btn_translate.setProperty("active", False)
            self.btn_ai.setProperty("active", False)
            self.btn_edit.setProperty("active", False)
            self.btn_filter.setProperty("active", False)
            for btn in self._plugin_buttons.values():
                btn.setProperty("active", False)
        else:
            self.switch_sidebar_tab(main_cfg.active_tab, force_expand=True)

    def update_config(self, side_cfg: SidePanelConfig, main_cfg: MainConfig) -> None:
        side_cfg.collapsed = not self.sidebar.isVisible()
        side_cfg.plugins = [path for _, path in self._loaded_plugins]
        side_cfg.dirty = True

        current_widget = self.sidebar_stacked.currentWidget()
        active_tab = "filter"
        for name, adapter in self._panels.items():
            if current_widget == adapter.get_widget():
                active_tab = name
                break
        main_cfg.active_tab = active_tab
        main_cfg.dirty = True

    def set_enabled(self, enabled: bool) -> None:
        self.btn_translate.setEnabled(enabled)
        self.btn_ai.setEnabled(enabled)
        self.btn_edit.setEnabled(enabled)
        self.btn_filter.setEnabled(enabled)
        self.btn_add_plugin.setEnabled(enabled)
        for btn in self._plugin_buttons.values():
            btn.setEnabled(enabled)
            # 同步設定圓圈減按鈕的狀態
            for child in btn.findChildren(QPushButton):
                child.setEnabled(enabled)
        for adapter in self._panels.values():
            adapter.set_enabled(enabled)

    # ── 外掛相關繪圖與動態載入邏輯 ───────────────────────────────────────────────


    def on_add_plugin_clicked(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "選擇外掛資料夾")
        if path:
            self.load_plugin_by_path(path, auto_save=True)

    def load_plugin_by_path(self, path: str, auto_save: bool = True) -> bool:
        path = os.path.normpath(path)
        
        # 取得現有面板 UUID 集合
        existing_uuids = {a.get_uuid() for a in self._panels.values()}

        try:
            plugin_key, panel = self.plugin_manager.load_plugin(path, existing_uuids)
        except PluginWarning as w:
            if auto_save:
                QMessageBox.warning(self, "警告", str(w))
            return False
        except PluginError as e:
            if auto_save:
                QMessageBox.critical(self, "錯誤", str(e))
            return False

        # 封裝為 PluginHostAdapter 並註冊
        adapter = PluginHostAdapter(panel)
        uuid_str = adapter.get_uuid()
        self._panels[plugin_key] = adapter
        self.sidebar_stacked.addWidget(adapter.get_widget())

        # 建立活動列按鈕與圓圈減移除按鈕
        btn = create_plugin_button(
            parent_widget=self,
            uuid_str=uuid_str,
            icon=adapter.get_icon(),
            on_click=lambda: self.switch_sidebar_tab(plugin_key),
            on_remove_click=lambda: self.remove_plugin(plugin_key)
        )

        # 將按鈕插入到活動列（圓圈+按鈕的前面）
        layout = self.activity_bar.layout()
        idx = layout.indexOf(self.btn_add_plugin)
        if idx != -1:
            layout.insertWidget(idx, btn)
        else:
            layout.addWidget(btn)

        # 整批連接標準私有信號
        self._connect_panel_signals(adapter)

        # 初始資料狀態同步
        adapter.initialize()

        self._plugin_buttons[plugin_key] = btn
        self._loaded_plugins.append((plugin_key, path))

        # 更新設定檔中的外掛路徑
        if self.context and self.context.side_panel_config:
            self.context.side_panel_config.plugins = [p for _, p in self._loaded_plugins]
            self.context.side_panel_config.dirty = True

        if auto_save:
            self.settings_save_requested.emit()

        return True

    def remove_plugin(self, plugin_key: str) -> None:
        reply = QMessageBox.question(
            self, "確認移除", "確定要移除該 plugin 外掛嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        path, panel = self.plugin_manager.remove_plugin(plugin_key)

        # 從 _panels 移除 Adapter（實體 panel 從 Adapter 取得）
        adapter = self._panels.pop(plugin_key, None)
        if adapter:
            panel = adapter.get_panel()
            if self.sidebar_stacked.currentWidget() is panel:
                self.switch_sidebar_tab("filter", force_expand=True)
            self.sidebar_stacked.removeWidget(panel)

            # 防止信號記憶體洩漏與懸空信號：呼叫 adapter.cleanup() 進行統一清理
            try:
                adapter.cleanup()
            except Exception:
                pass

            panel.deleteLater()

        btn = self._plugin_buttons.pop(plugin_key, None)
        if btn:
            self.activity_bar.layout().removeWidget(btn)
            btn.deleteLater()

        # 自載入列表中移除
        self._loaded_plugins = [item for item in self._loaded_plugins if item[0] != plugin_key]

        # 更新設定檔記憶體
        if self.context and self.context.side_panel_config:
            self.context.side_panel_config.plugins = [p for _, p in self._loaded_plugins]
            self.context.side_panel_config.dirty = True

        self.plugin_removed.emit(plugin_key)
        self.settings_save_requested.emit()
