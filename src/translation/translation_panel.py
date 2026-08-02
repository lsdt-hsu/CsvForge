"""
translation_panel.py — 翻譯面板容器

架構參考 edit_panel.py：
本面板繼承 BasePluginPanel 作為外掛容器，內部包含並維護兩個子面板：
1. SingleTranslationSubPanel ("單筆翻譯")
2. BatchTranslationSubPanel ("批次翻譯")

同一時間僅允許展開一個子面板，展開事件由 _on_sub_panel_expanded 進行互斥處理。
"""

from PyQt6.QtWidgets import QScrollArea, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

from plugin_sdk.panel_base import BasePluginPanel
from translation.single_translation_sub_panel import SingleTranslationSubPanel
from translation.batch_translation_sub_panel import BatchTranslationSubPanel


class TranslationPanel(BasePluginPanel):
    _UUID = "c7a10787-8df1-4340-974a-4e6f47721867"
    _N_NON_COL_OPTIONS = 0

    def __init__(self, parent=None, context=None):
        super().__init__(
            parent=parent,
            title_text="翻譯",
            require_data_loading=True,
            context=context,
        )
        # 用於儲存註冊的子面板清單，格式為 (config_key, panel_instance)
        self.sub_panels = []
        self._setup_ui()

    def _setup_ui(self):
        # 1. 建立可捲動容器 (防止未來子面板過多超出螢幕)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 消除預設邊框與背景色
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.viewport().setStyleSheet("background: transparent;")

        inner = QWidget()
        self.inner_layout = QVBoxLayout(inner)
        self.inner_layout.setContentsMargins(0, 0, 0, 0)

        # 2. 註冊子面板
        self._register_sub_panel("single", SingleTranslationSubPanel(self.api, self.context))
        self._register_sub_panel("batch", BatchTranslationSubPanel(self.api, self.context))

        # 3. 彈性推頂
        self.inner_layout.addStretch()

        scroll.setWidget(inner)
        self.controls_layout.addWidget(scroll)

    def _register_sub_panel(self, key: str, panel):
        """將子面板加入容器，並綁定展開事件以實作互斥收合"""
        panel.expanded.connect(self._on_sub_panel_expanded)
        self.sub_panels.append((key, panel))
        self.inner_layout.addWidget(panel)

    def _on_sub_panel_expanded(self, expanded_panel):
        """當某個面板展開時，強制收合其他面板"""
        for _, panel in self.sub_panels:
            if panel is not expanded_panel:
                panel.force_collapse()

    def on_csv_data_refreshed(self) -> None:
        """事件廣播：資料刷新"""
        for _, panel in self.sub_panels:
            panel.on_data_refreshed()

    def _internal_get_package_name(self) -> str:
        return "translate_panel"

    def _internal_get_uuid(self) -> str:
        return self._UUID

    def _internal_serialize_config(self) -> dict:
        """分發 Config：將各子面板的設定打包成一個大 dict"""
        config = {}
        for key, panel in self.sub_panels:
            config[key] = panel.get_config()
        return config

    def _internal_deserialize_config(self, data: dict) -> None:
        """分發 Config：將對應的設定還原給各子面板，支援舊版格式向下相容"""
        for key, panel in self.sub_panels:
            if key in data:
                panel.restore_config(data.get(key, {}))
            elif key == "batch":
                # 相容舊版直接存在根節點的批次翻譯設定
                panel.restore_config(data)
            else:
                panel.restore_config({})

    def _internal_set_enabled(self, enabled: bool) -> None:
        """事件廣播：全域 UI 鎖定/解鎖"""
        super()._internal_set_enabled(enabled)
        for _, panel in self.sub_panels:
            panel.set_panel_enabled(enabled)

    def _internal_is_task_running(self) -> bool:
        """點擊主介面或切換標籤頁時查詢任務是否在執行中"""
        for _, panel in self.sub_panels:
            if getattr(panel, "_worker", None) is not None:
                return True
        return False

    def _internal_cancel_task(self) -> None:
        """主程式進行取消時傳遞至各子面板"""
        for _, panel in self.sub_panels:
            worker = getattr(panel, "_worker", None)
            if worker is not None:
                worker.cancel()
