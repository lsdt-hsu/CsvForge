import os
import sys
import importlib.util

class PluginWarning(Exception):
    """外掛警告，對應 UI 的 warning 彈窗"""
    pass

class PluginError(Exception):
    """外掛嚴重錯誤，對應 UI 的 critical 彈窗"""
    pass

class PluginManager:
    def __init__(self, context=None):
        self.context = context
        self._plugins = {}  # {plugin_key: (path, panel_instance)}

    def load_plugin(self, path: str, existing_uuids: set) -> tuple:
        """
        嘗試從指定路徑載入外掛。
        成功時回傳 (plugin_key, panel_instance)
        失敗時拋出 PluginWarning 或 PluginError
        """
        path = os.path.normpath(path)
        
        # 1. 檢查重複路徑
        for p_key, (existing_path, _) in self._plugins.items():
            if existing_path == path:
                raise PluginWarning("該外掛路徑已在載入列表中。")

        if not os.path.exists(path):
            raise PluginWarning(f"找不到路徑: {path}")

        entry_file = os.path.join(path, "plugin.py")
        if not os.path.exists(entry_file):
            raise PluginWarning("在選擇的資料夾中找不到標準入口檔 `plugin.py`。")

        try:
            if path not in sys.path:
                sys.path.insert(0, path)

            spec = importlib.util.spec_from_file_location("plugin_module", entry_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            panel_class = getattr(module, "PanelClass", None)
            if not panel_class:
                raise PluginWarning("外掛入口檔 `plugin.py` 中找不到 `PanelClass` 類別。")

            panel = panel_class(context=self.context)
        except PluginWarning:
            raise
        except Exception as e:
            raise PluginError(f"載入外掛時發生錯誤：\n{str(e)}")

        uuid_str = panel.get_uuid()
        if uuid_str in existing_uuids:
            panel.deleteLater()
            raise PluginError(f"外掛 UUID 重複，拒絕載入。\n重複的 UUID: {uuid_str}")

        plugin_key = f"PLUGIN-{uuid_str}"
        self._plugins[plugin_key] = (path, panel)
        return plugin_key, panel

    def remove_plugin(self, plugin_key: str) -> tuple:
        """
        移除指定的外掛。
        回傳 (path, panel_instance) 或 (None, None)
        """
        item = self._plugins.pop(plugin_key, None)
        if item:
            return item[0], item[1]
        return None, None
