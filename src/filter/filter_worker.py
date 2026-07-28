import re
import time
import unicodedata
from PyQt6.QtCore import QObject, pyqtSignal
from common_data.task_status import TaskStatus
from filter.filter_config import CompareMethod

# 全角數字/符號轉換表
FULL_TO_HALF_MAP = {
    '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
    '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
    '．': '.', '＋': '+', '－': '-', 'ｅ': 'e', 'Ｅ': 'E',
    ' ': ' ', '　': ' '  # 全形空格
}
FULL_TO_HALF_TRANS = str.maketrans(FULL_TO_HALF_MAP)

# 常用日文全漢字字典
JAPANESE_KANJI_WORDS = {
    "東京", "京都", "大阪", "無料", "割引", "新幹線", "非常口", "切符", "交番", 
    "案内", "名簿", "消去", "確認", "返信", "送信", "受信", "設定", "登録", 
    "取消", "終了", "開始", "新規", "更新", "変更", "削除", "印刷", "保存",
    "読込", "書込", "編集", "検索", "置換", "選擇", "全選", "移動", "複製",
    "貼付", "挿入", "追加", "作成", "開発", "設計", "計画", "実行", "停止"
}

class FilterWorker(QObject):
    """
    FilterWorker — 在背景執行緒中執行 CSV 列過濾運算。

    【架構規範】：此 Worker 繼承自 QObject（非 QThread），由主程式的
    PluginHostAdapter 統一建立 QThread 並管理生命週期。

    標準接口信號（run_worker 架構必要）：
      progress(current, total): 進度更新，主程式自動套 ThrottledProgress 節流。
      finished(status): 任務結束， "finished" | "error" | "cancelled"。

    業務信號（外掛面板可自行連接）：
      filter_completed(matched_indices, elapsed_time): 過濾完成，帶回結果與耗時。
      log_emitted(level, msg): 發送日誌訊息到日誌面板。
    """

    # ── 標準接口信號（run_worker 架構必要）────────────────────────────────────────────
    progress = pyqtSignal(int, int)          # current, total
    finished = pyqtSignal(TaskStatus)               # TaskStatus Enum

    # ── 業務信號（外掛面板可連接）───────────────────────────────────────────────────
    filter_completed = pyqtSignal(object, float)  # matched_indices, elapsed_time
    log_emitted = pyqtSignal(str, str)            # level, message

    def __init__(self, all_rows, start_row, end_row, is_header, 
                 filter_config, parent=None):
        super().__init__(parent)
        self.all_rows = all_rows
        self.start_row = start_row
        self.end_row = end_row
        self.is_header = is_header
        
        self.filter_config = filter_config
        
        self._is_cancelled = False
        # 供面板在 finished("error") 時讀取錯誤詳情
        self._last_error: str = ""

        # 初始化 OpenCC 轉換器 (離線字典載入)
        try:
            from opencc import OpenCC
            self.cc_t2s = OpenCC('t2s')
            self.cc_s2t = OpenCC('s2t')
        except Exception:
            self.cc_t2s = None
            self.cc_s2t = None

    def cancel(self) -> None:
        """供主程式呼叫，用以要求終止過濾迴圈。"""
        self._is_cancelled = True

    def check_row_match(self, row, compare_col, compare_method, compare_target, compare_value, regex_pattern, range_start=None, range_end=None, invert=False):
        # 決定比對範圍欄位索引集合
        if compare_col == -1:  # 所有欄位
            cols_to_check = list(range(len(row)))
        elif compare_col == -2:  # 欄位範圍
            start_c = range_start if range_start is not None else 0
            end_c = range_end if range_end is not None else len(row) - 1
            
            # 防呆邊界
            start_c = max(0, start_c)
            end_c = min(len(row) - 1, end_c)
            
            cols_to_check = list(range(start_c, end_c + 1))
        else:
            # 特定欄位 (整數)
            cols_to_check = [compare_col]

        # 決定比對目標值
        if compare_method == CompareMethod.BELONG:
            target_val = compare_value
        elif compare_target == -1:  # 手動輸入
            target_val = compare_value
        else:
            # 特定欄位的值 (整數)
            t_idx = compare_target
            target_val = row[t_idx] if t_idx < len(row) else ""

        is_match = False
        
        if compare_method == CompareMethod.FULL_MATCH:
            is_match = any((row[c] if c < len(row) else "") == target_val for c in cols_to_check)
        elif compare_method == CompareMethod.CONTAINS:
            is_match = any(target_val in (row[c] if c < len(row) else "") for c in cols_to_check)
        elif compare_method == CompareMethod.REGEX:
            if compare_target == -1 and regex_pattern:
                is_match = any(bool(regex_pattern.search(row[c] if c < len(row) else "")) for c in cols_to_check)
            else:
                # 欄位比對當作正規表達式
                try:
                    t_regex = re.compile(target_val)
                    is_match = any(bool(t_regex.search(row[c] if c < len(row) else "")) for c in cols_to_check)
                except re.error:
                    is_match = False
        elif compare_method == CompareMethod.BELONG:
            is_match = any(self.is_belong_match(row[c] if c < len(row) else "", compare_target, target_val) for c in cols_to_check)
                    
        return not is_match if invert else is_match

    def is_belong_match(self, text, target, sub_value):
        if target == "語系":
            if sub_value == "中文":
                if not any('\u4e00' <= c <= '\u9fff' for c in text):
                    return False
                if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text):
                    return False
                return True
                
            elif sub_value == "繁體中文":
                if not any('\u4e00' <= c <= '\u9fff' for c in text):
                    return False
                if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text):
                    return False
                # 使用 OpenCC
                if self.cc_s2t:
                    for c in text:
                        if '\u4e00' <= c <= '\u9fff':
                            if self.cc_s2t.convert(c) == c:
                                return True
                    return False
                else:
                    # big5 檢查
                    for c in text:
                        if '\u4e00' <= c <= '\u9fff':
                            try:
                                c.encode('big5')
                                return True
                            except UnicodeEncodeError:
                                pass
                    return False
                    
            elif sub_value == "簡體中文":
                if not any('\u4e00' <= c <= '\u9fff' for c in text):
                    return False
                if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text):
                    return False
                # 使用 OpenCC
                if self.cc_t2s:
                    for c in text:
                        if '\u4e00' <= c <= '\u9fff':
                            if self.cc_t2s.convert(c) == c:
                                return True
                    return False
                else:
                    # gb2312 檢查
                    for c in text:
                        if '\u4e00' <= c <= '\u9fff':
                            try:
                                c.encode('gb2312')
                                return True
                            except UnicodeEncodeError:
                                pass
                    return False
                    
            elif sub_value == "日文(專字)":
                for c in text:
                    if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff':
                        return True
                    if c in ('\u3005', '\u3006', '\u3012', '\u303b', '\u303d', '\u3004'):  # 々, 〆, 〒, 〻, 〽, 〄
                        return True
                    if '\u4e00' <= c <= '\u9fff':
                        try:
                            c.encode('big5')
                            has_big5 = True
                        except UnicodeEncodeError:
                            has_big5 = False
                        try:
                            c.encode('gb2312')
                            has_gb2312 = True
                        except UnicodeEncodeError:
                            has_gb2312 = False
                        if not has_big5 and not has_gb2312:
                            return True
                return False
                
            elif sub_value == "日文(通用)":
                if self.is_belong_match(text, "語系", "日文(專字)"):
                    return True
                if not any('\u4e00' <= c <= '\u9fff' for c in text):
                    return False
                # 字典匹配
                kanji_blocks = re.findall(r'[\u4e00-\u9fff]+', text)
                for block in kanji_blocks:
                    L = len(block)
                    for length in range(2, min(5, L + 1)):
                        for start in range(L - length + 1):
                            substr = block[start:start+length]
                            if substr in JAPANESE_KANJI_WORDS:
                                return True
                return False
                
            elif sub_value == "韓文":
                return any('\uac00' <= c <= '\ud7af' or '\u1100' <= c <= '\u11ff' or '\u3130' <= c <= '\u318f' for c in text)
                
            elif sub_value == "英文":
                return any('a' <= c <= 'z' or 'A' <= c <= 'Z' for c in text)
                
            elif sub_value == "拉丁語系":
                return any(('\u0000' <= c <= '\u007f' and ('a' <= c <= 'z' or 'A' <= c <= 'Z')) or
                           '\u0080' <= c <= '\u00ff' or
                           '\u0100' <= c <= '\u017f' or
                           '\u0180' <= c <= '\u024f' for c in text)
                           
            elif sub_value == "其他語系":
                for c in text:
                    cat = unicodedata.category(c)
                    if cat.startswith('L'):
                        is_latin = ('\u0000' <= c <= '\u024f')
                        is_cjk = ('\u4e00' <= c <= '\u9fff')
                        is_kana = ('\u3040' <= c <= '\u30ff')
                        is_hangul = ('\uac00' <= c <= '\ud7af' or '\u1100' <= c <= '\u11ff' or '\u3130' <= c <= '\u318f')
                        if not (is_latin or is_cjk or is_kana or is_hangul):
                            return True
                return False
                
        elif target == "含數字":
            if sub_value == "半形":
                return any('0' <= c <= '9' for c in text)
            elif sub_value == "全半形":
                return any('0' <= c <= '9' or '０' <= c <= '９' for c in text)
            elif sub_value == "多國語言":
                return any(c.isnumeric() for c in text)
        elif target == "純數字":
            if sub_value == "半形":
                return bool(re.match(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$', text))
            elif sub_value == "全半形":
                converted = text.translate(FULL_TO_HALF_TRANS)
                return bool(re.match(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$', converted))
            elif sub_value == "多國語言":
                if not text:
                    return False
                norm = text.translate(str.maketrans({
                    '＋': '+', '－': '-', '．': '.',
                    'ｅ': 'e', 'Ｅ': 'E'
                }))
                if 'e' in norm or 'E' in norm:
                    parts = re.split(r'[eE]', norm, maxsplit=1)
                    if len(parts) != 2:
                        return False
                    base, exp = parts[0], parts[1]
                    if not exp:
                        return False
                    if exp.startswith('+') or exp.startswith('-'):
                        exp = exp[1:]
                    if not exp or not all(c.isnumeric() for c in exp):
                        return False
                    if not base:
                        return False
                    if base.startswith('+') or base.startswith('-'):
                        base = base[1:]
                    if not base:
                        return False
                    if '.' in base:
                        subparts = base.split('.', 1)
                        joined = subparts[0] + subparts[1]
                        if not joined or not all(c.isnumeric() for c in joined):
                            return False
                    else:
                        if not all(c.isnumeric() for c in base):
                            return False
                    return True
                else:
                    val = norm
                    if val.startswith('+') or val.startswith('-'):
                        val = val[1:]
                    if not val:
                        return False
                    if '.' in val:
                        subparts = val.split('.', 1)
                        joined = subparts[0] + subparts[1]
                        if not joined or not all(c.isnumeric() for c in joined):
                            return False
                    else:
                        if not all(c.isnumeric() for c in val):
                            return False
                    return True
                
        elif target == "文數字(無符號)":
            if not text:
                return False
            if sub_value == "半形":
                for c in text:
                    cat = unicodedata.category(c)
                    is_alnum = cat.startswith('L') or cat.startswith('N')
                    is_space = (c == ' ')
                    if not (is_alnum or is_space):
                        return False
                    w = unicodedata.east_asian_width(c)
                    if w in ('W', 'F'):
                        return False
                return True
            elif sub_value == "全半形":
                for c in text:
                    cat = unicodedata.category(c)
                    is_alnum = cat.startswith('L') or cat.startswith('N')
                    is_space = (c in (' ', '\u3000'))
                    if not (is_alnum or is_space):
                        return False
                return True
                
        elif target == "僅符號":
            if not text:
                return False
            if sub_value == "半形":
                for c in text:
                    cat = unicodedata.category(c)
                    if cat.startswith('L') or cat.startswith('N'):
                        return False
                    w = unicodedata.east_asian_width(c)
                    if w in ('W', 'F'):
                        return False
                return True
            elif sub_value == "全半形":
                for c in text:
                    cat = unicodedata.category(c)
                    if cat.startswith('L') or cat.startswith('N'):
                        return False
                return True
                
        return False

    def eval_logic_tree(self, node, rule_results):
        if not node:
            return True
        if node.op_type == "LEAF":
            idx = node.leaf_idx - 1
            if idx < len(rule_results):
                return rule_results[idx]
            return False
        elif node.op_type == "AND":
            return all(self.eval_logic_tree(c, rule_results) for c in node.children)
        elif node.op_type == "OR":
            return any(self.eval_logic_tree(c, rule_results) for c in node.children)
        elif node.op_type == "XOR":
            res = [self.eval_logic_tree(c, rule_results) for c in node.children]
            return sum(res) % 2 == 1
        return False

    def evaluate_general_rules(self, row, rules_cfg, tree, regex_patterns) -> bool:
        # 若無規則或無邏輯樹，則直接最佳化回傳 True
        if not rules_cfg or not tree:
            return True

        # 求解各單一規則結果
        rule_results = []
        for j, r_cfg in enumerate(rules_cfg):
            col = r_cfg.get("compare_col")
            method = r_cfg.get("compare_method", 0)
            if not isinstance(method, int):
                method = 0
            
            invert = r_cfg.get("invert", False)
            if not isinstance(invert, bool):
                invert = False

            match_res = self.check_row_match(
                row, col,
                method,
                r_cfg.get("compare_target"),
                r_cfg.get("compare_value"),
                regex_patterns[j],
                range_start=r_cfg.get("range_start"),
                range_end=r_cfg.get("range_end"),
                invert=invert
            )
            rule_results.append(match_res)
        
        # 遞迴運算 AST 邏輯樹
        return self.eval_logic_tree(tree, rule_results)

    def run(self):
        try:
            start_time = time.time()
            matched_indices = []

            try:
                from filter.logic_tree import logic_tree

                total_rows = len(self.all_rows)
                end_bound = self.end_row if self.end_row is not None else total_rows
                end_bound = min(end_bound, total_rows)

                rules_cfg = self.filter_config.get("rules", [])
                lt_cfg = self.filter_config.get("logic_tree")
                tree = logic_tree.deserialize_tree(lt_cfg)

                # 效能優化判定：若無實質行號限制且滿足「無過濾規則」，直接回傳 None (回復顯示全部)
                actual_start = max(2, self.start_row) if self.is_header else self.start_row
                has_row_limit = (actual_start > (2 if self.is_header else 1)) or (self.end_row is not None and self.end_row < total_rows)
                is_no_rules_filter = not rules_cfg or not tree

                if not has_row_limit and is_no_rules_filter:
                    self.filter_completed.emit(None, time.time() - start_time)
                    self.finished.emit(TaskStatus.FINISHED)
                    return

                # 正規表達式預先編譯
                regex_patterns = []
                for j, r_cfg in enumerate(rules_cfg):
                    method = r_cfg.get("compare_method", 0)
                    if not isinstance(method, int):
                        method = 0
                    target = r_cfg.get("compare_target")
                    val = r_cfg.get("compare_value", "")

                    pat = None
                    if method == CompareMethod.REGEX and target == -1:
                        try:
                            pat = re.compile(val)
                        except re.error as e:
                            self._last_error = f"規則 #{j+1} 正規表達式語法錯誤: {e}"
                            self.log_emitted.emit("ERROR", self._last_error)
                            self.finished.emit(TaskStatus.ERROR)
                            return
                    regex_patterns.append(pat)

                for i, row in enumerate(self.all_rows):
                    if self._is_cancelled:
                        self.finished.emit(TaskStatus.CANCELLED)
                        return

                    # 報告進度
                    if i % 10000 == 0:
                        self.progress.emit(i, total_rows)

                    # 排除標題行
                    r_num = i + 1
                    if self.is_header and r_num == 1:
                        continue

                    # 程式流程明確判定：起始行號限制 AND 結束行號限制 AND (一般規則總結果)
                    in_start_limit = (r_num >= actual_start)
                    in_end_limit = (self.end_row is None or r_num <= end_bound)
                    rules_match = self.evaluate_general_rules(row, rules_cfg, tree, regex_patterns)

                    if in_start_limit and in_end_limit and rules_match:
                        matched_indices.append(i)

                self.progress.emit(total_rows, total_rows)
                self.filter_completed.emit(matched_indices, time.time() - start_time)
                self.finished.emit(TaskStatus.FINISHED)

            except Exception as e:
                self._last_error = f"過濾發生未預期錯誤: {e}"
                self.log_emitted.emit("ERROR", self._last_error)
                self.finished.emit(TaskStatus.ERROR)
        finally:
            # 🔪 主動釋放大型資料引用，不等 deleteLater
            self.all_rows = None
            self.filter_config = None
            self.cc_t2s = None
            self.cc_s2t = None
