import requests

def check_ollama_models(server_url: str) -> list[str]:
    """
    非同步測試 Local AI (Ollama) 連線，拉取 /api/tags 中的模型列表。
    這是一個原子性的純網路請求，如果出錯會拋出 Exception。
    """
    url = server_url.rstrip('/') + '/api/tags'
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        models = [m['name'] for m in data.get('models', [])]
        return models
    except Exception as e:
        raise RuntimeError(f"連線失敗或無法取得模型列表: {str(e)}")

def generate_local_ai(server_url: str, model: str, prompt: str, num_ctx: int, temperature: float) -> str:
    """
    呼叫本地離線 AI 接口 (/api/generate) 來產生文字。
    這是一個原子性的純網路請求，不夾雜 UI 邏輯。
    """
    url = server_url.rstrip('/') + '/api/generate'
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": num_ctx,
            "temperature": temperature
        }
    }
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        if "response" in data:
            return data["response"]
        else:
            raise ValueError(f"回傳格式異常，缺少 'response' 欄位。回傳資料: {data}")
    except Exception as e:
        raise RuntimeError(f"Ollama 生成請求失敗: {str(e)}")

def generate_google_ai(api_key: str, model: str, prompt: str, temperature: float) -> str:
    """
    呼叫 Google Gemini API 來產生文字。
    這是一個原子性的純網路請求，不夾雜 UI 邏輯。
    """
    # 如果使用者沒有輸入 model，預設使用 gemini-1.5-flash
    model_name = model if model else "gemini-1.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature
        }
    }
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # 檢查是否含有錯誤資訊
        if "error" in data:
            err_msg = data["error"].get("message", "未知錯誤")
            raise ValueError(f"Gemini API 回傳錯誤: {err_msg}")
            
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini API 未回傳任何 candidates。")
            
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise ValueError("Gemini API 回傳的候選內容中沒有 parts。")
            
        text = parts[0].get("text", "")
        return text
    except Exception as e:
        raise RuntimeError(f"Google Gemini 生成請求失敗: {str(e)}")
