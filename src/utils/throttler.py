import time
import weakref
from threading import Timer, Lock
from PyQt6.sip import isdeleted

class ThrottledProgress:
    """
    限制信號發送頻率的 Helper 類別。
    預設每秒最多發送 5 次 (時間間隔 >= 0.2 秒)。
    支援 trailing edge，並強制綁定 parent 以進行安全的生命週期管理。
    """
    def __init__(self, signal, parent, min_interval: float = 0.2):
        if parent is None:
            raise ValueError("ThrottledProgress: parent 參數不可為 None")
            
        self.signal = signal
        self.min_interval = min_interval
        self.last_emit_time = 0.0
        self.timer = None
        self.pending_args = None
        self.lock = Lock()
        
        # 1. 弱引用 parent (通常是擁有該信號的 QObject)，防止阻礙垃圾回收 (GC)
        self.weak_parent = weakref.ref(parent)

    def emit(self, *args, force: bool = False) -> bool:
        """
        嘗試發送信號。
        """
        with self.lock:
            # 2. 發送前主動檢查 parent 是否已銷毀，若已被銷毀則直接取消定時並跳過
            if self._is_parent_deleted_locked():
                self._cancel_timer_locked()
                return False
                
            current_time = time.time()
            time_passed = current_time - self.last_emit_time

            if force or (time_passed >= self.min_interval):
                self._cancel_timer_locked()
                self._emit_signal_locked(args, current_time)
                return True
            else:
                self.pending_args = args
                if self.timer is None:
                    remaining_time = self.min_interval - time_passed
                    self.timer = Timer(remaining_time, self._on_timer_trigger)
                    self.timer.start()
                return False

    def cancel(self) -> None:
        """
        取消任何懸掛的補發定時器。
        當擁有者 (Panel 或 Worker) 即將銷毀或完成工作時，必須主動呼叫此方法。
        """
        with self.lock:
            self._cancel_timer_locked()
            self.pending_args = None

    def _is_parent_deleted_locked(self) -> bool:
        p = self.weak_parent()
        if p is None or isdeleted(p):
            return True
        return False

    def _emit_signal_locked(self, args, current_time):
        if self._is_parent_deleted_locked():
            return
        
        # 直接發送，不使用 try-except 吞食銷毀異常。
        # 若忘記在 parent 銷毀時 cancel，將直接拋出 C++ 物件銷毀異常以協助除錯
        self.signal.emit(*args)
        self.last_emit_time = current_time
        self.pending_args = None

    def _cancel_timer_locked(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def _on_timer_trigger(self):
        with self.lock:
            if self._is_parent_deleted_locked():
                self.pending_args = None
                self.timer = None
                return
                
            if self.pending_args is not None:
                current_time = time.time()
                self._emit_signal_locked(self.pending_args, current_time)
            self.timer = None
