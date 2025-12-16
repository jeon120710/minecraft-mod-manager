import sys
from PySide6.QtWidgets import QApplication, QMessageBox
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

    def on_load_finished():
        window.show()
        window.activateWindow()

    def on_load_failed(error_message):
        QMessageBox.critical(
            None, # Parent 없음
            "초기 로딩 오류!",
            f"모드 정보를 불러오는 중 오류가 발생했습니다: {error_message}\n\n프로그램을 종료합니다."
        )
        app.quit() # 오류 발생 시 앱 종료

    window.initial_load_finished.connect(on_load_finished)
    window.initial_load_failed.connect(on_load_failed)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
