"""Profiler utilities."""

import sys
import gc
import tracemalloc
import psutil
from typing import Any, Optional

class MemoryProfiler:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MemoryProfiler, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self.load_count = 0
            self._snap_before = None
            self._rss_before = None
            self._proc = psutil.Process()

    def start_diagnostic(self, target_obj: Optional[Any] = None, target_name: str = "OBJECT"):
        """
        開始記憶體診斷，記錄當前快照。
        """
        # 開始時也呼叫一次 gc.collect()
        gc.collect()

        self.load_count += 1
        
        # 啟動記憶體追蹤
        if not tracemalloc.is_tracing():
            tracemalloc.start()

        # ── 1. 檢查目標物件的 refcount 與 referrers ──
        if target_obj is not None:
            rc = sys.getrefcount(target_obj) - 1  # getrefcount 本身會 +1
            non_frame_referrers = []
            for r in gc.get_referrers(target_obj):
                t = type(r).__name__
                if t == 'frame':
                    continue
                if t == 'dict':
                    owners = [type(o).__name__ for o in gc.get_referrers(r) if type(o).__name__ != 'frame']
                    non_frame_referrers.append(f"dict(len={len(r)}, owners={owners[:3]})")
                else:
                    non_frame_referrers.append(f"{t}: {repr(r)[:80]}")
            print(f"[DIAG #{self.load_count}] OLD {target_name}: refcount={rc}")
            print(f"[DIAG #{self.load_count}]   referrers={non_frame_referrers}")
        else:
            print(f"[DIAG #{self.load_count}] OLD {target_name} is empty, skipping refcount check")

        # ── 2. 記錄 tracemalloc 快照與 OS RSS ──
        self._snap_before = tracemalloc.take_snapshot()
        self._rss_before = self._proc.memory_info().rss / (1024 * 1024)  # 轉換為 MB

    def end_diagnostic(self):
        """
        結束診斷，印出與 start 之間的記憶體與快照變化，並徹底清理診斷資料。
        """
        if self._snap_before is None or self._rss_before is None:
            print(f"[DIAG #{self.load_count}] Warning: end_diagnostic called without a matching start_diagnostic.")
            return

        gc.collect()
        
        _snap_after = tracemalloc.take_snapshot()
        _rss_after = self._proc.memory_info().rss / (1024 * 1024)  # MB
        _py_current, _py_peak = tracemalloc.get_traced_memory()

        # 印出記憶體增量結果
        print(f"[DIAG #{self.load_count}] RSS: before={self._rss_before:.1f}MB, after={_rss_after:.1f}MB, delta={_rss_after - self._rss_before:+.1f}MB")
        print(f"[DIAG #{self.load_count}] Python traced: current={_py_current / (1024*1024):.1f}MB, peak={_py_peak / (1024*1024):.1f}MB")

        # 顯示 tracemalloc 分配差異 Top 5
        _stats = _snap_after.compare_to(self._snap_before, 'lineno')
        print(f"[DIAG #{self.load_count}] tracemalloc Top 5 增量:")
        for _s in _stats[:5]:
            print(f"  {_s}")
        print(f"{'='*60}")

        # ── 3. 確實清理所有診斷資料（避免本身造成 Memory Leak）──
        self._snap_before = None
        self._rss_before = None
        
        # 刪除與釋放本地暫存物件
        del _snap_after
        del _stats
        gc.collect()

# 全域單一實例，供跨模組匯入使用
profiler = MemoryProfiler()