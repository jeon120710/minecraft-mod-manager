import sys
import json
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from gui.main_window import MainWindow
from gui.style import apply_global_style

# CLI-related imports
from core.mod_scanner import scan_mods, ModsFolderNotFoundError
from core.modrinth_api import check_mod_for_update
from core.update_mod import update_mod
from core.app_path import get_app_data_dir

APP_DATA_DIR = get_app_data_dir()
CONFIG_FILE = APP_DATA_DIR / "config.json"

def _ensure_config_file():
    """
    Ensures that a valid config.json file exists in the AppData directory.
    - If it doesn't exist, it migrates it from the project root or creates a new one.
    - If it exists but is empty, it populates it with default content.
    """
    if not CONFIG_FILE.exists():
        project_config_path = Path("config.json")
        if project_config_path.exists():
            try:
                import shutil
                shutil.copy2(project_config_path, CONFIG_FILE)
                print(f"기존 설정 파일을 '{CONFIG_FILE}'(으)로 이전했습니다.")
            except Exception as e:
                print(f"설정 파일 이전 중 오류 발생: {e}")
        else:
            default_config = {"problematic_files": []}
            with CONFIG_FILE.open('w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            print(f"'{CONFIG_FILE}'에 기본 설정 파일을 생성했습니다.")
    # 파일이 존재하지만 비어있는 경우, 기본 내용으로 채움
    elif CONFIG_FILE.stat().st_size == 0:
        default_config = {"problematic_files": []}
        with CONFIG_FILE.open('w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)
        print(f"비어있는 '{CONFIG_FILE}'에 기본 설정을 추가했습니다.")

def update_problematic_mods():
    """
    Scans for mods, identifies problematic ones, and updates them if a newer version is available.
    """
    try:
        with CONFIG_FILE.open('r', encoding='utf-8') as f:
            config = json.load(f)
            problematic_files = config.get("problematic_files", [])
    except (json.JSONDecodeError, FileNotFoundError):
        print(f"오류: '{CONFIG_FILE}' 파일의 형식이 잘못되었습니다.")
        return

    print("모드 폴더를 스캔합니다...")
    print(f"설정 파일 경로: {CONFIG_FILE}")
    try:
        installed_mods = scan_mods()
    except ModsFolderNotFoundError:
        print("오류: '.minecraft/mods' 폴더를 찾을 수 없습니다.")
        print("마인크래프트가 설치되어 있고, 모드 폴더가 한번이라도 생성된 적이 있는지 확인해주세요.")
        return

    # Filter for the specific mods that have issues
    target_mods = [mod for mod in installed_mods if mod["file"] in problematic_files]

    if not target_mods:
        print(f"지정된 문제 모드를 찾을 수 없습니다. '{CONFIG_FILE}'의 파일 이름이 정확한지 확인해주세요.")
        return

    print(f"{len(target_mods)}개의 문제 모드를 확인하고 업데이트를 시도합니다...")

    for mod in target_mods:
        print(f"\n[{mod['mod_name']}] 확인 중...")
        
        # If scanner failed to detect mc_version, skip update for this mod.
        if not mod.get('mc_version') or mod.get('mc_version') == '-':
            print(f"-> 오류: '{mod['file']}'의 마인크래프트 버전을 확인할 수 없습니다. 업데이트를 건너뜁니다.")
            continue
        
        # If scanner failed to detect loader, skip update for this mod.
        if not mod.get('loaders'):
            print(f"-> 오류: '{mod['file']}'의 모드 로더(Fabric/Forge 등)를 확인할 수 없습니다. 업데이트를 건너뜁니다.")
            continue

        status = check_mod_for_update(mod)

        if status == "업데이트 가능":
            try:
                print(f"-> '{mod['mod_name']}'을(를) '{mod['latest_version']}' 버전으로 업데이트합니다...")
                print(f"   다운로드 URL: {mod['download_url']}")
                update_mod(mod)
                print(f"-> '{mod['mod_name']}' 업데이트 완료! 새 파일: {mod['latest_filename']}")
            except Exception as e:
                print(f"-> '{mod['mod_name']}' 업데이트 중 오류 발생: {e}")
        elif status == "최신 버전":
            print(f"-> 최신 버전입니다: {mod['mod_version']}")
        else:
            print(f"-> 업데이트 확인 실패 또는 해당 없음: {status}")

def main():
    # 프로그램 시작 시 항상 config 파일 상태를 확인하고 준비
    _ensure_config_file()

    # config.json을 확인하여 '문제 모드 업데이트'를 실행할지 결정
    run_gui = True
    if CONFIG_FILE.exists() and CONFIG_FILE.stat().st_size > 0:
        try:
            with CONFIG_FILE.open('r', encoding='utf-8') as f:
                config = json.load(f)
            if config.get("problematic_files"):
                # 사용자에게 실행할 작업을 물어봄
                reply = input(f"'{CONFIG_FILE}'에 지정된 {len(config['problematic_files'])}개의 모드에 대한 특별 업데이트를 실행하시겠습니까? (y/N): ").lower()
                if reply == 'y':
                    run_gui = False
                    update_problematic_mods()
        except (json.JSONDecodeError, IOError) as e:
            print(f"경고: '{CONFIG_FILE}' 파일을 읽는 중 오류가 발생했습니다: {e}")
            # 오류가 있어도 GUI는 실행되도록 계속 진행
    
    # 사용자가 'y'를 입력하지 않았거나, config 파일에 내용이 없는 경우 GUI 실행
    if not run_gui:
        sys.exit(0)
        
    print("GUI 애플리케이션을 시작합니다...")
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
