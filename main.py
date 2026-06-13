import sys
import csv
import os
import time
import re
import concurrent.futures
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QFrame, QHeaderView
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer, QSettings
from PyQt6.QtGui import QIntValidator, QFont
from deep_translator import GoogleTranslator
import threading
import requests

# 執行緒區域變數，用以捕捉最近一次 HTTP 請求的狀態碼與錯誤訊息
_http_error_info = threading.local()
_original_get = requests.get

def _custom_get(*args, **kwargs):
    _http_error_info.status_code = None
    _http_error_info.reason = None
    try:
        response = _original_get(*args, **kwargs)
        if response.status_code < 200 or response.status_code >= 300:
            _http_error_info.status_code = response.status_code
            _http_error_info.reason = response.reason or response.text[:200]
        return response
    except Exception as e:
        _http_error_info.reason = str(e)
        raise e

requests.get = _custom_get

# --- 輔助函數：自動檢測編碼與分隔符 ---
def detect_encoding(file_path):
    encodings = ['utf-8-sig', 'utf-8', 'cp950', 'gbk', 'utf-16', 'latin-1']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                f.read(4096)
            return enc
        except UnicodeDecodeError:
            continue
    return 'utf-8'

def detect_delimiter(file_path, encoding):
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            sample = f.read(2048)
            dialect = csv.Sniffer().sniff(sample)
            return dialect.delimiter
    except Exception:
        return ','

