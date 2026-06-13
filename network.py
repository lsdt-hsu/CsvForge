import threading
import requests

# Thread-local variable to capture HTTP status code and message
_http_error_info = threading.local()
_original_get = requests.get

def _custom_get(*args, **kwargs):
    _http_error_info.status_code = None
    _http_error_info.reason = None
    try:
        response = _original_get(*args, **kwargs)
        if response.status_code < 200 or response.status_code >= 300:
            _http_error_info.status_code = response.status_code
            _http_error_info.reason = response.reason or response.text[:200]
        return response
    except Exception as e:
        _http_error_info.reason = str(e)
        raise e

def get_http_error_info():
    return _http_error_info

def setup_http_hook():
    requests.get = _custom_get
