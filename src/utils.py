import csv

def detect_encoding(file_path):
    encodings = ['utf-8-sig', 'utf-8', 'cp950', 'gbk', 'utf-16', 'latin-1']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                f.read(4096)
            return enc
        except UnicodeDecodeError:
            continue
    return 'utf-8'

def detect_delimiter(file_path, encoding):
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            sample = f.read(2048)
            dialect = csv.Sniffer().sniff(sample)
            return dialect.delimiter
    except Exception:
        return ','

def prevent_sleep(prevent: bool = True) -> bool:
    """
    Prevent Windows from sleeping when prevent is True, and restore sleep behavior when False.
    Returns True if the operation succeeded, False otherwise.
    """
    import os
    if os.name == 'nt':
        try:
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            if prevent:
                # Prevent sleep
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
            else:
                # Restore sleep behavior
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            return True
        except Exception as e:
            print(f"Failed to set thread execution state: {e}")
            return False
    return False

