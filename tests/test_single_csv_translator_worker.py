import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# 將 src 目錄加入 sys.path 以方便匯入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from translation.single_csv_translator_worker import SingleCSVTranslatorWorker
from common_data.task_status import TaskStatus


class TestSingleCSVTranslatorWorker(unittest.TestCase):

    def setUp(self):
        self.all_rows = [
            ["こんにちは \n ", ""],
            ["世界 \r\n ", ""],
            ["", ""],
        ]
        self.visible_indices = [0, 1, 2]

    @patch("translation.single_csv_translator_worker.GoogleTranslator")
    def test_single_translation_success_strip_formatting(self, mock_translator_cls):
        mock_translator = MagicMock()
        mock_translator.translate.side_effect = lambda text: f"  Translated: {text.strip()} \n"
        mock_translator_cls.return_value = mock_translator

        worker = SingleCSVTranslatorWorker(
            all_rows=self.all_rows,
            visible_row_indices=self.visible_indices,
            source_col_idx=0,
            target_col_idx=1,
            source_lang="ja",
            target_lang="zh-TW",
            single_interval=0.0,
            skip_translated=True,
        )

        finished_status = None

        def on_finished(status):
            nonlocal finished_status
            finished_status = status

        worker.finished.connect(on_finished)
        # 覆寫 msleep 以加快測試
        worker.msleep = lambda msecs: None

        worker.run()

        self.assertEqual(finished_status, TaskStatus.FINISHED)
        self.assertEqual(self.all_rows[0][1], "Translated: こんにちは")
        self.assertEqual(self.all_rows[1][1], "Translated: 世界")

    @patch("translation.single_csv_translator_worker.GoogleTranslator")
    def test_single_translation_error_rank_increment_and_skip(self, mock_translator_cls):
        mock_translator = MagicMock()
        # 第一筆報錯，第二筆成功
        mock_translator.translate.side_effect = [
            Exception("Network Timeout"),
            "Hello World\n",
        ]
        mock_translator_cls.return_value = mock_translator

        all_rows = [
            ["Row1 Error", ""],
            ["Row2 OK", ""],
        ]
        worker = SingleCSVTranslatorWorker(
            all_rows=all_rows,
            visible_row_indices=[0, 1],
            source_col_idx=0,
            target_col_idx=1,
            source_lang="en",
            target_lang="zh-TW",
            single_interval=0.0,
            skip_translated=True,
        )

        finished_status = None

        def on_finished(status):
            nonlocal finished_status
            finished_status = status

        worker.finished.connect(on_finished)
        worker.msleep = lambda msecs: None

        worker.run()

        self.assertEqual(finished_status, TaskStatus.FINISHED)
        # 第一筆翻譯失敗未回填，error_rank 從 0 + 5 扣除成功後的 1 = 4
        self.assertEqual(all_rows[0][1], "")
        self.assertEqual(all_rows[1][1], "Hello World")
        self.assertEqual(worker.error_rank, 4)

    @patch("translation.single_csv_translator_worker.GoogleTranslator")
    def test_single_translation_error_rank_reaches_15_aborts(self, mock_translator_cls):
        mock_translator = MagicMock()
        mock_translator.translate.side_effect = Exception("Translation Error")
        mock_translator_cls.return_value = mock_translator

        all_rows = [
            ["Row 1", ""],
            ["Row 2", ""],
            ["Row 3", ""],
            ["Row 4", ""],
        ]
        worker = SingleCSVTranslatorWorker(
            all_rows=all_rows,
            visible_row_indices=[0, 1, 2, 3],
            source_col_idx=0,
            target_col_idx=1,
            source_lang="ja",
            target_lang="zh-TW",
            single_interval=0.0,
            skip_translated=True,
        )

        finished_status = None

        def on_finished(status):
            nonlocal finished_status
            finished_status = status

        worker.finished.connect(on_finished)
        worker.msleep = lambda msecs: None

        worker.run()

        # 當連續 3 次失敗 (5 * 3 = 15)，會觸發 RuntimeError 並發射 ERROR status
        self.assertEqual(finished_status, TaskStatus.ERROR)
        self.assertIn("Error Rank: 15 >= 15", worker._last_error)


if __name__ == "__main__":
    unittest.main()
