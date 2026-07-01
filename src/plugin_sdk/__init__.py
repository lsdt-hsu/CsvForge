# src/plugin_sdk/__init__.py
from plugin_sdk.context import PluginContext
from plugin_sdk.panel_base import BasePluginPanel
from plugin_sdk.plugin_api import PluginAPI
# 注意：PluginHostAdapter 刻意不在此處 export，
# 防止外掛開發者誤用。LeftPanel 應直接從 plugin_sdk.host_adapter import。
