import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from network import setup_http_hook
from ui import MainWindow

if __name__ == "__main__":
    # Setup HTTP interceptor hook
    setup_http_hook()
    
    app = QApplication(sys.argv)
    
    font = QFont("Microsoft JhengHei", 9)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
