"""
FileOpsMixin — 檔案操作與存檔

職責：CSV 來源/輸出路徑的瀏覽、交換、變更事件處理；
      將 DataEditorPanel 的記憶體資料寫入 CSV 檔案。
"""
from __future__ import annotations

import csv
import os
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFileDialog, QMessageBox

if TYPE_CHECKING:
    from ui import MainWindow


class FileOpsMixin:

    def swap_csv_paths(self: "MainWindow") -> None:
        src = self.txt_src_path.text()
        out = self.txt_out_path.text()
        self.txt_src_path.setText(out)
        self.txt_out_path.setText(src)

    def browse_source_file(self: "MainWindow") -> None:
        current_src = self.txt_src_path.text().strip()
        initial_path = current_src if current_src else os.path.expanduser("~")
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇來源 CSV 檔案", initial_path, "CSV 檔案 (*.csv);;所有檔案 (*)"
        )
        if file_path:
            current_out = self.txt_out_path.text().strip()
            if current_out and file_path == current_out:
                QMessageBox.warning(
                    self,
                    "路徑重複",
                    "選擇的來源 CSV 檔案不能與輸出 CSV 檔案路徑相同！請重新選擇。",
                )
                return

            self.txt_src_path.setText(file_path)
            # 自動推導輸出檔案路徑
            if not self.txt_out_path.text().strip():
                dir_name, file_name = os.path.split(file_path)
                name, ext = os.path.splitext(file_name)
                default_out = os.path.join(dir_name, f"{name}_translated{ext}")
                self.txt_out_path.setText(default_out)

    def browse_output_file(self: "MainWindow") -> None:
        current_out = self.txt_out_path.text().strip()
        initial_path = current_out if current_out else os.path.expanduser("~")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "選擇儲存輸出 CSV 檔案", initial_path, "CSV 檔案 (*.csv);;所有檔案 (*)"
        )
        if file_path:
            current_src = self.txt_src_path.text().strip()
            if current_src and file_path == current_src:
                QMessageBox.warning(
                    self,
                    "路徑重複",
                    "選擇的輸出 CSV 檔案不能與來源 CSV 檔案路徑相同！請重新選擇。",
                )
                return

            self.txt_out_path.setText(file_path)

    def on_source_file_changed(self: "MainWindow", file_path: str) -> None:
        self.txt_end_row.setPlaceholderText("預設至檔尾")
        self.edit_content_panel.clear()
        self.edit_panel.reset_panel()
        if self.worker and hasattr(self.worker, "loaded_rows"):
            self.worker.loaded_rows = []

    def save_edit_data(self: "MainWindow") -> None:
        out_path = self.txt_out_path.text().strip()
        if not out_path:
            QMessageBox.warning(self, "錯誤", "請指定輸出 CSV 檔案路徑！")
            return

        src_path = self.txt_src_path.text().strip()
        if src_path and out_path and src_path == out_path:
            QMessageBox.warning(
                self, "路徑重複", "來源 CSV 與輸出 CSV 路徑相同，無法存檔！請變更輸出路徑。"
            )
            return

        all_rows = self.edit_content_panel.get_all_rows()
        if not all_rows:
            QMessageBox.warning(self, "錯誤", "沒有資料可儲存。")
            return

        delimiter = self.edit_content_panel.get_delimiter()

        try:
            out_dir = os.path.dirname(out_path)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)

            with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f, delimiter=delimiter)
                writer.writerows(all_rows)

            self.edit_content_panel.set_modified(False)
            self.append_log("SUCCESS", f"編輯資料存檔成功！已寫入至：{out_path}")
            QMessageBox.information(self, "成功", f"存檔成功！\n檔案已儲存至：\n{out_path}")

        except Exception as e:
            self.append_log("ERROR", f"存檔失敗：{str(e)}")
            QMessageBox.critical(self, "存檔失敗", f"存檔失敗：\n{str(e)}")
