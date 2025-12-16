import os
from pathlib import Path
import sys

def get_app_data_dir() -> Path:
    """
    애플리케이션 데이터(캐시, 로그 등)를 저장할 디렉토리를 반환합니다.
    - Windows: %LOCALAPPDATA%/MinecraftModManager
    - macOS: ~/Library/Application Support/MinecraftModManager
    - Linux: ~/.local/share/MinecraftModManager
    - 기타: [프로젝트 폴더]/.data
    디렉토리가 없으면 생성합니다.
    """
    app_name = "MinecraftModManager"

    if sys.platform == "win32":
        path = Path(os.environ.get("LOCALAPPDATA", "")) / app_name
    elif sys.platform == "darwin":
        path = Path.home() / "Library/Application Support" / app_name
    else: # Linux and other Unix-like OS
        # XDG_DATA_HOME 환경 변수 확인, 없으면 ~/.local/share 사용
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            path = Path(xdg_data_home) / app_name
        else:
            path = Path.home() / ".local/share" / app_name
    
    # LOCALAPPDATA가 없는 등의 예외 상황을 위한 폴백
    if not path.parent.exists():
        print(f"[경고] 기본 데이터 폴더를 찾을 수 없습니다. 프로젝트 폴더 내에 .data 폴더를 생성합니다.")
        # 이 부분은 main.py의 위치에 따라 상대 경로가 달라질 수 있으므로 주의
        # 일단은 현재 작업 디렉토리 기준으로 생성
        path = Path.cwd() / ".data"

    # 최종 경로 생성
    path.mkdir(parents=True, exist_ok=True)
    return path
