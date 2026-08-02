import concurrent.futures
import time
from PyQt6.QtCore import QObject, pyqtSignal
from common_data.task_status import TaskStatus
from deep_translator import GoogleTranslator
from utils.network import get_http_error_info

# --- 單筆 CSV 翻譯執行緒工人類 ---
class SingleCSVTranslatorWorker(QObject):
    """
    SingleCSVTranslatorWorker — 在背景執行緒中執行 CSV 單筆全文翻譯。

    【架構規範】：此 Worker 繼承自 QObject（非 QThread），由主程式的
    PluginHostAdapter 統一建立 QThread 並管理生命週期。

    標準接口信號（run_worker 架構必要）：
      progress(current, total): 進度更新，主程式自動套 ThrottledProgress 節流。
      finished(status): 任務結束， "finished" | "error" | "cancelled"。

    業務信號（外掛面板可自行連接）：
      status_updated(status_str): 更新 UI 狀態列字串。
      log_emitted(level, msg): 發送日誌訊息到日誌面板。
      data_changed(): 有任意列被修改時發射。
    """

    # ── 標準接口信號（run_worker 架構必要）────────────────────────────────────────────
    progress = pyqtSignal(int, int)      # current, total
    finished = pyqtSignal(TaskStatus)    # TaskStatus Enum

    # ── 業務信號（外掛面板可連接）───────────────────────────────────────────────────
    status_updated = pyqtSignal(str)     # 狀態欄更新日誌
    log_emitted = pyqtSignal(str, str)   # 級別 (INFO/SUCCESS/WARNING/ERROR), 訊息
    data_changed = pyqtSignal()          # 有任意列被修改時發射

    def __init__(self, all_rows, visible_row_indices,
                 source_col_idx, target_col_idx,
                 source_lang, target_lang,
                 single_interval=1.0,
                 skip_translated=True):
        super().__init__()
        self.all_rows = all_rows
        self.visible_row_indices = visible_row_indices
        self.source_col_idx = source_col_idx
        self.target_col_idx = target_col_idx
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.single_interval = single_interval
        self.skip_translated = skip_translated
        self._is_cancelled = False
        self.error_rank = 0
        # 供面板在 finished("error") 時讀取錯誤詳情
        self._last_error: str = ""
        self.prevent_sleep = True
        self.task_name = "單筆翻譯中..."
        self._executor = None

    def cancel(self) -> None:
        """供主程式呼叫，用以要求終止背景處理迴圈。"""
        self._is_cancelled = True

    def pause(self):
        pass

    def resume(self):
        pass

    def _get_http_error_suffix(self):
        """
        獲取 HTTP 錯誤狀態碼與原因的字尾說明。
        """
        error_info = get_http_error_info()
        status_code = getattr(error_info, "status_code", None)
        reason = getattr(error_info, "reason", None)
        if status_code is not None:
            return f" (HTTP Status Code: {status_code}, Message: {reason})"
        elif reason is not None:
            return f" (Error: {reason})"
        return ""

    def msleep(self, msecs: int) -> None:
        """使執行緒暫停指定的毫秒數。"""
        from PyQt6.QtCore import QThread
        QThread.msleep(msecs)

    def _wait_for_future(self, future, timeout=20.0):
        """非阻塞式輪詢等待 Future 完成，並支援即時取消。"""
        start_time = time.time()
        while not future.done():
            if self._is_cancelled:
                future.cancel()
                raise RuntimeError("使用者已取消翻譯")
            if time.time() - start_time > timeout:
                future.cancel()
                raise concurrent.futures.TimeoutError("翻譯超時")
            self.msleep(100)
        return future.result()

    def run(self):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            self.error_rank = 0
            self.log_emitted.emit("INFO", "開始執行記憶體 CSV 單筆翻譯工作...")

            total_to_translate = len(self.visible_row_indices)
            self.log_emitted.emit("INFO", f"欲翻譯之可見行數共 {total_to_translate} 行")

            target_col_idx = self.target_col_idx
            processed_count = 0

            for idx in self.visible_row_indices:
                if self._is_cancelled:
                    break

                row = self.all_rows[idx]

                # 補齊欄位避免 IndexError
                while len(row) <= max(self.source_col_idx, self.target_col_idx):
                    row.append("")

                processed_count += 1
                self.progress.emit(processed_count, total_to_translate)

                target_val = row[self.target_col_idx].strip()
                source_val = row[self.source_col_idx]

                # 若目標列的值不為空，且設定為略過已翻譯欄位，跳過不翻譯
                if self.skip_translated and target_val != "":
                    continue

                row_num = idx + 1

                # 若來源內容為空，跳過不翻譯
                if not source_val or source_val.strip() == "":
                    continue

                # 間隔控制：error_rank > 0 時，固定為 user 選定間隔 + 10 秒
                if self.error_rank > 0:
                    actual_interval = self.single_interval + 10.0
                    self.log_emitted.emit(
                        "WARNING",
                        f"偵測到 Error Rank 為 {self.error_rank}，單筆翻譯間隔固定延長 10 秒，共 {actual_interval:.1f} 秒。"
                    )
                else:
                    actual_interval = self.single_interval

                # 依計算間隔進行暫停與取消檢查
                sleep_steps = int(actual_interval * 10)
                for _ in range(sleep_steps):
                    if self._is_cancelled:
                        break
                    self.msleep(100)

                if self._is_cancelled:
                    break

                try:
                    translator_single = GoogleTranslator(source=self.source_lang, target=self.target_lang)
                    if not self._executor:
                        raise RuntimeError("ThreadPoolExecutor 未初始化")
                    future_single = self._executor.submit(translator_single.translate, source_val)
                    single_translated = self._wait_for_future(future_single, timeout=20.0)

                    if single_translated is None:
                        raise ValueError("單筆翻譯結果為空")

                    # 對來源欄位內容不做修改，直接全文翻譯；結果去除頭尾空白與換行後回填
                    processed_translated = single_translated.strip()

                    row[target_col_idx] = processed_translated
                    self.data_changed.emit()

                    self.error_rank = max(0, self.error_rank - 1)

                    success_status = f"單筆翻譯成功 | 來源：{source_val} | 翻譯：{processed_translated} | 行號：{row_num} | Error Rank: {self.error_rank}"
                    self.status_updated.emit(success_status)
                    self.log_emitted.emit("SUCCESS", f"單筆翻譯成功 (第 {row_num} 行)")
                    self.log_emitted.emit("INFO", f"送出文字：{source_val}")
                    self.log_emitted.emit("INFO", f"收到文字：{processed_translated}")

                except Exception as e:
                    if self._is_cancelled or "使用者已取消翻譯" in str(e):
                        break

                    suffix = self._get_http_error_suffix()
                    self.error_rank += 5

                    fail_status = f"單筆翻譯異常 | 來源：{source_val} | 錯誤：{str(e)}{suffix} | 行號：{row_num} | Error Rank: {self.error_rank}"
                    self.status_updated.emit(fail_status)
                    self.log_emitted.emit(
                        "WARNING",
                        f"單筆翻譯發生異常 (第 {row_num} 行)，內容: '{source_val}'，錯誤: {str(e)}{suffix}，Error Rank + 5 = {self.error_rank}"
                    )

                    if self.error_rank >= 15:
                        raise RuntimeError(f"單筆翻譯異常次數過多 (Error Rank: {self.error_rank} >= 15)，終止翻譯。最後錯誤: {str(e)}")

            if self._is_cancelled:
                self.log_emitted.emit("WARNING", "使用者已取消翻譯。")
                self.finished.emit(TaskStatus.CANCELLED)
            else:
                self.log_emitted.emit("SUCCESS", "單筆翻譯完成！")
                self.finished.emit(TaskStatus.FINISHED)

        except Exception as e:
            self._last_error = str(e)
            self.log_emitted.emit("ERROR", f"單筆翻譯過程發生錯誤：{str(e)}")
            self.finished.emit(TaskStatus.ERROR)
        finally:
            if self._executor:
                self._executor.shutdown(wait=False)
                self._executor = None
