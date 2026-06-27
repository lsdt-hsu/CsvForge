# src/base/theme.py
from PyQt6.QtGui import QFont

# 佈局常數
# 僅定義左側面板容器寬度，各 Package 內部的佈局與元件寬度細節由其自主決定
SIDEBAR_WIDTH = 280
SIDEBAR_FULL_WIDTH = 341
SIDEBAR_MIN_WIDTH = 60

class ThemeStyle:
    # ── 色彩定義 ──
    COLOR_BG_DARK = "#1a1b26"          # 主視窗背景色
    COLOR_PANEL_BG = "#20212e"         # 面板背景色
    COLOR_BORDER = "#2f3047"           # 邊框顏色
    
    COLOR_TEXT_STANDARD = "#a9b1d6"    # 標準文字顏色
    COLOR_TEXT_MUTED = "#565f89"       # 靜音/提示文字顏色
    COLOR_TEXT_HIGHLIGHT = "#7aa2f7"   # 高亮/標題文字顏色
    COLOR_TEXT_CRITICAL = "#f7768e"    # 錯誤/警告文字顏色
    
    # ── 字型與文字大小 ──
    FONT_FAMILY = "Microsoft JhengHei, Segoe UI, sans-serif"
    FONT_SIZE_STANDARD = 13
    
    # ── 按鈕基本樣式 (QSS) ──
    STYLE_BUTTON_COMMON = """
        QPushButton {
            background-color: #414868;
            color: #c0caf5;
            border: none;
            border-radius: 6px;
            padding: 8px 15px;
            font-weight: bold;
            font-size: 13px;
        }
        QPushButton:hover {
            background-color: #565f89;
        }
        QPushButton:pressed {
            background-color: #3b4261;
        }
    """
    
    # ── 重要/停止按鈕樣式 ──
    STYLE_BUTTON_CRITICAL = "background-color: #f7768e; color: #1a1b26; font-weight: bold;"
    
    # ── 禁用按鈕樣式 ──
    STYLE_BUTTON_DISABLED = "background-color: #24283b; color: #565f89; font-weight: bold;"
    
    # ── 通用輸入與控制項樣式 ──
    STYLE_INPUT = """
        QLineEdit {
            background-color: #16161e;
            border: 1px solid #2f3047;
            border-radius: 6px;
            padding: 7px;
            color: #c0caf5;
        }
        QLineEdit:focus {
            border: 1px solid #7aa2f7;
        }
    """
    
    STYLE_COMBOBOX = """
        QComboBox {
            background-color: #16161e;
            border: 1px solid #2f3047;
            border-radius: 6px;
            padding: 7px;
            color: #c0caf5;
        }
        QComboBox:focus {
            border: 1px solid #7aa2f7;
        }
        QComboBox::drop-down {
            border: 0px;
        }
    """

    @staticmethod
    def apply_primary_button_style(button, is_running: bool = False) -> None:
        """
        為側面板的主要按鈕（例如「開始翻譯」）提供完整的建議樣式。
        - is_running = False: 一般狀態（例如「開始翻譯」，使用亮藍/青色系）
        - is_running = True: 停止狀態（例如「停止」，使用紅色系）
        禁用狀態由按鈕本身的 setEnabled(False) 控制，並在此樣式中處理。
        """
        if is_running:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #f7768e;
                    color: #1a1b26;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 15px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #ff9eaf;
                }
                QPushButton:pressed {
                    background-color: #db4b66;
                }
                QPushButton:disabled {
                    background-color: #24283b;
                    color: #565f89;
                }
            """)
        else: # 一般狀態 (is_running = False)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #7aa2f7;
                    color: #1a1b26;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 15px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #89ddff;
                }
                QPushButton:pressed {
                    background-color: #3b4261;
                    color: #c0caf5;
                }
                QPushButton:disabled {
                    background-color: #24283b;
                    color: #565f89;
                }
            """)

    @staticmethod
    def get_standard_font() -> QFont:
        font = QFont("Microsoft JhengHei")
        font.setPointSize(ThemeStyle.FONT_SIZE_STANDARD)
        return font
