import concurrent.futures
import re
import time
from PyQt6.QtCore import QObject, pyqtSignal
from common_data.task_status import TaskStatus
from deep_translator import GoogleTranslator
from utils.network import get_http_error_info

# --- CSV 翻譯執行緒工人類 ---
class CSVTranslatorWorker(QObject):
    """
    CSVTranslatorWorker — 在背景執行緒中執行 CSV 批次翻譯。

    【架構規範】：此 Worker 繼承自 QObject（非 QThread），由主程式的
    PluginHostAdapter 統一建立 QThread 並管理生命週期。

    標準接口信號（run_worker 架構必要）：
      progress(current, total): 進度更新，主程式自動套 ThrottledProgress 節流。
      finished(status): 任務結束， TaskStatus 列舉物件。

    業務信號（外掛面板可自行連接）：
      status_updated(status_str): 更新 UI 狀態列字串。
      log_emitted(level, msg): 發送日誌訊息到日誌面板。
      data_changed(): 有任意列被修改時發射。
    """

    # ── 標準接口信號（run_worker 架構必要）────────────────────────────────────────────
    progress = pyqtSignal(int, int)      # current, total
    finished = pyqtSignal(TaskStatus)           # TaskStatus Enum

    # ── 業務信號（外掛面板可連接）───────────────────────────────────────────────────
    status_updated = pyqtSignal(str)     # 狀態欄更新日誌
    log_emitted = pyqtSignal(str, str)   # 級別 (INFO/SUCCESS/WARNING/ERROR), 訊息
    data_changed = pyqtSignal()          # 有任意列被修改時發射

    def __init__(self, all_rows, visible_row_indices,
                 source_col_idx, target_col_idx,
                 source_lang, target_lang,
                 batch_interval=10, single_interval=1, batch_size=18,
                 skip_translated=True):
        super().__init__()
        self.all_rows = all_rows
        self.visible_row_indices = visible_row_indices
        self.source_col_idx = source_col_idx
        self.target_col_idx = target_col_idx
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.batch_interval = batch_interval
        self.single_interval = single_interval
        self.batch_size = batch_size
        self.skip_translated = skip_translated
        self._is_cancelled = False
        self.error_rank = 0
        # 供面板在 TaskStatus.ERROR 時讀取錯誤詳情
        self._last_error: str = ""
        self.prevent_sleep = True
        self.task_name = "翻譯中..."
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

    def _do_batch_translate(self, joined_string, tag_buffer):
        """
        嘗試批取翻譯。
        回傳: (is_fallback_needed, fallback_reason, translated_tags, translated_text)
        """
        is_fallback_needed = False
        fallback_reason = ""
        translated_tags = []
        translated_text = ""
        
        try:
            translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)
            if not self._executor:
                raise RuntimeError("ThreadPoolExecutor 未初始化")
            future = self._executor.submit(translator.translate, joined_string)
            translated_text = self._wait_for_future(future, timeout=20.0)
            
            if not translated_text:
                raise ValueError("翻譯結果為空")

            translated_tags = [t.strip() for t in re.split(r'[,，、]', translated_text) if t.strip()]
            
            if len(translated_tags) != len(tag_buffer):
                is_fallback_needed = True
                fallback_reason = (
                    f"翻譯數量與來源數量不符 (來源 {len(tag_buffer)} 筆，翻譯 {len(translated_tags)} 筆)\n"
                    f"發送字串：'{joined_string}'\n"
                    f"接收字串：'{translated_text}'"
                )
                
        except Exception as e:
            if "No translation was found using the current translator" in str(e):
                is_fallback_needed = True
                fallback_reason = "翻譯失敗: 'No translation was found using the current translator'"
            else:
                raise e
                
        return is_fallback_needed, fallback_reason, translated_tags, translated_text

    def _do_single_translate_fallback(self, tag_buffer, target_col_idx):
        """
        當批次翻譯失敗或數量不符時，逐一翻譯 tag_buffer 中的項目。
        """
        for k, (r_obj, source_val, row_num) in enumerate(tag_buffer):
            if self._is_cancelled:
                raise RuntimeError("使用者已取消翻譯")
            
            actual_single_interval = self.single_interval + self.error_rank * 10
            if self.error_rank > 0:
                self.log_emitted.emit("WARNING", f"偵測到 Error Rank 為 {self.error_rank}，單筆翻譯間隔延長 {self.error_rank * 10} 秒，共 {actual_single_interval} 秒。")
            for _ in range(int(actual_single_interval * 10)):
                if self._is_cancelled:
                    raise RuntimeError("使用者已取消翻譯")
                self.msleep(100)
            
            try:
                translator_single = GoogleTranslator(source=self.source_lang, target=self.target_lang)
                if not self._executor:
                    raise RuntimeError("ThreadPoolExecutor 未初始化")
                future_single = self._executor.submit(translator_single.translate, source_val)
                single_translated = self._wait_for_future(future_single, timeout=20.0)
                
                if not single_translated:
                    raise ValueError("個別翻譯結果為空")
                
                single_translated_processed = single_translated.replace(",", "，")
                
                r_obj[target_col_idx] = single_translated_processed
                self.data_changed.emit()
                
                self.error_rank = max(0, self.error_rank - 1)
                
                success_status = f"個別翻譯成功 | 來源：{source_val} | 翻譯：{single_translated_processed} | 行號：{row_num} | Error Rank: {self.error_rank}"
                self.status_updated.emit(success_status)
                self.log_emitted.emit("SUCCESS", f"個別翻譯成功 (第 {row_num} 行)")
                self.log_emitted.emit("INFO", f"送出文字：{source_val}")
                self.log_emitted.emit("INFO", f"收到文字：{single_translated_processed}")
            except Exception as e:
                err_msg = str(e).lower()
                err_module = type(e).__module__
                
                is_net_timeout_empty = (
                    isinstance(e, (concurrent.futures.TimeoutError, TimeoutError)) or
                    isinstance(e, ValueError) or
                    "timeout" in err_msg or
                    "connection" in err_msg or
                    "network" in err_msg or
                    "requests" in err_module or
                    "urllib" in err_module or
                    "socket" in err_module or
                    isinstance(e, (OSError, ConnectionError))
                )
                
                suffix = self._get_http_error_suffix()

                if is_net_timeout_empty:
                    raise RuntimeError(f"個別翻譯失敗 (第 {row_num} 行)，翻譯內容: '{source_val}'，錯誤: {str(e)}{suffix}")
                else:
                    self.error_rank += 5
                    fail_status = f"個別翻譯異常 | 來源：{source_val} | 錯誤：{str(e)}{suffix} | 行號：{row_num} | Error Rank: {self.error_rank}"
                    self.status_updated.emit(fail_status)
                    self.log_emitted.emit("WARNING", f"單筆翻譯發生異常 (第 {row_num} 行)，內容: '{source_val}'，錯誤: {str(e)}{suffix}，Error Rank + 5 = {self.error_rank}")
                    
                    if self.error_rank >= 15:
                        raise RuntimeError(f"單筆翻譯異常次數過多 (Error Rank: {self.error_rank} >= 15)，終止翻譯。最後錯誤: {str(e)}")
        
        tag_buffer.clear()
        self._sleep_batch_interval(msg_prefix="個別翻譯批次完成，", is_fallback=True)

    def _sleep_batch_interval(self, msg_prefix: str = "", is_fallback: bool = False) -> None:
        actual_batch_interval = self.batch_interval + self.error_rank * 10
        if self.error_rank > 0:
            interval_type = "批次冷卻時間" if is_fallback else "批次翻譯間隔"
            self.log_emitted.emit(
                "WARNING",
                f"{msg_prefix}偵測到 Error Rank 為 {self.error_rank}，"
                f"{interval_type}延長 {self.error_rank * 10} 秒，共 {actual_batch_interval} 秒..."
            )
        else:
            action_text = "進行冷卻，" if is_fallback else ""
            self.log_emitted.emit("WARNING", f"{msg_prefix}{action_text}休息 {self.batch_interval} 秒...")
        for _ in range(actual_batch_interval):
            if self._is_cancelled:
                break
            self.msleep(1000)

    def translate_batch(self, tag_buffer, target_col_idx):
        if not tag_buffer:
            return True
            
        if self._is_cancelled:
            raise RuntimeError("使用者已取消翻譯")
            
        texts = [item[1] for item in tag_buffer]
        joined_string = ",".join(texts)
        
        try:
            is_fallback_needed, fallback_reason, translated_tags, translated_text = self._do_batch_translate(
                joined_string, tag_buffer
            )

            if is_fallback_needed:
                self.log_emitted.emit("WARNING", f"{fallback_reason}\n開始進行逐筆個別翻譯...")
                self._do_single_translate_fallback(tag_buffer, target_col_idx)
                return False
                
            for (r_obj, _, _), trans_text in zip(tag_buffer, translated_tags):
                r_obj[target_col_idx] = trans_text
                
            self.data_changed.emit()
            self.error_rank = max(0, self.error_rank - 1)
            
            first_row = tag_buffer[0][2]
            last_row = tag_buffer[-1][2]
            
            success_status = f"批次翻譯成功 | 來源：{joined_string} | 翻譯：{translated_text} | 行號：{first_row} - {last_row} | Error Rank: {self.error_rank}"
            self.status_updated.emit(success_status)
            self.log_emitted.emit("SUCCESS", f"批次翻譯成功 (第 {first_row} - {last_row} 行)")
            self.log_emitted.emit("INFO", f"送出文字：{joined_string}")
            self.log_emitted.emit("INFO", f"收到文字：{translated_text}")
            
            tag_buffer.clear()
            return True
            
        except Exception as e:
            suffix = self._get_http_error_suffix()
            error_msg = f"{str(e)}{suffix}"

            fail_status = f"翻譯失敗 | 送出文字：{joined_string} | 錯誤訊息：{error_msg}"
            self.status_updated.emit(fail_status)
            self.log_emitted.emit("ERROR", f"翻譯失敗！ 送出文字：{joined_string}\n收到文字：\n錯誤訊息：{error_msg}")
            
            tag_buffer.clear()
            raise RuntimeError(fail_status)

    def run(self):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            self.error_rank = 0
            self.log_emitted.emit("INFO", "開始執行記憶體 CSV 翻譯工作...")

            total_to_translate = len(self.visible_row_indices)
            self.log_emitted.emit("INFO", f"欲翻譯之可見行數共 {total_to_translate} 行")

            tag_buffer = []
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
                tag_buffer.append((row, source_val, row_num))
                
                total_char_len = sum(len(item[1]) for item in tag_buffer)
                if len(tag_buffer) >= self.batch_size or total_char_len > 240:
                    self.log_emitted.emit("INFO", f"達到批次處理上限 (tag: {len(tag_buffer)}/{self.batch_size}, chars: {total_char_len}/240)，開始進行批次翻譯...")
                    self.translate_batch(tag_buffer, self.target_col_idx)
                    
                    self._sleep_batch_interval()
                    
            if self._is_cancelled:
                self.log_emitted.emit("WARNING", "使用者已取消翻譯。")
                self.finished.emit(TaskStatus.CANCELLED)
            else:
                if tag_buffer:
                    self.log_emitted.emit("INFO", f"開始處理最後殘留批次，共 {len(tag_buffer)} 筆...")
                    self.translate_batch(tag_buffer, self.target_col_idx)
                self.log_emitted.emit("SUCCESS", "翻譯完成！")
                self.finished.emit(TaskStatus.FINISHED)
  
        except Exception as e:
            self._last_error = str(e)
            self.log_emitted.emit("ERROR", f"翻譯過程發生錯誤：{str(e)}")
            self.finished.emit(TaskStatus.ERROR)
        finally:
            if self._executor:
                self._executor.shutdown(wait=False)
                self._executor = None
