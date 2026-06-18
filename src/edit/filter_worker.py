import re
import time
import unicodedata
from PyQt6.QtCore import QThread, pyqtSignal

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

class FilterWorker(QThread):
    progress_updated = pyqtSignal(int, int)
    filter_completed = pyqtSignal(object, float)  # 傳回: 匹配的索引列表, 執行時間(秒)
    filter_error = pyqtSignal(str)

    def __init__(self, all_rows, start_row, end_row, is_header, 
                 src_col, tgt_col, filter_config, parent=None):
        super().__init__(parent)
        self.all_rows = all_rows
        self.start_row = start_row
        self.end_row = end_row
        self.is_header = is_header
        
        self.src_col = src_col
        self.tgt_col = tgt_col
        self.filter_config = filter_config
        
        self._is_cancelled = False

        # 初始化 OpenCC 轉換器 (離線字典載入)
        try:
            from opencc import OpenCC
            self.cc_t2s = OpenCC('t2s')
            self.cc_s2t = OpenCC('s2t')
        except Exception:
            self.cc_t2s = None
            self.cc_s2t = None

    def cancel(self):
        self._is_cancelled = True

    def check_row_match(self, row, compare_col, compare_method, compare_target, compare_value, regex_pattern):
        # 決定比對範圍欄位索引集合
        if compare_col == "all":
            cols_to_check = list(range(len(row)))
        elif compare_col == "range":
            start_c = max(0, self.src_col - 1)
            end_c = min(len(row) - 1, self.tgt_col - 1)
            cols_to_check = list(range(start_c, end_c + 1))
        else:
            # 特定欄位 (整數)
            cols_to_check = [compare_col]

        # 決定比對目標值
        if compare_method in ("屬於", "不屬於"):
            target_val = compare_value
        elif compare_target == "manual":
            target_val = compare_value
        else:
            # 特定欄位的值 (整數)
            t_idx = compare_target
            target_val = row[t_idx] if t_idx < len(row) else ""

        is_match = False
        
        if compare_method == "完全符合":
            is_match = any((row[c] if c < len(row) else "") == target_val for c in cols_to_check)
        elif compare_method == "包含":
            is_match = any(target_val in (row[c] if c < len(row) else "") for c in cols_to_check)
        elif compare_method == "未包含":
            # 「未包含」：所有欄位皆不包含 target_val (AND 邏輯)
            is_match = all(target_val not in (row[c] if c < len(row) else "") for c in cols_to_check)
        elif compare_method == "正規表達式":
            if compare_target == "manual" and regex_pattern:
                is_match = any(bool(regex_pattern.search(row[c] if c < len(row) else "")) for c in cols_to_check)
            else:
                # 欄位比對當作正規表達式（以 target_val 做為 pattern）
                try:
                    t_regex = re.compile(target_val)
                    is_match = any(bool(t_regex.search(row[c] if c < len(row) else "")) for c in cols_to_check)
                except re.error:
                    is_match = False
        elif compare_method in ("屬於", "不屬於"):
            is_belong = any(self.is_belong_match(row[c] if c < len(row) else "", compare_target, target_val) for c in cols_to_check)
            is_match = not is_belong if compare_method == "不屬於" else is_belong
                    
        return is_match

    def is_belong_match(self, text, target, sub_value):
        if target == "語系":
            if sub_value == "中文":
                # 含有任何漢字，且不含日文假名
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
                    # 部分符合即可：只要含有一個中文字元，且該字元在 s2t 轉換後保持不變
                    for c in text:
                        if '\u4e00' <= c <= '\u9fff':
                            if self.cc_s2t.convert(c) == c:
                                return True
                    return False
                else:
                    # 降級備用：使用 big5 編碼檢查
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
                    # 降級備用：使用 gb2312 編碼檢查
                    for c in text:
                        if '\u4e00' <= c <= '\u9fff':
                            try:
                                c.encode('gb2312')
                                return True
                            except UnicodeEncodeError:
                                pass
                    return False
                    
            elif sub_value == "日文(專字)":
                # 假名，日文特有符號/疊字，或日文特有漢字（無法編碼為 big5 且無法編碼為 gb2312）
                for c in text:
                    if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff':
                        return True
                    if c in ('\u3005', '\u3006', '\u3012', '\u303b', '\u303d', '\u3004'):  # 々, 〆, 〒, 〻, 〽, 〄
                        return True
                    if '\u4e00' <= c <= '\u9fff':
                        # 雙重編碼失敗檢查
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
                # if 含日文專字：return true
                if self.is_belong_match(text, "語系", "日文(專字)"):
                    return True
                # else if 不含漢字：return false
                if not any('\u4e00' <= c <= '\u9fff' for c in text):
                    return False
                # else 採用欄位字串拆解法匹配日文全漢字字典
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
            # 必須完全符合
            if sub_value == "半形":
                return bool(re.match(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$', text))
            elif sub_value == "全半形":
                converted = text.translate(FULL_TO_HALF_TRANS)
                return bool(re.match(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$', converted))
            elif sub_value == "多國語言":
                if not text:
                    return False
                # 標準化全形控制字元
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
            # 必須完全符合
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
            # 必須完全符合 (不含文數字，可含空白)
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

    def run(self):
        start_time = time.time()
        matched_indices = []
        
        try:
            total_rows = len(self.all_rows)
            end_bound = self.end_row if self.end_row is not None else total_rows
            end_bound = min(end_bound, total_rows)
            
            is_dual = self.filter_config.get("is_dual", False)
            rule1 = self.filter_config.get("rule1", {})
            rule2 = self.filter_config.get("rule2", {})
            
            col1 = rule1.get("compare_col", "none")
            col2 = rule2.get("compare_col", "none") if is_dual else "none"
            
            # 若為「不過濾」，回傳 None 交給 Model 處理
            if col1 == "none" and col2 == "none":
                self.filter_completed.emit(None, time.time() - start_time)
                return

            # 正規表達式預先編譯
            regex_pattern1 = None
            if col1 != "none":
                if rule1.get("compare_method") == "正規表達式" and rule1.get("compare_target") == "manual":
                    try:
                        regex_pattern1 = re.compile(rule1.get("compare_value", ""))
                    except re.error as e:
                        self.filter_error.emit(f"規則一正規表達式語法錯誤: {e}")
                        return

            regex_pattern2 = None
            if is_dual and col2 != "none":
                if rule2.get("compare_method") == "正規表達式" and rule2.get("compare_target") == "manual":
                    try:
                        regex_pattern2 = re.compile(rule2.get("compare_value", ""))
                    except re.error as e:
                        self.filter_error.emit(f"規則二正規表達式語法錯誤: {e}")
                        return

            for i, row in enumerate(self.all_rows):
                if self._is_cancelled:
                    return
                
                # 報告進度
                if i % 10000 == 0:
                    self.progress_updated.emit(i, total_rows)
                
                # 排除標題行
                r_num = i + 1
                if self.is_header and r_num == 1:
                    continue
                    
                # 僅檢查在 start_row 與 end_row 之間的資料
                actual_start = max(2, self.start_row) if self.is_header else self.start_row
                if not (actual_start <= r_num <= end_bound):
                    continue
                
                # 規則一比對
                if col1 == "none":
                    match1 = True
                else:
                    match1 = self.check_row_match(
                        row, col1,
                        rule1.get("compare_method"),
                        rule1.get("compare_target"),
                        rule1.get("compare_value"),
                        regex_pattern1
                    )
                
                # 規則二比對
                if is_dual:
                    if col2 == "none":
                        match2 = True
                    else:
                        match2 = self.check_row_match(
                            row, col2,
                            rule2.get("compare_method"),
                            rule2.get("compare_target"),
                            rule2.get("compare_value"),
                            regex_pattern2
                        )
                    
                    op = self.filter_config.get("op", "AND")
                    if op == "AND":
                        is_match = match1 and match2
                    else: # OR
                        is_match = match1 or match2
                else:
                    is_match = match1

                if is_match:
                    matched_indices.append(i)

            self.progress_updated.emit(total_rows, total_rows)
            self.filter_completed.emit(matched_indices, time.time() - start_time)

        except Exception as e:
            self.filter_error.emit(f"過濾發生未預期錯誤: {e}")
