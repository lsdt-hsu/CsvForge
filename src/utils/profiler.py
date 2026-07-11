"""Profiler utilities."""

import sys
import gc
import tracemalloc
import psutil
from typing import Any, Optional
from enum import Enum

class ProfilerMode(Enum):
    NORMAL = "normal"
    CONTINUOUS = "continuous"
    COMPARE_TO_FIRST = "compare_to_first"

class MemoryProfiler:
    _instance = None
    _mode: ProfilerMode = ProfilerMode.COMPARE_TO_FIRST

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MemoryProfiler, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._proc = psutil.Process()
            self.reset()

    def reset(self):
        """
        重設所有診斷狀態與計數。
        """
        self.load_count = 0
        self._snap_before = None
        self._rss_before = None
        if tracemalloc.is_tracing():
            try:
                tracemalloc.stop()
            except RuntimeError:
                pass

    def start_diagnostic(self, target_obj: Optional[Any] = None, target_name: str = "OBJECT"):
        """
        開始記憶體診斷，記錄當前快照。
        """
        self.load_count += 1

        if self._snap_before is not None:
            return

        # 開始時呼叫 gc.collect()
        gc.collect()

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

        # ── 2. 記錄當前快照作為基準 ──
        self._snap_before = tracemalloc.take_snapshot()
        self._rss_before = self._proc.memory_info().rss / (1024 * 1024)  # 轉換為 MB

    def _print_comparison(self, baseline_snap, baseline_rss, current_snap, current_rss, label: str):
        _py_current, _py_peak = tracemalloc.get_traced_memory()
        print(f"[DIAG {label}] RSS: before={baseline_rss:.1f}MB, after={current_rss:.1f}MB, delta={current_rss - baseline_rss:+.1f}MB")
        print(f"[DIAG {label}] Python traced: current={_py_current / (1024*1024):.1f}MB, peak={_py_peak / (1024*1024):.1f}MB")

        _stats = current_snap.compare_to(baseline_snap, 'lineno')
        print(f"[DIAG {label}] tracemalloc Top 5 增量:")
        for _s in _stats[:5]:
            print(f"  {_s}")
        print(f"{'='*60}")
        del _stats

    def end_diagnostic(self):
        """
        結束診斷，印出與 start 之間的記憶體與快照變化，並依據模式處理/清理診斷資料。
        """
        if self._snap_before is None or self._rss_before is None:
            print(f"[DIAG #{self.load_count}] Warning: end_diagnostic called without a matching start_diagnostic.")
            return

        # 開始時呼叫 gc.collect()
        gc.collect()
        
        _snap_after = tracemalloc.take_snapshot()
        _rss_after = self._proc.memory_info().rss / (1024 * 1024)  # MB

        # 進行比對與輸出
        self._print_comparison(
            baseline_snap=self._snap_before,
            baseline_rss=self._rss_before,
            current_snap=_snap_after,
            current_rss=_rss_after,
            label=f"#{self.load_count}"
        )

        # ── 依據不同 mode 處理基準快照 ──
        if self._mode == ProfilerMode.NORMAL:
            self._snap_before = None
            self._rss_before = None
        elif self._mode == ProfilerMode.CONTINUOUS:
            self._snap_before = _snap_after
            self._rss_before = _rss_after
        elif self._mode == ProfilerMode.COMPARE_TO_FIRST:
            pass  # 保留第一次快照作為基準，捨棄新的快照，不修改 self._snap_before

        # 結束時呼叫 gc.collect()
        del _snap_after
        gc.collect()

# 全域單一實例，供跨模組匯入使用
profiler = MemoryProfiler()