from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QToolButton, QTextEdit, QScrollArea, QFrame, QLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, QPoint, QRect, QSize


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=6):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def doLayout(self, rect, testOnly):
        left, top, right, bottom = self.getContentsMargins()
        effectiveRect = rect.adjusted(+left, +top, -right, -bottom)
        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0
        spaceX = self.spacing()
        spaceY = self.spacing()

        for item in self.itemList:
            wid = item.widget()
            if not wid:
                continue
            sz = item.sizeHint()
            nextX = x + sz.width() + spaceX
            if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + sz.width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), sz))

            x = nextX
            lineHeight = max(lineHeight, sz.height())

        return y + lineHeight - rect.y() + bottom


class AiPromptWidget(QWidget):
    """
    AiPromptWidget — 負責 AI 欄位動態映射與 Prompt 指示的 UI 模組。
    
    具備職責：
      - 渲染寫入目標欄位選單 (QComboBox, 支援編輯以自訂新欄位名稱)。
      - 動態生成 CSV 的 Header 對應的 QToolButton，支援點擊直接將變數帶入 Prompt 游標處。
      - 繪製自訂 Prompt 指示文字框 (QTextEdit)。
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. 設定目標寫回欄位
        target_layout = QHBoxLayout()
        target_layout.setSpacing(8)
        
        lbl_target = QLabel("輸出欄位：")
        lbl_target.setStyleSheet("color: #c0caf5;")
        
        # 目標寫入欄位選單，限制為唯讀下拉選單
        self.cb_target_col = QComboBox()
        self.cb_target_col.setPlaceholderText("選擇欄位名稱")
        self.cb_target_col.setStyleSheet("""
            QComboBox {
                background-color: #1a1b26;
                color: #c0caf5;
                border: 1px solid #3b4261;
                border-radius: 4px;
                padding: 4px;
            }
            QComboBox:focus {
                border: 1px solid #7aa2f7;
            }
        """)
        
        target_layout.addWidget(lbl_target)
        target_layout.addWidget(self.cb_target_col, 1)
        layout.addLayout(target_layout)

        # 2. 可用欄位標籤 (QToolButton 水平滾動區)
        lbl_tags_title = QLabel("可用欄位快選：")
        lbl_tags_title.setStyleSheet("color: #c0caf5;")
        layout.addWidget(lbl_tags_title)

        # 使用 QScrollArea 裝載多列折行的 QToolButtons
        self.tags_scroll = QScrollArea()
        self.tags_scroll.setWidgetResizable(True)
        self.tags_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.tags_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tags_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tags_scroll.setStyleSheet("background-color: transparent;")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        self.tags_layout = FlowLayout(self.scroll_content, spacing=6)
        
        self.tags_scroll.setWidget(self.scroll_content)
        layout.addWidget(self.tags_scroll)

        # 3. AI 指示 (Prompt)
        lbl_prompt_title = QLabel("AI 指示（Prompt）：")
        lbl_prompt_title.setStyleSheet("color: #c0caf5;")
        layout.addWidget(lbl_prompt_title)

        self.txt_prompt = QTextEdit()
        self.txt_prompt.setPlaceholderText("請輸入 AI 指導語，例如：\n根據 {姓名} 與 {生日}，以紫微斗數判斷今日運勢。\n嚴格限制：只能傳回「吉」、「普通」、「兇」其中一個詞。")
        self.txt_prompt.setAcceptRichText(False)
        self.txt_prompt.setMinimumHeight(100)
        self.txt_prompt.setStyleSheet("""
            QTextEdit {
                background-color: #1a1b26;
                color: #c0caf5;
                border: 1px solid #3b4261;
                border-radius: 4px;
                padding: 6px;
                font-family: Consolas, 'Courier New', monospace;
            }
            QTextEdit:focus {
                border: 1px solid #7aa2f7;
            }
        """)
        fm = self.txt_prompt.fontMetrics()
        self.txt_prompt.setMaximumHeight(10 * fm.lineSpacing() + 16)
        layout.addWidget(self.txt_prompt)

    def update_columns(self, limit, csv_data):
        """
        當載入 CSV 完成時被呼叫，清空舊標籤與下拉選單，並依最新 Header 重新渲染。
        """
        # 1. 清空舊有 QToolButton 標籤
        while self.tags_layout.count() > 0:
            item = self.tags_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # 2. 重新填充 QComboBox 下拉選單項目
        self.cb_target_col.blockSignals(True)
        self.cb_target_col.clear()
        
        if csv_data and limit > 0:
            for i in range(limit):
                header = csv_data.get_column_header(i)
                self.cb_target_col.addItem(header, i)
                
        self.cb_target_col.blockSignals(False)

        # 3. 動態繪製一排 QToolButton
        if not csv_data or limit == 0:
            # 若無 headers，顯示簡單提示標記
            lbl_tip = QLabel("（CSV 未包含欄位標記）")
            lbl_tip.setStyleSheet("color: #565f89; font-style: italic;")
            self.tags_layout.addWidget(lbl_tip)
            self.adjust_tags_height()
            return

        for i in range(limit):
            header = csv_data.get_column_header(i)
            btn = QToolButton()
            btn.setText(f"{{{header}}}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QToolButton {
                    background-color: #24283b;
                    color: #7aa2f7;
                    border: 1px solid #3b4261;
                    border-radius: 3px;
                    padding: 4px 8px;
                    font-size: 11px;
                }
                QToolButton:hover {
                    background-color: #3b4261;
                    color: #bb9af3;
                    border: 1px solid #7aa2f7;
                }
            """)
            # 使用預設參數 lambda 綁定 header 值，避免 loop scope bind 問題
            btn.clicked.connect(lambda checked=False, name=header: self._on_tag_clicked(name))
            self.tags_layout.addWidget(btn)

        self.adjust_tags_height()

    def _on_tag_clicked(self, tag_name: str):
        """
        處理點擊可用欄位標籤：自動將該字串插入到 Prompt 文字框的當前游標處。
        """
        insert_text = f"{{{tag_name}}}"
        cursor = self.txt_prompt.textCursor()
        cursor.insertText(insert_text)
        self.txt_prompt.setTextCursor(cursor)
        self.txt_prompt.setFocus()

    def get_target_col(self) -> int:
        """
        取得使用者選定的寫回目標欄位索引 (0-based)。
        若未選擇，則回傳 -1。
        """
        val = self.cb_target_col.currentData()
        return val if isinstance(val, int) else -1

    def get_prompt(self) -> str:
        """
        取得目前自訂 Prompt 內容。
        """
        return self.txt_prompt.toPlainText()

    def set_target_col(self, col_idx):
        if not isinstance(col_idx, int):
            col_idx = -1
            
        if 0 <= col_idx < self.cb_target_col.count():
            self.cb_target_col.setCurrentIndex(col_idx)
        else:
            self.cb_target_col.setCurrentIndex(-1)

    def set_prompt(self, text: str):
        self.txt_prompt.setPlainText(text)

    def set_enabled(self, enabled: bool):
        self.cb_target_col.setEnabled(enabled)
        self.txt_prompt.setEnabled(enabled)
        # 禁用或啟用所有標籤按鈕
        for i in range(self.tags_layout.count()):
            item = self.tags_layout.itemAt(i)
            if item and item.widget():
                item.widget().setEnabled(enabled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_tags_height()

    def adjust_tags_height(self):
        if not hasattr(self, 'scroll_content') or not self.scroll_content.layout():
            return
        
        w = self.tags_scroll.viewport().width()
        if w <= 0:
            w = self.tags_scroll.width()
        if w <= 0:
            w = 300
            
        layout = self.scroll_content.layout()
        
        btn_height = 24
        spacing = layout.spacing()
        if spacing < 0:
            spacing = 6
            
        max_btn_width = 0
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                h = item.widget().sizeHint().height()
                if h > 0:
                    btn_height = max(btn_height, h)
                w_btn = item.widget().sizeHint().width()
                if w_btn > max_btn_width:
                    max_btn_width = w_btn
        
        max_btn_width += 12
        self.scroll_content.setMinimumWidth(max_btn_width)
        
        margins = layout.contentsMargins()
        max_h = 5 * btn_height + 4 * spacing + margins.top() + margins.bottom()
        
        ideal_h = layout.heightForWidth(w)
        if ideal_h <= 0:
            ideal_h = btn_height + margins.top() + margins.bottom()
            
        final_h = min(ideal_h, max_h)
        final_h += 4
        
        self.tags_scroll.setFixedHeight(final_h)
