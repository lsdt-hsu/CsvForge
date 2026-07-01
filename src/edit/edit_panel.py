# src/edit/edit_panel.py
from plugin_sdk.panel_base import BasePluginPanel
from plugin_sdk.theme import applyHintLabel
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt


class EditPanel(BasePluginPanel):
    def __init__(self, parent=None, context=None):
        super().__init__(parent, title_text="編輯(施工中)", require_data_loading=False, context=context)

    def _internal_get_package_name(self) -> str:
        return "edit_panel"

    def _internal_get_uuid(self) -> str:
        return "4e47a9e3-8287-48f8-b39f-26b669fcf72a"

    def _internal_serialize_config(self) -> dict:
        return {}

    def _internal_deserialize_config(self, data: dict) -> None:
        pass