# --- CSV 翻譯執行緒工人類 ---
class CSVTranslatorWorker(QThread):
    progress_updated = pyqtSignal(int, int)      # 已翻譯列數, 總共列數
    status_updated = pyqtSignal(str)             # 狀態欄更新日誌
    log_emitted = pyqtSignal(str, str)           # 級別 (INFO/SUCCESS/WARNING/ERROR), 訊息
    finished_successfully = pyqtSignal(str)      # 成功時的輸出檔案路徑
    finished_with_error = pyqtSignal(str)        # 錯誤原因

    def __init__(self, source_path, output_path, start_row, end_row, source_col, target_col, source_lang, target_lang, batch_interval=10, single_interval=1):
        super().__init__()
        self.source_path = source_path
        self.output_path = output_path
        self.start_row = start_row
        self.end_row = end_row
        self.source_col = source_col
        self.target_col = target_col
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.batch_interval = batch_interval
        self.single_interval = single_interval
        self._is_paused = False
        self._is_cancelled = False
        self.error_rank = 0

    def pause(self):
        self._is_paused = True

    def cancel(self):
        self._is_cancelled = True

    def translate_batch(self, tag_buffer, line_buffer, writer, reader, target_col_idx, source_col_idx, max_idx):
        if not tag_buffer:
            return True
            
        if self._is_cancelled:
            raise RuntimeError("使用者已取消翻譯")
            
        texts = [item[1] for item in tag_buffer]
        joined_string = ",".join(texts)
        translated_text = ""
        next_to_write = 0
        
        is_fallback_needed = False
        fallback_reason = ""
        
        try:
            try:
                # 1. 嘗試批次翻譯
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

            if is_fallback_needed:
                self.log_emitted.emit("WARNING", f"{fallback_reason}\n開始進行逐筆個別翻譯...")
                
                for k, (r_obj, source_val, row_num) in enumerate(tag_buffer):
                    if self._is_cancelled:
                        raise RuntimeError("使用者已取消翻譯")
                    
                    # 每一筆個別翻譯前，加入單筆間隔冷卻時間 (每 100ms 檢查一次是否取消)
                    for _ in range(self.single_interval * 10):
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
                        
                        status_code = getattr(_http_error_info, "status_code", None)
                        reason = getattr(_http_error_info, "reason", None)
                        extra_info = ""
                        if status_code is not None:
                            extra_info = f" (HTTP Status Code: {status_code}, Message: {reason})"
                        elif reason is not None:
                            extra_info = f" (Error: {reason})"

                        if is_net_timeout_empty:
                            raise RuntimeError(f"個別翻譯失敗 (第 {row_num} 行)，翻譯內容: '{source_val}'，錯誤: {str(e)}{extra_info}")
                        else:
                            self.error_rank += 5
                            fail_status = f"個別翻譯異常 | 來源：{source_val} | 錯誤：{str(e)}{extra_info} | 行號：{row_num} | Error Rank: {self.error_rank}"
                            self.status_updated.emit(fail_status)
                            self.log_emitted.emit("WARNING", f"單筆翻譯發生異常 (第 {row_num} 行)，內容: '{source_val}'，錯誤: {str(e)}{extra_info}，Error Rank + 5 = {self.error_rank}")
                            
                            if self.error_rank >= 15:
                                raise RuntimeError(f"單筆翻譯異常次數過多 (Error Rank: {self.error_rank} >= 15)，終止翻譯。最後錯誤: {str(e)}")
                    
                    # 寫回 CSV
                    idx = line_buffer.index(r_obj)
                    write_slice = line_buffer[next_to_write : idx + 1]
                    if write_slice:
                        writer.writerows(write_slice)
                    next_to_write = idx + 1

                if next_to_write < len(line_buffer):
                    writer.writerows(line_buffer[next_to_write:])
                
                tag_buffer.clear()
                line_buffer.clear()
                
                # 逐筆個別翻譯執行到最後，加上跟批次翻譯一樣的冷卻時間
                self.log_emitted.emit("WARNING", f"個別翻譯批次完成，進行冷卻，休息 {self.batch_interval} 秒...")
                for _ in range(self.batch_interval):
                    if self._is_cancelled:
                        break
                    self.msleep(1000)
                
                return False
                
            # 正常批次翻譯成功
            for (r_obj, _, _), trans_text in zip(tag_buffer, translated_tags):
                r_obj[target_col_idx] = trans_text
                
            first_row = tag_buffer[0][2]
            last_row = tag_buffer[-1][2]
            
            success_status = f"批次翻譯成功 | 來源：{joined_string} | 翻譯：{translated_text} | 行號：{first_row} - {last_row}"
            self.status_updated.emit(success_status)
            self.log_emitted.emit("SUCCESS", f"批次翻譯成功 (第 {first_row} - {last_row} 行)")
            self.log_emitted.emit("INFO", f"送出文字：{joined_string}")
            self.log_emitted.emit("INFO", f"收到文字：{translated_text}")
            return True
            
        except Exception as e:
            # 批次或個別翻譯發生致命錯誤，寫出剩餘行，將剩餘未翻譯行原樣寫入，避免損壞檔案
            error_msg = str(e)
            status_code = getattr(_http_error_info, "status_code", None)
            reason = getattr(_http_error_info, "reason", None)
            if status_code is not None:
                error_msg = f"{error_msg} (HTTP Status Code: {status_code}, Message: {reason})"
            elif reason is not None:
                error_msg = f"{error_msg} (Error: {reason})"

            fail_status = f"翻譯失敗 | 送出文字：{joined_string} | 錯誤訊息：{error_msg}"
            self.status_updated.emit(fail_status)
            self.log_emitted.emit("ERROR", f"翻譯失敗！ 送出文字：{joined_string}\n收到文字：\n錯誤訊息：{error_msg}")
            
            if next_to_write < len(line_buffer):
                writer.writerows(line_buffer[next_to_write:])
            tag_buffer.clear()
            line_buffer.clear()
            
            self.log_emitted.emit("WARNING", "翻譯終止，將剩餘未翻譯行原樣寫入檔案...")
            for remain_row in reader:
                while len(remain_row) <= max_idx:
                    remain_row.append("")
                writer.writerow(remain_row)
                
            raise RuntimeError(fail_status)

    def run(self):
        try:
            self.error_rank = 0
            self.log_emitted.emit("INFO", "開始執行 CSV 翻譯工作...")
            self.log_emitted.emit("INFO", "正在檢測檔案編碼與格式...")
            encoding = detect_encoding(self.source_path)
            delimiter = detect_delimiter(self.source_path, encoding)
            self.log_emitted.emit("INFO", f"檢測到檔案編碼: {encoding}，分隔符: '{delimiter}'")

            # 讀取檔案總行數
            with open(self.source_path, 'r', encoding=encoding, errors='replace') as f:
                total_file_rows = sum(1 for _ in csv.reader(f, delimiter=delimiter))
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
                                
        # 4. 開始與停止控制
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
                            
        # 結束行號
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
                            
                        # 5.4 如果 tag buffer 長度達到 18 筆或 line buffer 達到 500 筆
                        if len(tag_buffer) >= 18 or len(line_buffer) >= 500:
                            self.log_emitted.emit("INFO", f"達到批次處理上限 (tag: {len(tag_buffer)}/18, line: {len(line_buffer)}/500)，開始進行批次翻譯...")
                            if self.translate_batch(tag_buffer, line_buffer, writer, reader, target_col_idx, source_col_idx, max_idx):
                                # 5.4.2
                                writer.writerows(line_buffer)
                                tag_buffer.clear()
                                line_buffer.clear()
                                
                                # 5.4.3 休息指定的批次間隔時間
                                self.log_emitted.emit("WARNING", f"休息 {self.batch_interval} 秒...")
                                for _ in range(self.batch_interval):
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

            self.log_emitted.emit("SUCCESS", f"翻譯完成！結果已寫入至：{self.output_path}")
            self.finished_successfully.emit(self.output_path)

        except Exception as e:
            self.log_emitted.emit("ERROR", f"翻譯過程發生錯誤：{str(e)}")
            self.finished_with_error.emit(str(e))


            # 恢復視窗幾何狀態
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.start_time = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_elapsed_time)
        self.settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.ini")
        self.default_dir = os.path.expanduser("~")
        
        self.init_ui()
        self.restore_settings()

    def init_ui(self):
        self.setWindowTitle("CsvTranslator - CSV 批次翻譯工具")
        self.resize(1100, 750)
        self.setMinimumSize(950, 600)
        
        # 主視窗佈局設定
        main_widget = QWidget()
        main_widget.setObjectName("mainContainer")
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ----------------- 左側面板：參數與設定 -----------------
        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_panel.setFixedWidth(420)
        
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(15)

        # 標題
        lbl_title = QLabel("CsvTranslator")
        lbl_title.setObjectName("appTitle")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(lbl_title)

        # 1. 檔案與路徑設定
        grp_files = QFrame()
        grp_files.setObjectName("grpFrame")
        grp_files_layout = QVBoxLayout(grp_files)
        grp_files_layout.setSpacing(8)
        
        lbl_files_sec = QLabel("檔案與路徑設定")
        lbl_files_sec.setObjectName("sectionHeader")
        grp_files_layout.addWidget(lbl_files_sec)

        lbl_src = QLabel("來源 CSV 檔案 (*.csv)：")
        grp_files_layout.addWidget(lbl_src)
        src_path_layout = QHBoxLayout()
        self.txt_src_path = QLineEdit()
        self.txt_src_path.setPlaceholderText("請選擇或輸入來源 CSV 檔案...")
        self.txt_src_path.textChanged.connect(self.on_source_file_changed)
        btn_src_browse = QPushButton("瀏覽...")
        btn_src_browse.setObjectName("btnBrowse")
        btn_src_browse.clicked.connect(self.browse_source_file)
        src_path_layout.addWidget(self.txt_src_path)
        src_path_layout.addWidget(btn_src_browse)
        grp_files_layout.addLayout(src_path_layout)

        lbl_out = QLabel("輸出 CSV 檔案 (*.csv)：")
        grp_files_layout.addWidget(lbl_out)
        out_path_layout = QHBoxLayout()
        self.txt_out_path = QLineEdit()
        self.txt_out_path.setPlaceholderText("請選擇或輸入輸出檔案路徑...")
        btn_out_browse = QPushButton("瀏覽...")
        btn_out_browse.setObjectName("btnBrowse")
        btn_out_browse.clicked.connect(self.browse_output_file)
        out_path_layout.addWidget(self.txt_out_path)
        out_path_layout.addWidget(btn_out_browse)
        grp_files_layout.addLayout(out_path_layout)

        left_layout.addWidget(grp_files)

        grp_params = QFrame()
        grp_params.setObjectName("grpFrame")
        grp_params_layout = QVBoxLayout(grp_params)
        grp_params_layout.setSpacing(8)

        lbl_params_sec = QLabel("範圍與間隔時間設定")
        lbl_params_sec.setObjectName("sectionHeader")
        grp_params_layout.addWidget(lbl_params_sec)

        grid_params = QGridLayout()
        grid_params.setSpacing(10)

        # 起始行號
        lbl_start_row = QLabel("起始行號：")
        self.txt_start_row = QLineEdit("2")  # 預設起始為 2 (排除標頭)
        self.txt_start_row.setValidator(QIntValidator(1, 9999999))
        grid_params.addWidget(lbl_start_row, 0, 0)
        grid_params.addWidget(self.txt_start_row, 0, 1)

        # 結束行號
        lbl_end_row = QLabel("結束行號：")
        self.txt_end_row = QLineEdit()
        self.txt_end_row.setPlaceholderText("預設至檔尾")
        self.txt_end_row.setValidator(QIntValidator(1, 9999999))
        grid_params.addWidget(lbl_end_row, 0, 2)
        grid_params.addWidget(self.txt_end_row, 0, 3)

        # 來源列號
        lbl_src_col = QLabel("來源列號：")
        self.txt_src_col = QLineEdit("1")
        self.txt_src_col.setValidator(QIntValidator(1, 9999))
        grid_params.addWidget(lbl_src_col, 1, 0)
        grid_params.addWidget(self.txt_src_col, 1, 1)

        # 目標列號
        lbl_tgt_col = QLabel("目標列號：")
        self.txt_tgt_col = QLineEdit("2")
        self.txt_tgt_col.setValidator(QIntValidator(1, 9999))
        grid_params.addWidget(lbl_tgt_col, 1, 2)
        grid_params.addWidget(self.txt_tgt_col, 1, 3)

        # 批次間隔
        lbl_batch_interval = QLabel("批次間隔(秒)：")
        self.txt_batch_interval = QLineEdit("10")
        self.txt_batch_interval.setValidator(QIntValidator(10, 30))
        grid_params.addWidget(lbl_batch_interval, 2, 0)
        grid_params.addWidget(self.txt_batch_interval, 2, 1)

        # 單筆間隔
        lbl_single_interval = QLabel("單筆間隔(秒)：")
        self.txt_single_interval = QLineEdit("1")
        self.txt_single_interval.setValidator(QIntValidator(1, 5))
        grid_params.addWidget(lbl_single_interval, 2, 2)
        grid_params.addWidget(self.txt_single_interval, 2, 3)

        grp_params_layout.addLayout(grid_params)
        left_layout.addWidget(grp_params)

        # 3. 語言設定
        grp_lang = QFrame()
        grp_lang.setObjectName("grpFrame")
        grp_lang_layout = QVBoxLayout(grp_lang)
        grp_lang_layout.setSpacing(8)

        lbl_lang_sec = QLabel("翻譯語言設定")
        lbl_lang_sec.setObjectName("sectionHeader")
        grp_lang_layout.addWidget(lbl_lang_sec)

        grid_lang = QGridLayout()
        grid_lang.setSpacing(10)

        # 支援語言清單：en, zh-TW, zh-CN, ja, ko
        self.langs = [
            ("en", "en (英文)"),
            ("zh-TW", "zh-TW (繁中)"),
            ("zh-CN", "zh-CN (簡中)"),
            ("ja", "ja (日文)"),
            ("ko", "ko (韓文)"),
        ]

        lbl_src_lang = QLabel("來源語言：")
        self.cb_src_lang = QComboBox()
        for code, name in self.langs:
            self.cb_src_lang.addItem(name, code)
        self.cb_src_lang.setCurrentIndex(0) # 預設英文

        lbl_tgt_lang = QLabel("目標語言：")
        self.cb_tgt_lang = QComboBox()
        for code, name in self.langs:
            self.cb_tgt_lang.addItem(name, code)
        self.cb_tgt_lang.setCurrentIndex(1) # 預設繁中

        grid_lang.addWidget(lbl_src_lang, 0, 0)
        grid_lang.addWidget(self.cb_src_lang, 0, 1)
        grid_lang.addWidget(lbl_tgt_lang, 1, 0)
        grid_lang.addWidget(self.cb_tgt_lang, 1, 1)

        grp_lang_layout.addLayout(grid_lang)
        left_layout.addWidget(grp_lang)

        # 4. 開始與停止控制
        left_layout.addStretch()
        
        self.btn_start = QPushButton("開始翻譯")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.clicked.connect(self.start_translation)
        left_layout.addWidget(self.btn_start)

        main_layout.addWidget(left_panel)

        # ----------------- 右側面板：預覽、進度與日誌 -----------------
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)

        # A. 來源檔案預覽
        grp_preview = QFrame()
        grp_preview.setObjectName("rightFrame")
        grp_preview_layout = QVBoxLayout(grp_preview)
        grp_preview_layout.setContentsMargins(15, 15, 15, 15)
        grp_preview_layout.setSpacing(8)

        lbl_preview_title = QLabel("來源檔案預覽 (前 10 行)")
        lbl_preview_title.setObjectName("sectionHeader")
        grp_preview_layout.addWidget(lbl_preview_title)

        self.table_preview = QTableWidget()
        self.table_preview.setRowCount(0)
        self.table_preview.setColumnCount(0)
        self.table_preview.horizontalHeader().setDefaultSectionSize(110)
        self.table_preview.verticalHeader().setDefaultSectionSize(28)
        grp_preview_layout.addWidget(self.table_preview)

        self.lbl_preview_status = QLabel("尚未選擇來源 CSV 檔案")
        self.lbl_preview_status.setObjectName("previewStatus")
        grp_preview_layout.addWidget(self.lbl_preview_status)

        right_panel.addWidget(grp_preview, stretch=4)

        # B. 執行狀態與日誌
        grp_status = QFrame()
        grp_status.setObjectName("rightFrame")
        grp_status_layout = QVBoxLayout(grp_status)
        grp_status_layout.setContentsMargins(15, 15, 15, 15)
        grp_status_layout.setSpacing(8)

        lbl_log_title = QLabel("執行狀態與日誌")
        lbl_log_title.setObjectName("sectionHeader")
        grp_status_layout.addWidget(lbl_log_title)

        # 進度、計時與日誌文字顯示
        status_info_layout = QHBoxLayout()
        self.lbl_progress_info = QLabel("進度：0 / 0 筆 (0%)")
        self.lbl_time_info = QLabel("已用時間：00:00:00")
        self.lbl_task_status = QLabel("狀態：就緒")
        self.lbl_task_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        status_info_layout.addWidget(self.lbl_progress_info)
        status_info_layout.addWidget(self.lbl_time_info)
        status_info_layout.addWidget(self.lbl_task_status)
        grp_status_layout.addLayout(status_info_layout)

        # 進度、計時與日誌文字顯示
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        grp_status_layout.addWidget(self.progress_bar)

        # 結束行號
        self.txt_log = QTextEdit()
        self.txt_log.setObjectName("logConsole")
        self.txt_log.setReadOnly(True)
        grp_status_layout.addWidget(self.txt_log)

        right_panel.addWidget(grp_status, stretch=5)

        main_layout.addLayout(right_panel, stretch=1)

        # 載入 QSS 樣式設定
        self.apply_style()

    def apply_style(self):
        qss = """
        /* 主視窗樣式 */
        QMainWindow {
            background-color: #1a1b26;
        }
        QWidget#mainContainer {
            background-color: #1a1b26;
        }

        /* 面板樣式 */
        QFrame#leftPanel {
            background-color: #20212e;
            border: 1px solid #2f3047;
            border-radius: 12px;
        }
        QFrame#grpFrame {
            background-color: #242538;
            border: 1px solid #2f3047;
            border-radius: 8px;
            padding: 5px;
        }
        QFrame#rightFrame {
            background-color: #20212e;
            border: 1px solid #2f3047;
            border-radius: 12px;
        }

        /* 標籤字型與文字樣式 */
        QLabel {
            color: #a9b1d6;
            font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
            font-size: 13px;
        }
        QLabel#appTitle {
            font-size: 22px;
            font-weight: bold;
            color: #7aa2f7;
            margin-bottom: 10px;
            font-family: "Segoe UI", "Microsoft JhengHei", sans-serif;
        }
        QLabel#sectionHeader {
            font-size: 14px;
            font-weight: bold;
            color: #7aa2f7;
            border-bottom: 1px solid #2f3047;
            padding-bottom: 5px;
            margin-bottom: 5px;
        }
        QLabel#previewStatus {
            font-size: 11px;
            color: #565f89;
        }

        /* 輸入框與下拉選單 */
        QLineEdit, QComboBox {
            background-color: #16161e;
            border: 1px solid #2f3047;
            border-radius: 6px;
            padding: 7px;
            color: #c0caf5;
        }
        QLineEdit:focus, QComboBox:focus {
            border: 1px solid #7aa2f7;
        }
        QComboBox::drop-down {
            border: 0px;
        }

        /* 按鈕樣式 */
        QPushButton {
            background-color: #414868;
            color: #c0caf5;
            border: none;
            border-radius: 6px;
            padding: 8px 15px;
            font-weight: bold;
            font-size: 13px;
        }
        QPushButton:hover {
            background-color: #565f89;
        }
        QPushButton:pressed {
            background-color: #3b4261;
        }
        QPushButton#btnStart {
            background-color: #7aa2f7;
            color: #1a1b26;
            font-size: 15px;
            padding: 12px;
        }
        QPushButton#btnStart:hover {
            background-color: #89ddff;
        }
        QPushButton#btnStart:disabled {
            background-color: #24283b;
            color: #565f89;
        }

        QPushButton#btnBrowse {
            background-color: #3b4261;
            font-size: 12px;
            padding: 7px 12px;
        }
        QPushButton#btnBrowse:hover {
            background-color: #414868;
        }

        /* 表格樣式 */
        QTableWidget {
            background-color: #16161e;
            color: #a9b1d6;
            border: 1px solid #2f3047;
            gridline-color: #232433;
            border-radius: 8px;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QTableWidget::item:selected {
            background-color: #2e3c64;
            color: #c0caf5;
        }
        QHeaderView::section {
            background-color: #20212e;
            color: #7aa2f7;
            padding: 6px;
            border: 1px solid #2f3047;
            font-weight: bold;
        }
        QScrollBar:vertical {
            background-color: #16161e;
            width: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background-color: #3b4261;
            min-height: 20px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #414868;
        }

        /* 進度條樣式 */
        QProgressBar {
            border: 1px solid #2f3047;
            border-radius: 6px;
            background-color: #16161e;
            text-align: center;
            color: #c0caf5;
            font-weight: bold;
            font-size: 11px;
            height: 18px;
        }
        QProgressBar::chunk {
            background-color: #9ece6a;
            border-radius: 5px;
        }

            "WARNING": "#e0af68",    # 警告
        QTextEdit#logConsole {
            background-color: #16161e;
            border: 1px solid #2f3047;
            border-radius: 8px;
            font-family: "Consolas", "Courier New", monospace;
            font-size: 12px;
            color: #9ece6a;
            padding: 8px;
        }
        """
        self.setStyleSheet(qss)

    # ----------------- 事件與邏輯處理函數 -----------------
    def browse_source_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇來源 CSV 檔案", self.default_dir, "CSV 檔案 (*.csv);;所有檔案 (*)"
        )
        if file_path:
            self.txt_src_path.setText(file_path)
            self.default_dir = os.path.dirname(os.path.abspath(file_path))
            # 自動推導輸出檔案路徑
            if not self.txt_out_path.text().strip():
                dir_name, file_name = os.path.split(file_path)
                name, ext = os.path.splitext(file_name)
                default_out = os.path.join(dir_name, f"{name}_translated{ext}")
                self.txt_out_path.setText(default_out)

    def browse_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "選擇儲存輸出 CSV 檔案", self.default_dir, "CSV 檔案 (*.csv);;所有檔案 (*)"
        )
        if file_path:
            self.txt_out_path.setText(file_path)
            self.default_dir = os.path.dirname(os.path.abspath(file_path))

    def on_source_file_changed(self, file_path):
        if not file_path.strip() or not os.path.exists(file_path):
            self.table_preview.clear()
            self.table_preview.setRowCount(0)
            self.table_preview.setColumnCount(0)
            self.lbl_preview_status.setText("請選擇來源檔案，或來源檔案不存在")
            self.txt_end_row.setPlaceholderText("預設至檔尾")
            return
        
        self.load_csv_preview(file_path)

    def load_csv_preview(self, file_path):
        try:
            encoding = detect_encoding(file_path)
            delimiter = detect_delimiter(file_path, encoding)
            
            rows = []
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                reader = csv.reader(f, delimiter=delimiter)
                for i, row in enumerate(reader):
                    if i >= 10:
                        break
                    rows.append(row)
            
            if not rows:
                self.lbl_preview_status.setText("來源檔案為空，無法進行預覽")
                return

            max_cols = max(len(r) for r in rows)
            
            self.table_preview.clear()
            self.table_preview.setRowCount(len(rows))
            self.table_preview.setColumnCount(max_cols)
            
            # 設定列與行標頭
            col_headers = [f"第 {i+1} 欄" for i in range(max_cols)]
            self.table_preview.setHorizontalHeaderLabels(col_headers)
            
            row_headers = [f"第 {i+1} 行" for i in range(len(rows))]
            self.table_preview.setVerticalHeaderLabels(row_headers)
            
            for r_idx, row in enumerate(rows):
                for c_idx in range(max_cols):
                    val = row[c_idx] if c_idx < len(row) else ""
                    item = QTableWidgetItem(val)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    self.table_preview.setItem(r_idx, c_idx, item)
            
            self.table_preview.resizeColumnsToContents()
            self.lbl_preview_status.setText(f"預覽載入完成 (編碼: {encoding}, 分隔符: '{delimiter}')")
            
            # 自動推導輸出檔案路徑
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                total_rows = sum(1 for _ in csv.reader(f, delimiter=delimiter))
            self.txt_end_row.setPlaceholderText(f"預設至檔尾 ({total_rows})")

        except Exception as e:
            self.lbl_preview_status.setText(f"載入預覽失敗: {str(e)}")

    def append_log(self, level, message):
        color_map = {
            "INFO": "#c0caf5",       # 一般日誌
            "SUCCESS": "#9ece6a",    # 成功
            "WARNING": "#e0af68",    # 警告
            "ERROR": "#f7768e"       # 錯誤
        }
        color = color_map.get(level, "#c0caf5")
        timestamp = time.strftime("[%H:%M:%S]")
        log_html = f'<font color="#565f89">{timestamp}</font> <font color="{color}">[{level}] {message}</font>'
        
        # 將新日誌插入至日誌最上方 (倒序)
        cursor = self.txt_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.insertHtml(log_html)
        cursor.insertBlock()
        
        # 將新日誌插入至日誌最上方 (倒序)
        if self.txt_log.document().blockCount() > 10001:
            end_cursor = self.txt_log.textCursor()
            end_cursor.movePosition(end_cursor.MoveOperation.End)
            end_cursor.movePosition(end_cursor.MoveOperation.PreviousBlock, end_cursor.MoveMode.KeepAnchor)
            end_cursor.removeSelectedText()

    def start_translation(self):
        # 如果正在翻譯，按按鈕則觸發 STOP 中斷
        if self.btn_start.text() == "STOP":
            if self.worker:
                self.btn_start.setText("正在停止...")
                self.btn_start.setEnabled(False)
                self.lbl_task_status.setText("狀態：正在中斷工作...")
                self.worker.cancel()
            return

        # 檢查輸入欄位範圍
        src_path = self.txt_src_path.text().strip()
        out_path = self.txt_out_path.text().strip()
        
        if not src_path or not os.path.exists(src_path):
            QMessageBox.warning(self, "輸入錯誤", "請選擇正確的來源 CSV 檔案路徑")
            return
        if not out_path:
            QMessageBox.warning(self, "輸入錯誤", "請指定輸出檔案路徑")
            return
        
        # 讀取並驗證行數欄位
        try:
            start_row = int(self.txt_start_row.text())
            if start_row < 1:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "輸入錯誤", "起始行號必須是大於或等於 1 的正整數")
            return

        end_row = None
        if self.txt_end_row.text().strip():
            try:
                end_row = int(self.txt_end_row.text())
                if end_row < start_row:
                    QMessageBox.warning(self, "輸入錯誤", "結束行號不能小於起始行號")
                    return
            except ValueError:
                QMessageBox.warning(self, "輸入錯誤", "結束行號必須是正整數")
                return

        try:
            src_col = int(self.txt_src_col.text())
            tgt_col = int(self.txt_tgt_col.text())
            if src_col < 1 or tgt_col < 1:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "輸入錯誤", "來源列號與目標列號必須是大於或等於 1 的正整數")
            return

        src_lang = self.cb_src_lang.currentData()
        tgt_lang = self.cb_tgt_lang.currentData()

        # 驗證批次間隔與單筆間隔
        try:
            batch_interval = int(self.txt_batch_interval.text())
            if not (10 <= batch_interval <= 30):
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "輸入錯誤", "批次間隔時間必須在 10 至 30 秒之間")
            return

        try:
            single_interval = int(self.txt_single_interval.text())
            if not (1 <= single_interval <= 5):
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "輸入錯誤", "單筆間隔時間必須在 1 至 5 秒之間")
            return

        # 清空舊 UI 顯示狀態
        self.txt_log.clear()
        self.progress_bar.setValue(0)
        self.lbl_progress_info.setText("進度：0 / 0 筆 (0%)")
        self.lbl_task_status.setText("狀態：翻譯中...")
        
        # 記錄開始時間
        self.start_time = time.time()
        self.timer.start(1000)

        # 如果正在翻譯，按按鈕則觸發 STOP 中斷
        self.btn_start.setText("STOP")
        self.btn_start.setStyleSheet("background-color: #f7768e; color: #1a1b26;")

        self.set_ui_enabled(False)

        # 初始化背景翻譯工作器
        self.worker = CSVTranslatorWorker(
            source_path=src_path,
            output_path=out_path,
            start_row=start_row,
            end_row=end_row,
            source_col=src_col,
            target_col=tgt_col,
            source_lang=src_lang,
            target_lang=tgt_lang,
            batch_interval=batch_interval,
            single_interval=single_interval
        )
        self.worker.progress_updated.connect(self.on_worker_progress)
        self.worker.status_updated.connect(self.lbl_task_status.setText)
        self.worker.log_emitted.connect(self.append_log)
        self.worker.finished_successfully.connect(self.on_worker_success)
        self.worker.finished_with_error.connect(self.on_worker_error)
        
        self.worker.start()

    def on_worker_progress(self, current, total):
        self.progress_bar.setValue(int(current / total * 100))
        self.lbl_progress_info.setText(f"進度：{current} / {total} 筆 ({int(current/total*100)}%)")

    def update_elapsed_time(self):
        elapsed = int(time.time() - self.start_time)
        hrs = elapsed // 3600
        mins = (elapsed % 3600) // 60
        secs = elapsed % 60
        self.lbl_time_info.setText(f"已用時間：{hrs:02d}:{mins:02d}:{secs:02d}")

    def on_worker_success(self, out_path):
        self.timer.stop()
        self.lbl_task_status.setText("狀態：完成")
        self.set_ui_enabled(True)
        QMessageBox.information(self, "成功", f"翻譯完成！\n檔案已儲存至：\n{out_path}")

    def on_worker_error(self, err_msg):
        self.timer.stop()
        self.lbl_task_status.setText("狀態：錯誤")
        self.set_ui_enabled(True)
        QMessageBox.critical(self, "翻譯中斷", f"翻譯過程發生錯誤：\n{err_msg}")

    def set_ui_enabled(self, enabled):
        self.txt_src_path.setEnabled(enabled)
        self.txt_out_path.setEnabled(enabled)
        self.txt_start_row.setEnabled(enabled)
        self.txt_end_row.setEnabled(enabled)
        self.txt_src_col.setEnabled(enabled)
        self.txt_tgt_col.setEnabled(enabled)
        self.txt_batch_interval.setEnabled(enabled)
        self.txt_single_interval.setEnabled(enabled)
        self.cb_src_lang.setEnabled(enabled)
        self.cb_tgt_lang.setEnabled(enabled)
        
        if enabled:
            self.btn_start.setEnabled(True)
            self.btn_start.setText("開始翻譯")
            self.btn_start.setStyleSheet("") # 恢復 QSS 原生樣式

    def restore_settings(self):
        if not os.path.exists(self.settings_path):
            return
        try:
            settings = QSettings(self.settings_path, QSettings.Format.IniFormat)
            
            geom = settings.value("geometry")
            if geom is not None:
                self.restoreGeometry(geom)
            
            # 恢復視窗最大化狀態
            is_max = settings.value("isMaximized")
            if is_max == "true" or is_max is True:
                self.showMaximized()
            
            # 讀取工作資料夾路徑
            self.default_dir = settings.value("default_dir", os.path.expanduser("~"))
            
            # 恢復使用者輸入欄位設定
            self.txt_start_row.setText(settings.value("start_row", "2"))
            self.txt_end_row.setText(settings.value("end_row", ""))
            self.txt_src_col.setText(settings.value("src_col", "1"))
            self.txt_tgt_col.setText(settings.value("tgt_col", "2"))

            # 讀取批次與單筆間隔時間並驗證其合法性
            batch_val = settings.value("batch_interval", "10")
            if not batch_val.isdigit() or not (10 <= int(batch_val) <= 30):
                batch_val = "10"
            self.txt_batch_interval.setText(batch_val)

            single_val = settings.value("single_interval", "1")
            if not single_val.isdigit() or not (1 <= int(single_val) <= 5):
                single_val = "1"
            self.txt_single_interval.setText(single_val)
            
            src_lang = settings.value("src_lang", "en")
            idx_src = self.cb_src_lang.findData(src_lang)
            if idx_src != -1:
                self.cb_src_lang.setCurrentIndex(idx_src)
                
            tgt_lang = settings.value("tgt_lang", "zh-TW")
            idx_tgt = self.cb_tgt_lang.findData(tgt_lang)
            if idx_tgt != -1:
                self.cb_tgt_lang.setCurrentIndex(idx_tgt)
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            settings = QSettings(self.settings_path, QSettings.Format.IniFormat)
            settings.setValue("geometry", self.saveGeometry())
            settings.setValue("isMaximized", self.isMaximized())
            settings.setValue("default_dir", self.default_dir)
            settings.setValue("start_row", self.txt_start_row.text())
            settings.setValue("end_row", self.txt_end_row.text())
            settings.setValue("src_col", self.txt_src_col.text())
            settings.setValue("tgt_col", self.txt_tgt_col.text())
            settings.setValue("batch_interval", self.txt_batch_interval.text())
            settings.setValue("single_interval", self.txt_single_interval.text())
            settings.setValue("src_lang", self.cb_src_lang.currentData())
            settings.setValue("tgt_lang", self.cb_tgt_lang.currentData())
        except Exception:
            pass
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    font = QFont("Microsoft JhengHei", 9)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
