import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from gui.main_window import MainWindow
from gui.style import apply_global_style


def main():
    app = QApplication(sys.argv)
    
    # 시스템 기본 폰트 설정
    font = QFont()
    font.setStyleHint(QFont.System)
    app.setFont(font)

    apply_global_style(app)

    window = MainWindow()
    window.show() # 로딩 상태와 관계없이 창을 먼저 표시

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
