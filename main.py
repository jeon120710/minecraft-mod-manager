#모듈 인풋(압축할때 플러그인 추가하기!!)
import sys
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFontDatabase

from gui.main_window import MainWindow
from gui.version_dialog import VersionSelectionDialog
from gui.style import apply_global_style
from core.config import load_selected_version, save_selected_version

def main():
    """Application entry point."""
    app = QApplication(sys.argv)

    # 폰트 로드 및 동적 폰트 이름 설정
    font_name = "Arial"  # 기본 대체 폰트
    font_path = os.path.join(os.path.dirname(__file__), 'gui', 'font', 'PretendardVariable.ttf')
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            if font_families:
                font_name = font_families[0]
                print(f"Font '{font_name}' loaded successfully.")
            else:
                print("Warning: Could not get font family name from loaded font.")
        else:
            print(f"Warning: Failed to load font at '{font_path}'")
    else:
        print(f"Warning: Font file not found at '{font_path}'")

    apply_global_style(app, font_name)
    selected_version = load_selected_version()
    
    if not selected_version:
        selected_version = VersionSelectionDialog.get_selected_version()

        if selected_version:
            # 사용자가 버전을 선택했으면 저장해주기
            save_selected_version(selected_version)
        else:
            # 선택하지 않고 닫았으면 프로그램 종료
            sys.exit(0) # 그냥 조용히 종료

    # --- 메인 윈도우 실행 ---
    # 선택된 버전 정보를 MainWindow에 전달
    window = MainWindow(selected_mc_version=selected_version)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()