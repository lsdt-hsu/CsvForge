import re

def extract_referenced_fields(prompt: str) -> list[str]:
    """
    使用正規表達式提取 Prompt 中所有以大括號 {} 包裹的欄位名稱。
    例如: "根據 {姓名} 與 {生日} 判斷運勢" -> ['姓名', '生日']
    
    此為純字串處理函數，不包含任何 UI 元件或狀態。
    """
    if not prompt:
        return []
    # 使用 seen 集合去重並保持順序
    seen = set()
    fields = []
    # 比對大括號內的內容
    for match in re.findall(r'\{(.*?)\}', prompt):
        stripped = match.strip()
        if stripped and stripped not in seen:
            seen.add(stripped)
            fields.append(stripped)
    return fields

def build_final_prompt(user_prompt: str, row_data: dict) -> str:
    """
    將 Prompt 模版中的 {欄位變數} 替換成 row_data 中對應的實質內容，
    拼裝出最終發送給 AI 的 Prompt。
    
    此為原子性的靜態處理方法，不包含任何 PyQt 依賴。
    """
    if not user_prompt:
        return ""
    referenced_fields = extract_referenced_fields(user_prompt)
    final_prompt = user_prompt
    for field in referenced_fields:
        if field in row_data:
            val = row_data[field]
            # 支援若欄位值為 None 的防呆處理，轉為空字串
            if val is None:
                val = ""
            final_prompt = final_prompt.replace(f"{{{field}}}", str(val))
    return final_prompt
