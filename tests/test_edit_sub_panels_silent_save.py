import unittest
from unittest.mock import MagicMock
import sys
import os

# 將 src 目錄加入 sys.path 以方便匯入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from PyQt6.QtWidgets import QApplication
from common_data.task_status import TaskStatus
from edit.replace_sub_panel import ReplaceSubPanel
from edit.paste_sub_panel import PasteSubPanel

app = QApplication.instance() or QApplication(sys.argv)


class TestEditSubPanelsSilentSave(unittest.TestCase):

    def setUp(self):
        self.api_mock = MagicMock()
        self.context_mock = MagicMock()
        self.context_mock.csv_data = MagicMock()

    def test_replace_sub_panel_silent_save_unconditional(self):
        for status in [TaskStatus.CANCELLED, TaskStatus.FINISHED, TaskStatus.ERROR, None, "custom_status"]:
            with self.subTest(status=status):
                self.api_mock.reset_mock()
                panel = ReplaceSubPanel(api=self.api_mock, context=self.context_mock)
                panel._on_worker_finished(status)
                self.api_mock.request_silent_save.assert_called_once()
                self.context_mock.csv_data.set_modified.assert_called_with(True)

    def test_paste_sub_panel_silent_save_unconditional(self):
        for status in [TaskStatus.CANCELLED, TaskStatus.FINISHED, TaskStatus.ERROR, None, "custom_status"]:
            with self.subTest(status=status):
                self.api_mock.reset_mock()
                panel = PasteSubPanel(api=self.api_mock, context=self.context_mock)
                panel._on_worker_finished(status)
                self.api_mock.request_silent_save.assert_called_once()
                self.context_mock.csv_data.set_modified.assert_called_with(True)


if __name__ == "__main__":
    unittest.main()
