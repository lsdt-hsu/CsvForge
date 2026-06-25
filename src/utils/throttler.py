import time

class ThrottledProgress:
    """
    限制信號發送頻率的 Helper 類別。
    預設每秒最多發送 5 次 (時間間隔 >= 0.2 秒)。
    """
    def __init__(self, signal, min_interval: float = 0.2):
        self.signal = signal
        self.min_interval = min_interval
        self.last_emit_time = 0.0

    def emit(self, *args, force: bool = False) -> bool:
        """
        嘗試發送信號。
        若距離上次發送時間大於等於指定間隔，或是 force=True，則成功發送並回傳 True；否則被過濾回傳 False。
        """
        current_time = time.time()
        if force or (current_time - self.last_emit_time >= self.min_interval):
            self.signal.emit(*args)
            self.last_emit_time = current_time
            return True
        return False
