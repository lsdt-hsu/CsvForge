from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QToolButton, QTextEdit, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt


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

        # 🤖 AI 欄位動態映射處理 標題
        lbl_section = QLabel("🤖 AI 欄位動態映射處理")
        lbl_section.setStyleSheet("font-weight: bold; color: #7aa2f7; font-size: 13px;")
        layout.addWidget(lbl_section)

        # 1. 設定目標寫回欄位
        target_layout = QHBoxLayout()
        target_layout.setSpacing(8)
        
        lbl_target = QLabel("1. 輸出欄位：")
        lbl_target.setStyleSheet("color: #c0caf5;")
        
        # 目標寫入欄位選單，限制為唯讀下拉選單
        self.cb_target_col = QComboBox()
        self.cb_target_col.setPlaceholderText("選擇欄位名稱")
        self.cb_target_col.setMinimumWidth(180)
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
        target_layout.addWidget(self.cb_target_col)
        target_layout.addStretch()
        layout.addLayout(target_layout)

        # 2. 可用欄位標籤 (QToolButton 水平滾動區)
        lbl_tags_title = QLabel("2. 可用欄位標籤（點擊可快速複製到 Prompt 中）：")
        lbl_tags_title.setStyleSheet("color: #a9b1d6; font-size: 11px;")
        layout.addWidget(lbl_tags_title)

        # 使用 QScrollArea 裝載橫向排開的 QToolButtons，確保欄位過多時能優雅橫向滾動
        self.tags_scroll = QScrollArea()
        self.tags_scroll.setWidgetResizable(True)
        self.tags_scroll.setFixedHeight(40)
        self.tags_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.tags_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tags_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tags_scroll.setStyleSheet("background-color: transparent;")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        self.tags_layout = QHBoxLayout(self.scroll_content)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(6)
        self.tags_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self.tags_scroll.setWidget(self.scroll_content)
        layout.addWidget(self.tags_scroll)

        # 3. AI 指示 (Prompt)
        lbl_prompt_title = QLabel("3. AI 指示（Prompt）：")
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
        layout.addWidget(self.txt_prompt)

    def update_headers(self, headers: list[str]):
        """
        當載入 CSV 完成時被呼叫，清空舊標籤與下拉選單，並依最新 Header 重新渲染。
        """
        # 1. 清空舊有 QToolButton 標籤
        while self.tags_layout.count() > 0:
            item = self.tags_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # 2. 重新填充 QComboBox 下拉選單項目 (維持當前選擇)
        self.cb_target_col.blockSignals(True)
        current_text = self.cb_target_col.currentText()
        self.cb_target_col.clear()
        if headers:
            self.cb_target_col.addItems(headers)
        if current_text:
            # 如果原先選取的文字不在新載入的 headers 中，則暫存追加它，平常不檢查其正確性
            if not headers or current_text not in headers:
                self.cb_target_col.addItem(current_text)
            self.cb_target_col.setCurrentText(current_text)
        self.cb_target_col.blockSignals(False)

        # 3. 動態繪製一排 QToolButton
        if not headers:
            # 若無 headers，顯示簡單提示標記
            lbl_tip = QLabel("（CSV 未包含欄位標記）")
            lbl_tip.setStyleSheet("color: #565f89; font-style: italic;")
            self.tags_layout.addWidget(lbl_tip)
            return

        for header in headers:
            btn = QToolButton()
            btn.setText(f"[ {{{header}}} ]")
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

    def _on_tag_clicked(self, tag_name: str):
        """
        處理點擊可用欄位標籤：自動將該字串插入到 Prompt 文字框的當前游標處。
        """
        insert_text = f"{{{tag_name}}}"
        cursor = self.txt_prompt.textCursor()
        cursor.insertText(insert_text)
        self.txt_prompt.setTextCursor(cursor)
        self.txt_prompt.setFocus()

    def get_target_col(self) -> str:
        """
        取得使用者選定或輸入的寫回目標欄位名稱。
        """
        return self.cb_target_col.currentText().strip()

    def get_prompt(self) -> str:
        """
        取得目前自訂 Prompt 內容。
        """
        return self.txt_prompt.toPlainText()

    def set_target_col(self, col_name: str):
        if not col_name:
            return
        # 平常還原設定時不比對正確性，若不在清單內，先暫存追加以防設定流失
        idx = self.cb_target_col.findText(col_name)
        if idx == -1:
            self.cb_target_col.addItem(col_name)
        self.cb_target_col.setCurrentText(col_name)

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
