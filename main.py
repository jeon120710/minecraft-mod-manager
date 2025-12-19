# -*- coding: utf-8 -*-
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFont

from gui.main_window import MainWindow
from gui.version_dialog import VersionSelectionDialog
from gui.style import apply_global_style
from core.config import load_selected_version, save_selected_version

def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    
    # 폰트 및 글로벌 스타일 적용
    font = QFont()
    font.setStyleHint(QFont.System)
    app.setFont(font)
    apply_global_style(app)

    # --- 버전 선택 로직 ---
    selected_version = load_selected_version()
    
    if not selected_version:
        # 저장된 버전이 없으면, 선택 다이얼로그를 띄움
        selected_version = VersionSelectionDialog.get_selected_version()

        if selected_version:
            # 사용자가 버전을 선택했으면 저장
            save_selected_version(selected_version)
        else:
            # 선택하지 않고 닫았으면 프로그램 종료
            # QMessageBox.information(None, "알림", "마인크래프트 버전을 선택해야 프로그램을 시작할 수 있습니다.")
            sys.exit(0) # 그냥 조용히 종료

    # --- 메인 윈도우 실행 ---
    # 선택된 버전 정보를 MainWindow에 전달
    window = MainWindow(selected_mc_version=selected_version)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()