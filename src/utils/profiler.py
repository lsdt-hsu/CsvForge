import tracemalloc
import functools

def profile_memory_growth(func):
    """
    記憶體快照裝飾器。
    掛在目標函數上，它會印出執行該函數前後，記憶體增加最多的前 10 行程式碼。
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 啟動記憶體追蹤
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            
        print(f"🔍 開始追蹤 [{func.__name__}] 記憶體變化...")
        snapshot1 = tracemalloc.take_snapshot()
        
        # 執行原本的載入 CSV 動作
        result = func(*args, **kwargs)
        
        # 再次拍照並比對
        snapshot2 = tracemalloc.take_snapshot()
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        print(f"📊 [{func.__name__}] 執行完畢，記憶體增長前 10 名嫌疑犯：")
        for stat in top_stats[:10]:
            print(stat)
            
        return result
    return wrapper