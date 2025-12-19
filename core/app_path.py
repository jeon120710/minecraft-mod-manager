import os
from pathlib import Path

def get_app_data_dir() -> Path:
    """
    운영체제에 맞는 애플리케이션 데이터 디렉토리 경로를 반환합니다.
    경로가 존재하지 않으면 생성합니다.
    """
    if os.name == 'nt': # Windows
        # LOCALAPPDATA 환경 변수를 사용하여 사용자별 경로를 동적으로 결정
        path = Path(os.getenv('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'MinecraftModManager'
    else: # macOS, Linux
        # 홈 디렉토리 아래에 .config 폴더를 사용하는 일반적인 방식
        path = Path.home() / '.config' / 'MinecraftModManager'
    
    # 경로가 존재하지 않으면 생성
    path.mkdir(parents=True, exist_ok=True)
    return path