from PyQt6.QtWidgets import QLabel
from plugin_sdk import theme
from edit.base_sub_panel import BaseSubPanel

class SingleTranslationSubPanel(BaseSubPanel):
    """
    單筆翻譯子面板
    目前暫時為空，預留未來擴充單筆翻譯功能。
    """

    def __init__(self, api, context, parent=None):
        super().__init__("單筆翻譯", api, context, parent)
        self._setup_ui()

    def _setup_ui(self):
        self.lbl_empty = QLabel("單筆翻譯功能開發中...")
        theme.applyStandardLabelStyle(self.lbl_empty)
        self.content_layout.addWidget(self.lbl_empty)

    def get_config(self) -> dict:
        return {}

    def restore_config(self, data: dict) -> None:
        pass

    def on_data_refreshed(self) -> None:
        pass

    def set_panel_enabled(self, global_enabled: bool) -> None:
        pass
