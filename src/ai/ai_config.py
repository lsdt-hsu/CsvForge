from dataclasses import dataclass

@dataclass
class AiPanelConfig:
    dirty: bool = False
    ai_service: str = "Google AI"
    google_api_key: str = ""
    google_model: str = "gemini-1.5-flash"
    local_backend: str = "Ollama"
    local_server_url: str = "http://localhost:11434"
    local_model: str = ""
    advanced_num_ctx: int = 4096
    advanced_temperature: float = 0.7
    target_col: int = -1
    prompt_template: str = ""

    def serialize(self) -> dict:
        """將設定序列化為 dict。"""
        return {
            "ai_service": self.ai_service,
            "google_api_key": self.google_api_key,
            "google_model": self.google_model,
            "local_backend": self.local_backend,
            "local_server_url": self.local_server_url,
            "local_model": self.local_model,
            "advanced_num_ctx": self.advanced_num_ctx,
            "advanced_temperature": self.advanced_temperature,
            "target_col": self.target_col,
            "prompt_template": self.prompt_template,
        }

    def deserialize(self, data: dict) -> None:
        """從 dict 反序列化並載入設定。"""
        self.ai_service = data.get("ai_service", "Google AI")
        self.google_api_key = data.get("google_api_key", "")
        self.google_model = data.get("google_model", "gemini-1.5-flash")
        self.local_backend = data.get("local_backend", "Ollama")
        self.local_server_url = data.get("local_server_url", "http://localhost:11434")
        self.local_model = data.get("local_model", "")
        
        try:
            self.advanced_num_ctx = int(data.get("advanced_num_ctx", 4096))
        except (ValueError, TypeError):
            self.advanced_num_ctx = 4096
            
        try:
            self.advanced_temperature = float(data.get("advanced_temperature", 0.7))
        except (ValueError, TypeError):
            self.advanced_temperature = 0.7
            
        try:
            self.target_col = int(data.get("target_col", -1))
        except (ValueError, TypeError):
            self.target_col = -1
            
        self.prompt_template = data.get("prompt_template", "")
