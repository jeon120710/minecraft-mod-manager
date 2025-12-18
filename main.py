import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from gui.main_window import MainWindow
from gui.style import apply_global_style

# CLI-related imports
from core.mod_scanner import scan_mods, ModsFolderNotFoundError
from core.modrinth_api import check_mod_for_update
from core.update_mod import update_mod

def update_problematic_mods():
    """
    Scans for mods, identifies problematic ones, and updates them if a newer version is available.
    """
    problematic_files = [
        "ferritecore-8.0.3-fabric.jar",
        "iris-fabric-1.10.2+mc1.21.11.jar",
        "MouseTweaks-fabric-mc1.21.11-2.30.jar",
        "shulkerboxtooltip-fabric-5.2.14+1.21.11.jar",
        "sodium-fabric-0.8.0+mc1.21.11.jar",
        "sodium-extra-fabric-0.8.0+mc1.21.11.jar",
    ]

    print("모드 폴더를 스캔합니다...")
    try:
        installed_mods = scan_mods()
    except ModsFolderNotFoundError:
        print("오류: '.minecraft/mods' 폴더를 찾을 수 없습니다.")
        print("마인크래프트가 설치되어 있고, 모드 폴더가 한번이라도 생성된 적이 있는지 확인해주세요.")
        return

    # Filter for the specific mods that have issues
    target_mods = [mod for mod in installed_mods if mod["file"] in problematic_files]

    if not target_mods:
        print("지정된 문제 모드를 찾을 수 없습니다. 파일 이름이 정확한지 확인해주세요.")
        return

    print(f"{len(target_mods)}개의 문제 모드를 확인하고 업데이트를 시도합니다...")

    for mod in target_mods:
        print(f"\n[{mod['mod_name']}] 확인 중...")
        
        # Fallback to derive mc_version from filename if scanner failed
        if mod.get('mc_version') == '-':
            if '1.21.11' in mod['file']: # Based on user's file list
                 mod['mc_version'] = '1.21.11'
            else:
                print(f"오류: '{mod['file']}'의 마인크래프트 버전을 확인할 수 없습니다. 업데이트를 건너뜁니다.")
                continue

        status = check_mod_for_update(mod)
        print(f"상태: {status}")

        if status == "업데이트 가능":
            try:
                print(f"'{mod['mod_name']}'을(를) '{mod['latest_version']}' 버전으로 업데이트합니다...")
                print(f"다운로드 URL: {mod['download_url']}")
                update_mod(mod)
                print(f"'{mod['mod_name']}' 업데이트 완료! 새 파일: {mod['latest_filename']}")
            except Exception as e:
                print(f"'{mod['mod_name']}' 업데이트 중 오류 발생: {e}")
        elif status == "최신 버전":
            print(f"'{mod['mod_name']}'은(는) 이미 최신 버전입니다.")
        else:
            print(f"'{mod['mod_name']}'에 대한 업데이트를 찾지 못했거나 오류가 발생했습니다.")

def main():
    # Check for CLI arguments
    if len(sys.argv) > 1 and sys.argv[1] == 'update':
        update_problematic_mods()
        sys.exit(0)

    # If no CLI args, run the GUI
    app = QApplication(sys.argv)
    
    # 시스템 기본 폰트 설정
    font = QFont()
    font.setStyleHint(QFont.System)
    app.setFont(font)

    apply_global_style(app)

    window = MainWindow()
    # window.show() # 로딩 상태와 관계없이 창을 먼저 표시 / MainWindow에서 직접 show()를 호출하도록 변경

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
