# src/plugin_sdk/context.py
from common_data.csv_data import CsvData

class PluginContext:
    """
    PluginContext — 提供給外掛面板與功能面板存取 CSV 數據與狀態的解耦上下文。
    與 AppContext 彼此獨立，不繼承，不引用。
    """
    def __init__(self, csv_data: CsvData):
        self._csv_data = csv_data

    @property
    def csv_data(self) -> CsvData:
        return self._csv_data

    @property
    def is_data_loaded(self) -> bool:
        return bool(self._csv_data.all_rows)

    @property
    def is_first_row_header(self) -> bool:
        return self._csv_data.is_header
