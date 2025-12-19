import os
import sys
from pathlib import Path
from packaging.version import parse, InvalidVersion

def get_app_data_dir() -> Path:
    """
    운영체제에 맞는 애플리케이션 데이터 디렉토리 경로를 반환합니다.
    경로가 존재하지 않으면 생성합니다.
    """
    if os.name == 'nt': # Windows
        path = Path(os.getenv('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'MinecraftModManager'
    else: # macOS, Linux
        path = Path.home() / '.config' / 'MinecraftModManager'
    
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_minecraft_dir() -> Path:
    """운영체제에 맞는 마인크래프트 기본 설치 경로를 반환합니다."""
    if sys.platform == "win32":
        return Path.home() / "AppData/Roaming/.minecraft"
    elif sys.platform == "darwin":
        return Path.home() / "Library/Application Support/minecraft"
    else:  # Linux and other Unix-like OS
        return Path.home() / ".minecraft"

def get_installed_mc_versions() -> list[str]:
    """
    설치된 마인크래프트 버전 목록을 스캔하고 정렬하여 반환합니다.
    Fabric, OptiFine 등이 포함된 버전 이름도 포함됩니다.
    """
    versions_path = get_minecraft_dir() / "versions"
    if not versions_path.exists():
        return []

    installed_versions = []
    for version_dir in versions_path.iterdir():
        if version_dir.is_dir():
            # 버전 이름과 동일한 json 파일이 있는지 확인하여 유효한 버전 폴더인지 검사
            version_json_path = version_dir / f"{version_dir.name}.json"
            if version_json_path.exists():
                installed_versions.append(version_dir.name)

    # 버전을 역순으로 정렬 (최신 버전이 위로)
    def sort_key(version_str):
        try:
            # e.g., "1.20.1-fabric-0.15.0" -> "1.20.1"
            base_version = version_str.split('-')[0]
            return parse(base_version)
        except InvalidVersion:
            # 숫자로 시작하지 않는 버전(e.g., "b1.7.3")은 낮은 우선순위로 처리
            return parse("0.0.0")

    installed_versions.sort(key=sort_key, reverse=True)
    return installed_versions

def get_mods_dir() -> Path:
    """마인크래프트 mods 폴더 경로를 반환합니다."""
    return get_minecraft_dir() / "mods"