# src/plugin_sdk/theme.py
from enum import Enum

# 側面板最大寬度限制 (對應原本的 SIDEBAR_FULL_WIDTH)
SIDEBAR_MAX_WIDTH = 341

class WidgetType(Enum):
    STD_LABEL = "label"
    STD_BUTTON = "button"
    STD_LINE_EDIT = "line_edit"
    STD_COMBO_BOX = "combo_box"
    STD_CHECK_BOX = "check_box"
    STD_SLIDER = "slider"

def getStandardFontSize(widget_type: WidgetType) -> int:
    """獲取常用元件的標準字型大小"""
    return 13

def getStandardTextColor(widget_type: WidgetType, state: str = "normal") -> str:
    """獲取常用元件在特定狀態下的文字色彩"""
    if widget_type == WidgetType.STD_BUTTON:
        if state == "disabled":
            return "#565f89"
        elif state == "pressed":
            return "#c0caf5"
        return "#c0caf5"

    if widget_type in (WidgetType.STD_LABEL, WidgetType.STD_CHECK_BOX):
        return "#a9b1d6"  # FONT COLOR STANDARD
    elif widget_type in (WidgetType.STD_LINE_EDIT, WidgetType.STD_COMBO_BOX):
        return "#c0caf5"  # FONT COLOR HIGHLIGHT/MUTED
    return "#a9b1d6"

def getStandardBgColor(widget_type: WidgetType, state: str = "normal") -> str:
    """獲取常用元件在特定狀態下的背景底色"""
    if widget_type == WidgetType.STD_BUTTON:
        if state == "normal":
            return "#414868"
        elif state == "hover":
            return "#565f89"
        elif state == "pressed":
            return "#3b4261"
        elif state == "disabled":
            return "#24283b"
    elif widget_type in (WidgetType.STD_LINE_EDIT, WidgetType.STD_COMBO_BOX):
        return "#16161e"
    return "transparent"

def getStandardBorder(widget_type: WidgetType, state: str = "normal") -> str:
    """獲取常用元件在特定狀態下的外框邊線樣式"""
    if widget_type in (WidgetType.STD_LINE_EDIT, WidgetType.STD_COMBO_BOX):
        if state == "focus":
            return "1px solid #7aa2f7"
        return "1px solid #2f3047"
    return "none"

def getStandardBorderRadius(widget_type: WidgetType) -> str:
    """獲取常用元件的標準圓角半徑"""
    return "6px"

def applyStandardLabelStyle(widget) -> None:
    """套用標準 Label 樣式"""
    qss = f"""
        QLabel {{
            color: {getStandardTextColor(WidgetType.STD_LABEL)};
            font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
            font-size: {getStandardFontSize(WidgetType.STD_LABEL)}px;
        }}
    """
    widget.setStyleSheet(qss)

def applyStandardButtonStyle(widget) -> None:
    """套用標準 Button 樣式，可帶入 is_running 區分執行中與就緒狀態"""
    qss = f"""
        QPushButton {{
            background-color: {getStandardBgColor(WidgetType.STD_BUTTON, "normal")};
            color: {getStandardTextColor(WidgetType.STD_BUTTON)};
            border: {getStandardBorder(WidgetType.STD_BUTTON)};
            border-radius: {getStandardBorderRadius(WidgetType.STD_BUTTON)};
            padding: 8px 15px;
            font-weight: bold;
            font-size: {getStandardFontSize(WidgetType.STD_BUTTON)}px;
        }}
        QPushButton:hover {{
            background-color: {getStandardBgColor(WidgetType.STD_BUTTON, "hover")};
        }}
        QPushButton:pressed {{
            background-color: {getStandardBgColor(WidgetType.STD_BUTTON, "pressed")};
            color: {getStandardTextColor(WidgetType.STD_BUTTON, "pressed")};
        }}
        QPushButton:disabled {{
            background-color: {getStandardBgColor(WidgetType.STD_BUTTON, "disabled")};
            color: {getStandardTextColor(WidgetType.STD_BUTTON, "disabled")};
        }}
    """
    widget.setStyleSheet(qss)

def applyStandardLineEditStyle(widget) -> None:
    """套用標準 LineEdit 樣式"""
    qss = f"""
        QLineEdit {{
            background-color: {getStandardBgColor(WidgetType.STD_LINE_EDIT, "normal")};
            border: {getStandardBorder(WidgetType.STD_LINE_EDIT, "normal")};
            border-radius: {getStandardBorderRadius(WidgetType.STD_LINE_EDIT)};
            padding: 7px;
            color: {getStandardTextColor(WidgetType.STD_LINE_EDIT)};
        }}
        QLineEdit:focus {{
            border: {getStandardBorder(WidgetType.STD_LINE_EDIT, "focus")};
        }}
    """
    widget.setStyleSheet(qss)

def applyStandardComboBoxStyle(widget) -> None:
    """套用標準 ComboBox 樣式"""
    qss = f"""
        QComboBox {{
            background-color: {getStandardBgColor(WidgetType.STD_COMBO_BOX, "normal")};
            border: {getStandardBorder(WidgetType.STD_COMBO_BOX, "normal")};
            border-radius: {getStandardBorderRadius(WidgetType.STD_COMBO_BOX)};
            padding: 7px;
            color: {getStandardTextColor(WidgetType.STD_COMBO_BOX)};
        }}
        QComboBox:focus {{
            border: {getStandardBorder(WidgetType.STD_COMBO_BOX, "focus")};
        }}
        QComboBox::drop-down {{
            border: 0px;
        }}
    """
    widget.setStyleSheet(qss)

def applyStandardCheckBoxStyle(widget) -> None:
    """套用標準 CheckBox 樣式"""
    qss = f"""
        QCheckBox {{
            color: {getStandardTextColor(WidgetType.STD_CHECK_BOX)};
            font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
            font-size: {getStandardFontSize(WidgetType.STD_CHECK_BOX)}px;
        }}
        QCheckBox:hover {{
            color: #c0caf5;
        }}
    """
    widget.setStyleSheet(qss)

def applyStandardSliderStyle(widget) -> None:
    """套用標準 Slider 樣式"""
    qss = """
        QSlider::groove:horizontal {
            height: 4px;
            background: transparent;
        }
        QSlider::sub-page:horizontal {
            background: #ff8760;
            border-radius: 2px;
        }
        QSlider::add-page:horizontal {
            background: #8a8a8a;
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: #ff8760;
            border: 4px solid #2e303e;
            width: 8px;
            height: 8px;
            margin-top: -6px;
            margin-bottom: -6px;
            border-radius: 8px;
        }
        QSlider::handle:horizontal:hover {
            background: #ff9e7d;
            border-color: #3b3d5c;
        }
    """
    widget.setStyleSheet(qss)

def applyTitleLabel(widget) -> None:
    """套用面板中的標題樣式 (如「翻譯」字樣)"""
    qss = """
        QLabel {
            color: #7aa2f7;
            font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
            font-size: 14px;
            font-weight: bold;
        }
    """
    widget.setStyleSheet(qss)

def applyHintLabel(widget) -> None:
    """套用獨立的提示文字樣式 (如「尚未載入資料」)"""
    qss = """
        QLabel {
            color: #565f89;
            font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
            font-size: 13px;
            font-style: italic;
        }
    """
    widget.setStyleSheet(qss)

def applyPrimaryButtonStyle(button, is_running: bool = False) -> None:
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
