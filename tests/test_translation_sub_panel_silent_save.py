import unittest
from unittest.mock import MagicMock
import sys
import os

# 將 src 目錄加入 sys.path 以方便匯入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from PyQt6.QtWidgets import QApplication
from common_data.task_status import TaskStatus
from translation.single_translation_sub_panel import SingleTranslationSubPanel
from translation.batch_translation_sub_panel import BatchTranslationSubPanel

app = QApplication.instance() or QApplication(sys.argv)


class TestTranslationSubPanelSilentSave(unittest.TestCase):

    def setUp(self):
        self.api_mock = MagicMock()
        self.context_mock = MagicMock()

    def test_single_translation_sub_panel_silent_save_unconditional(self):
        # 測試單筆翻譯面板在任何狀態下（包含 None、TaskStatus、未知字串等）結束時，皆會觸發靜默存檔
        for status in [TaskStatus.CANCELLED, TaskStatus.FINISHED, TaskStatus.ERROR, None, "custom_status"]:
            with self.subTest(status=status):
                self.api_mock.reset_mock()
                panel = SingleTranslationSubPanel(api=self.api_mock, context=self.context_mock)
                panel._on_worker_done(status)
                self.api_mock.request_silent_save.assert_called_once()

    def test_batch_translation_sub_panel_silent_save_unconditional(self):
        # 測試批次翻譯面板在任何狀態下（包含 None、TaskStatus、未知字串等）結束時，皆會觸發靜默存檔
        for status in [TaskStatus.CANCELLED, TaskStatus.FINISHED, TaskStatus.ERROR, None, "custom_status"]:
            with self.subTest(status=status):
                self.api_mock.reset_mock()
                panel = BatchTranslationSubPanel(api=self.api_mock, context=self.context_mock)
                panel._on_worker_done(status)
                self.api_mock.request_silent_save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
