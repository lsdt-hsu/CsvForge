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


def getStandardTextColor(widget_type: WidgetType) -> str:
    """獲取常用元件的標準文字色彩"""
    if widget_type in (WidgetType.STD_LABEL, WidgetType.STD_CHECK_BOX):
        return "#a9b1d6"  # FONT COLOR STANDARD
    elif widget_type in (WidgetType.STD_BUTTON, WidgetType.STD_LINE_EDIT, WidgetType.STD_COMBO_BOX):
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
        elif state == "running":
            return "#f7768e"
        elif state == "running_hover":
            return "#ff9eaf"
        elif state == "running_pressed":
            return "#db4b66"
        elif state == "primary":
            return "#7aa2f7"
        elif state == "primary_hover":
            return "#89ddff"
        elif state == "primary_pressed":
            return "#3b4261"
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


def applyStandardButtonStyle(widget, is_running: bool = False) -> None:
    """套用標準 Button 樣式，可帶入 is_running 區分執行中與就緒狀態"""
    if is_running:
        qss = f"""
            QPushButton {{
                background-color: {getStandardBgColor(WidgetType.STD_BUTTON, "running")};
                color: #1a1b26;
                border: {getStandardBorder(WidgetType.STD_BUTTON)};
                border-radius: {getStandardBorderRadius(WidgetType.STD_BUTTON)};
                padding: 8px 15px;
                font-weight: bold;
                font-size: {getStandardFontSize(WidgetType.STD_BUTTON)}px;
            }}
            QPushButton:hover {{
                background-color: {getStandardBgColor(WidgetType.STD_BUTTON, "running_hover")};
            }}
            QPushButton:pressed {{
                background-color: {getStandardBgColor(WidgetType.STD_BUTTON, "running_pressed")};
            }}
            QPushButton:disabled {{
                background-color: {getStandardBgColor(WidgetType.STD_BUTTON, "disabled")};
                color: #565f89;
            }}
        """
    else:
        qss = f"""
            QPushButton {{
                background-color: {getStandardBgColor(WidgetType.STD_BUTTON, "primary")};
                color: #1a1b26;
                border: {getStandardBorder(WidgetType.STD_BUTTON)};
                border-radius: {getStandardBorderRadius(WidgetType.STD_BUTTON)};
                padding: 8px 15px;
                font-weight: bold;
                font-size: {getStandardFontSize(WidgetType.STD_BUTTON)}px;
            }}
            QPushButton:hover {{
                background-color: {getStandardBgColor(WidgetType.STD_BUTTON, "primary_hover")};
            }}
            QPushButton:pressed {{
                background-color: {getStandardBgColor(WidgetType.STD_BUTTON, "primary_pressed")};
                color: {getStandardTextColor(WidgetType.STD_BUTTON)};
            }}
            QPushButton:disabled {{
                background-color: {getStandardBgColor(WidgetType.STD_BUTTON, "disabled")};
                color: #565f89;
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
            border: 1px solid #2f3047;
            height: 6px;
            background: #16161e;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #7aa2f7;
            width: 14px;
            margin-top: -4px;
            margin-bottom: -4px;
            border-radius: 7px;
        }
        QSlider::handle:horizontal:hover {
            background: #89ddff;
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
