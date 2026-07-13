import time
from PyQt6.QtCore import QObject, pyqtSignal
from common_data.task_status import TaskStatus
from ai.ai_utils import build_final_prompt
from ai.ai_client import generate_local_ai, generate_google_ai


class CSVAIWorker(QObject):
    """
    CSVAIWorker — 在背景執行緒中遍歷 CSV 資料、呼叫 AI 客戶端並更新資料。

    【架構規範】：此 Worker 繼承自 QObject（非 QThread），由主程式的
    PluginHostAdapter 統一建立 QThread 並管理生命週期。
    外掛透過 self.api.run_worker(worker, ...) 委託啟動，
    嚴禁外掛自行呼叫 worker.start()。

    標準接口信號（run_worker 架構必要）：
      progress(current, total): 進度更新，主程式自動套 ThrottledProgress 節流。
      finished(status): 任務結束，"finished" | "error" | "cancelled"。

    業務信號（外掛面板可自行連接）：
      status_updated(status_str): 更新 UI 狀態列字串。
      log_emitted(level, msg): 發送日誌訊息到日誌面板。
      data_changed(): 每次有欄位被寫入時，通知表格 UI 進行重繪。
    """

    # ── 標準接口信號（run_worker 架構必要）────────────────────────────────────
    progress = pyqtSignal(int, int)      # current, total
    finished = pyqtSignal(TaskStatus)           # TaskStatus Enum

    # ── 業務信號（外掛面板可連接）─────────────────────────────────────────────
    status_updated = pyqtSignal(str)
    log_emitted = pyqtSignal(str, str)   # level, message
    data_changed = pyqtSignal()

    def __init__(self, all_rows, visible_row_indices, is_header,
                 target_col_name, user_prompt, ai_service,
                 google_api_key="", google_model="",
                 local_server_url="", local_model="",
                 num_ctx=4096, temperature=0.7, headers=None):
        super().__init__()
        self.all_rows = all_rows
        self.visible_row_indices = visible_row_indices
        self.is_header = is_header
        self.target_col_name = target_col_name
        self.user_prompt = user_prompt
        self.ai_service = ai_service
        self.google_api_key = google_api_key
        self.google_model = google_model
        self.local_server_url = local_server_url
        self.local_model = local_model
        self.num_ctx = num_ctx
        self.temperature = temperature
        self.headers = list(headers) if headers is not None else []

        self._is_cancelled = False
        # 供面板在 finished("error") 時讀取錯誤詳情
        self._last_error: str = ""

    def cancel(self) -> None:
        """供主程式呼叫，用以要求終止背景處理迴圈。"""
        self._is_cancelled = True

    def run(self) -> None:
        """Worker 工作入口，由主程式透過 QThread.started 信號觸發。"""
        try:
            self.status_updated.emit("準備 AI 欄位對映...")
            self.log_emitted.emit("INFO", "開始執行 AI 批次處理任務...")

            if not self.all_rows:
                self._last_error = "沒有可載入的 CSV 資料"
                self.log_emitted.emit("ERROR", self._last_error)
                self.finished.emit(TaskStatus.ERROR)
                return

            # 1. 取得標準 headers
            if self.headers:
                headers = self.headers
            else:
                if self.is_header:
                    headers = [str(cell).strip() for cell in self.all_rows[0]]
                else:
                    headers = [str(i + 1) for i in range(len(self.all_rows[0]))]

            # 2. 判定目標寫回欄位索引並驗證有效性
            try:
                target_col_idx = int(self.target_col_name)
                if target_col_idx < 0:
                    raise ValueError()
            except (ValueError, TypeError):
                self._last_error = "目標輸出欄號格式不正確"
                self.log_emitted.emit("ERROR", self._last_error)
                self.finished.emit(TaskStatus.ERROR)
                return

            # 若發現輸出欄位超出有效範圍，直接報錯
            if target_col_idx >= len(self.all_rows[0]):
                self._last_error = f"目標輸出欄號 '{target_col_idx + 1}' 超出目前 CSV 的有效範圍，請先新增欄位或重新選擇！"
                self.log_emitted.emit("ERROR", self._last_error)
                self.finished.emit(TaskStatus.ERROR)
                return

            # 檢查 Prompt 內引用的欄位是否都存在於 headers 中
            from ai.ai_utils import extract_referenced_fields
            referenced_fields = extract_referenced_fields(self.user_prompt)
            missing_fields = [f for f in referenced_fields if f not in headers]
            if missing_fields:
                self._last_error = f"自訂 Prompt 中引用了不存在於目前 CSV 的欄位：{', '.join(missing_fields)}"
                self.log_emitted.emit("ERROR", self._last_error)
                self.finished.emit(TaskStatus.ERROR)
                return

            # 3. 取得需要執行的列索引清單，排列表頭行本身
            run_indices = [idx for idx in self.visible_row_indices]
            if self.is_header and 0 in run_indices:
                run_indices.remove(0)

            total_count = len(run_indices)
            processed_count = 0

            if total_count == 0:
                self.log_emitted.emit("WARNING", "沒有選定任何有效資料列進行處理")
                self.finished.emit(TaskStatus.FINISHED)
                return

            self.status_updated.emit("執行中...")

            # 4. 開始遍歷每一列進行處理
            for r_idx in run_indices:
                if self._is_cancelled:
                    self.log_emitted.emit("WARNING", "使用者中止了 AI 處理任務")
                    self.finished.emit(TaskStatus.CANCELLED)
                    return

                row = self.all_rows[r_idx]

                # 組裝當前行的 dict 對照
                row_data = {}
                for idx, h_name in enumerate(headers):
                    if idx < len(row):
                        row_data[h_name] = row[idx]
                    else:
                        row_data[h_name] = ""

                # 調用純靜態 utility 進行 prompt 字串拼裝
                final_prompt = build_final_prompt(self.user_prompt, row_data)

                self.log_emitted.emit("INFO", f"正在處理第 {r_idx + 1} 行... 呼叫 Prompt: {final_prompt[:80]}...")

                try:
                    if self.ai_service == "Google":
                        result = generate_google_ai(
                            api_key=self.google_api_key,
                            model=self.google_model,
                            prompt=final_prompt,
                            temperature=self.temperature
                        )
                    else:
                        result = generate_local_ai(
                            server_url=self.local_server_url,
                            model=self.local_model,
                            prompt=final_prompt,
                            num_ctx=self.num_ctx,
                            temperature=self.temperature
                        )

                    # 將回傳結果寫入指定目標列中
                    while len(row) <= target_col_idx:
                        row.append("")
                    row[target_col_idx] = result.strip()

                    self.log_emitted.emit("SUCCESS", f"第 {r_idx + 1} 行處理成功！")
                    self.data_changed.emit()

                except Exception as ex:
                    raise RuntimeError(f"第 {r_idx + 1} 行處理失敗: {str(ex)}")

                processed_count += 1
                self.progress.emit(processed_count, total_count)

                # 為了避免 API 呼叫過於密集，加一個微小 delay
                time.sleep(0.1)

            self.status_updated.emit("完成")
            self.log_emitted.emit("SUCCESS", "AI 批次處理任務已結束！")
            self.finished.emit(TaskStatus.FINISHED)

        except Exception as e:
            self._last_error = str(e)
            self.log_emitted.emit("ERROR", f"AI背景任務異常中止: {str(e)}")
            self.finished.emit(TaskStatus.ERROR)
