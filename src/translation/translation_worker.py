import os
import re
import csv
import concurrent.futures
from deep_translator import GoogleTranslator
from network import get_http_error_info
from csv_worker import BaseCSVWorker

# --- CSV 翻譯執行緒工人類 ---
class CSVTranslatorWorker(BaseCSVWorker):
    def __init__(self, source_path, output_path, start_row, end_row, source_col, target_col, source_lang, target_lang, batch_interval=10, single_interval=1, batch_size=18):
        super().__init__(source_path, output_path, start_row, end_row)
        self.source_col = source_col
        self.target_col = target_col
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.batch_interval = batch_interval
        self.single_interval = single_interval
        self.batch_size = batch_size
        self.error_rank = 0

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

    def _do_batch_translate(self, joined_string, tag_buffer):
        """
        嘗試批次翻譯。
        回傳: (is_fallback_needed, fallback_reason, translated_tags, translated_text)
        """
        is_fallback_needed = False
        fallback_reason = ""
        translated_tags = []
        translated_text = ""
        
        try:
            translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(translator.translate, joined_string)
                translated_text = future.result(timeout=20.0)
            
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
            # 檢測是否為 "No translation was found using the current translator" 異常
            if "No translation was found using the current translator" in str(e):
                is_fallback_needed = True
                fallback_reason = "翻譯失敗: 'No translation was found using the current translator'"
            else:
                # 其他錯誤直接 re-raise，由外層 try-except 捕獲處理
                raise e
                
        return is_fallback_needed, fallback_reason, translated_tags, translated_text

    def _do_single_translate_fallback(self, tag_buffer, line_buffer, writer, target_col_idx, context):
        """
        當批次翻譯失敗或數量不符時，逐一翻譯 tag_buffer 中的項目。
        """
        for k, (r_obj, source_val, row_num) in enumerate(tag_buffer):
            if self._is_cancelled:
                raise RuntimeError("使用者已取消翻譯")
            
            # 每一筆個別翻譯前，加入單筆間隔冷卻時間 (每 100ms 檢查一次是否取消)
            actual_single_interval = self.single_interval + self.error_rank * 10
            if self.error_rank > 0:
                self.log_emitted.emit("WARNING", f"偵測到 Error Rank 為 {self.error_rank}，單筆翻譯間隔延長 {self.error_rank * 10} 秒，共 {actual_single_interval} 秒。")
            for _ in range(int(actual_single_interval * 10)):
                if self._is_cancelled:
                    raise RuntimeError("使用者已取消翻譯")
                self.msleep(100)
            
            try:
                translator_single = GoogleTranslator(source=self.source_lang, target=self.target_lang)
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future_single = executor.submit(translator_single.translate, source_val)
                    single_translated = future_single.result(timeout=20.0)
                
                if not single_translated:
                    raise ValueError("個別翻譯結果為空")
                
                # 避免逗號切割CSV問題
                single_translated_processed = single_translated.replace(",", "，")
                
                r_obj[target_col_idx] = single_translated_processed
                
                self.error_rank = max(0, self.error_rank - 1)
                
                success_status = f"個別翻譯成功 | 來源：{source_val} | 翻譯：{single_translated_processed} | 行號：{row_num} | Error Rank: {self.error_rank}"
                self.status_updated.emit(success_status)
                self.log_emitted.emit("SUCCESS", f"個別翻譯成功 (第 {row_num} 行)")
                self.log_emitted.emit("INFO", f"送出文字：{source_val}")
                self.log_emitted.emit("INFO", f"收到文字：{single_translated_processed}")
            except Exception as e:
                err_msg = str(e).lower()
                err_type_str = type(e).__name__
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
            
            # 寫回 CSV
            idx = line_buffer.index(r_obj)
            next_to_write = context["next_to_write"]
            write_slice = line_buffer[next_to_write : idx + 1]
            if write_slice:
                writer.writerows(write_slice)
            context["next_to_write"] = idx + 1

        next_to_write = context["next_to_write"]
        if next_to_write < len(line_buffer):
            writer.writerows(line_buffer[next_to_write:])
        
        tag_buffer.clear()
        line_buffer.clear()
        
        # 逐筆個別翻譯執行到最後，加上跟批次翻譯一樣的冷卻時間
        actual_batch_interval = self.batch_interval + self.error_rank * 10
        if self.error_rank > 0:
            self.log_emitted.emit("WARNING", f"個別翻譯批次完成，偵測到 Error Rank 為 {self.error_rank}，批次冷卻時間延長 {self.error_rank * 10} 秒，共 {actual_batch_interval} 秒...")
        else:
            self.log_emitted.emit("WARNING", f"個別翻譯批次完成，進行冷卻，休息 {self.batch_interval} 秒...")
        for _ in range(actual_batch_interval):
            if self._is_cancelled:
                break
            self.msleep(1000)

    def _flush_remaining(self, line_buffer, tag_buffer, writer, reader, max_idx, context):
        """
        當翻譯發生致命錯誤時，將剩餘緩衝區的行與讀取器中未處理的行原樣寫入 CSV，以保護資料完整性。
        """
        next_to_write = context.get("next_to_write", 0)
        if next_to_write < len(line_buffer):
            writer.writerows(line_buffer[next_to_write:])
        tag_buffer.clear()
        line_buffer.clear()
        
        self.log_emitted.emit("WARNING", "翻譯終止，將剩餘未翻譯行原樣寫入檔案...")
        for remain_row in reader:
            while len(remain_row) <= max_idx:
                remain_row.append("")
            writer.writerow(remain_row)

    def translate_batch(self, tag_buffer, line_buffer, writer, reader, target_col_idx, source_col_idx, max_idx):
        if not tag_buffer:
            return True
            
        if self._is_cancelled:
            raise RuntimeError("使用者已取消翻譯")
            
        texts = [item[1] for item in tag_buffer]
        joined_string = ",".join(texts)
        context = {"next_to_write": 0}
        
        try:
            # 1. 嘗試批次翻譯
            is_fallback_needed, fallback_reason, translated_tags, translated_text = self._do_batch_translate(
                joined_string, tag_buffer
            )

            # 2. 如果需要 fallback，則執行逐筆個別翻譯
            if is_fallback_needed:
                self.log_emitted.emit("WARNING", f"{fallback_reason}\n開始進行逐筆個別翻譯...")
                self._do_single_translate_fallback(tag_buffer, line_buffer, writer, target_col_idx, context)
                return False
                
            # 3. 正常批次翻譯成功
            for (r_obj, _, _), trans_text in zip(tag_buffer, translated_tags):
                r_obj[target_col_idx] = trans_text
                
            self.error_rank = max(0, self.error_rank - 1)
            
            first_row = tag_buffer[0][2]
            last_row = tag_buffer[-1][2]
            
            success_status = f"批次翻譯成功 | 來源：{joined_string} | 翻譯：{translated_text} | 行號：{first_row} - {last_row} | Error Rank: {self.error_rank}"
            self.status_updated.emit(success_status)
            self.log_emitted.emit("SUCCESS", f"批次翻譯成功 (第 {first_row} - {last_row} 行)")
            self.log_emitted.emit("INFO", f"送出文字：{joined_string}")
            self.log_emitted.emit("INFO", f"收到文字：{translated_text}")
            return True
            
        except Exception as e:
            # 批次或個別翻譯發生致命錯誤，將剩餘未翻譯行原樣寫入，避免損壞檔案
            suffix = self._get_http_error_suffix()
            error_msg = f"{str(e)}{suffix}"

            fail_status = f"翻譯失敗 | 送出文字：{joined_string} | 錯誤訊息：{error_msg}"
            self.status_updated.emit(fail_status)
            self.log_emitted.emit("ERROR", f"翻譯失敗！ 送出文字：{joined_string}\n收到文字：\n錯誤訊息：{error_msg}")
            
            self._flush_remaining(line_buffer, tag_buffer, writer, reader, max_idx, context)
                
            raise RuntimeError(fail_status)

    def run(self):
        try:
            self.error_rank = 0
            self.log_emitted.emit("INFO", "開始執行 CSV 翻譯工作...")
            encoding, delimiter = self.detect_format()
            total_file_rows = self.count_total_rows(encoding, delimiter)
            self.log_emitted.emit("INFO", f"來源檔案讀取完成，共 {total_file_rows} 行。")

            # 翻譯範圍限制
            start_row = self.start_row
            end_row = self.end_row if self.end_row is not None else total_file_rows
            total_to_translate = max(0, end_row - start_row + 1)
            
            self.log_emitted.emit("INFO", f"欲翻譯範圍：自 {start_row} 行至 {end_row} 行 (共 {total_to_translate} 行)")

            tag_buffer = []
            line_buffer = []

            source_col_idx = self.source_col - 1
            target_col_idx = self.target_col - 1
            max_idx = max(source_col_idx, target_col_idx)

            with open(self.source_path, 'r', encoding=encoding, errors='replace') as f_in:
                reader = csv.reader(f_in, delimiter=delimiter)
                
                # 建立輸出檔案路徑
                out_dir = os.path.dirname(self.output_path)
                if out_dir and not os.path.exists(out_dir):
                    os.makedirs(out_dir, exist_ok=True)
                
                with open(self.output_path, 'w', encoding='utf-8-sig', newline='') as f_out:
                    writer = csv.writer(f_out, delimiter=delimiter)
                    
                    row_num = 0
                    processed_count = 0
                    
                    # 1. 迴圈讀取並處理每一列
                    for row in reader:
                        row_num += 1
                        
                        # 補齊欄位避免 IndexError
                        while len(row) <= max_idx:
                            row.append("")
                        
                        # 檢查是否取消
                        if self._is_cancelled:
                            self.log_emitted.emit("WARNING", "使用者已取消翻譯，正在將剩餘行原樣寫入檔案...")
                            writer.writerows(line_buffer)
                            tag_buffer.clear()
                            line_buffer.clear()
                            
                            writer.writerow(row)
                            
                            for remain_row in reader:
                                while len(remain_row) <= max_idx:
                                    remain_row.append("")
                                writer.writerow(remain_row)
                            break
                                
                        if row_num < start_row:
                            writer.writerow(row)
                            continue
                            
                        # 結束行號
                        if row_num > end_row:
                            if tag_buffer:
                                self.log_emitted.emit("INFO", f"已超過結束行，翻譯最後殘留批次，共 {len(tag_buffer)} 筆...")
                                if self.translate_batch(tag_buffer, line_buffer, writer, reader, target_col_idx, source_col_idx, max_idx):
                                    writer.writerows(line_buffer)
                                    tag_buffer.clear()
                                    line_buffer.clear()
                                
                            writer.writerow(row)
                            continue
                            
                        processed_count += 1
                        self.progress_updated.emit(processed_count, total_to_translate)
                        
                        target_val = row[target_col_idx].strip()
                        source_val = row[source_col_idx]
                        
                        if target_val != "" and not line_buffer:
                            writer.writerow(row)
                            continue
                            
                        # 5.2 如果目標列的值不為空，則加入 line buffer
                        elif target_val != "":
                            line_buffer.append(row)
                            
                        # 5.3 如果目標列的值為空，則加入待翻譯的 tag buffer，並加入 line buffer
                        else:
                            tag_buffer.append((row, source_val, row_num))
                            line_buffer.append(row)
                            
                        # 5.4 如果 tag buffer 長度達到 batch_size 筆，或 line buffer 達到 500 筆，或 tag buffer 總字元數超過 240
                        total_char_len = sum(len(item[1]) for item in tag_buffer)
                        if len(tag_buffer) >= self.batch_size or len(line_buffer) >= 500 or total_char_len > 240:
                            self.log_emitted.emit("INFO", f"達到批次處理上限 (tag: {len(tag_buffer)}/{self.batch_size}, line: {len(line_buffer)}/500, chars: {total_char_len}/240)，開始進行批次翻譯...")
                            if self.translate_batch(tag_buffer, line_buffer, writer, reader, target_col_idx, source_col_idx, max_idx):
                                # 5.4.2
                                writer.writerows(line_buffer)
                                tag_buffer.clear()
                                line_buffer.clear()
                                
                                # 5.4.3 休息指定的批次間隔時間
                                actual_batch_interval = self.batch_interval + self.error_rank * 10
                                if self.error_rank > 0:
                                    self.log_emitted.emit("WARNING", f"偵測到 Error Rank 為 {self.error_rank}，批次翻譯間隔延長 {self.error_rank * 10} 秒，共 {actual_batch_interval} 秒...")
                                else:
                                    self.log_emitted.emit("WARNING", f"休息 {self.batch_interval} 秒...")
                                for _ in range(actual_batch_interval):
                                    if self._is_cancelled:
                                        break
                                    self.msleep(1000)
                                
                    # 2. 如果已讀取到檔案末尾，處理最後殘留批次
                    if tag_buffer:
                        self.log_emitted.emit("INFO", f"文件已讀取完畢，開始處理最後殘留批次，共 {len(tag_buffer)} 筆...")
                        self.translate_batch(tag_buffer, line_buffer, writer, reader, target_col_idx, source_col_idx, max_idx)
                    
                    # 寫入 line buffer 中的剩餘行
                    if line_buffer:
                        writer.writerows(line_buffer)
                        tag_buffer.clear()
                        line_buffer.clear()
 
            if self._is_cancelled:
                self.log_emitted.emit("WARNING", f"翻譯已取消！結果已寫入至：{self.output_path}")
            else:
                self.log_emitted.emit("SUCCESS", f"翻譯完成！結果已寫入至：{self.output_path}")
            self.finished_successfully.emit(self.output_path)
 
        except Exception as e:
            self.log_emitted.emit("ERROR", f"翻譯過程發生錯誤：{str(e)}")
            self.finished_with_error.emit(str(e))

    def get_success_message(self, out_path):
        return "成功", f"翻譯完成！\n檔案已儲存至：\n{out_path}"

    def get_cancel_message(self, out_path):
        return "中斷", f"已取消翻譯！\n檔案已儲存至：\n{out_path}"

    def get_error_message(self, err_msg):
        return "翻譯中斷", f"翻譯過程發生錯誤：\n{err_msg}"

