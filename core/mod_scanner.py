import sys
from pathlib import Path
from core.loader_detect import detect_loader
from core.mc_version import detect_mc_version_and_name

class ModsFolderNotFoundError(Exception):
    """모드 폴더를 찾을 수 없을 때 발생하는 예외."""
    pass

def get_minecraft_dir():
    """운영체제에 맞는 마인크래프트 기본 설치 경로를 반환합니다."""
    if sys.platform == "win32":
        return Path.home() / "AppData/Roaming/.minecraft"
    elif sys.platform == "darwin":
        return Path.home() / "Library/Application Support/minecraft"
    else:  # Linux and other Unix-like OS
        return Path.home() / ".minecraft"

def get_mods_dir():
    """마인크래프트 mods 폴더 경로를 반환합니다."""
    minecraft_dir = get_minecraft_dir()
    return minecraft_dir / "mods"

def scan_mods(mods_dir_path: str = None):
    """
    지정된 경로 또는 기본 경로에서 모드를 스캔합니다.
    
    :param mods_dir_path: 스캔할 모드 폴더의 경로. None이면 기본 경로를 사용합니다.
    """
    if mods_dir_path:
        mods_dir = Path(mods_dir_path)
    else:
        mods_dir = get_mods_dir()
    
    if not mods_dir.exists():
        raise ModsFolderNotFoundError(f"모드 폴더를 찾을 수 없습니다: {mods_dir}")

    mods = []
    for file in mods_dir.glob("*.jar"):
        try:
            mod_name, mc_version, mod_version = detect_mc_version_and_name(file.name, mods_dir)
            mods.append({
                "file": file.name,
                "loader": detect_loader(file.name),
                "mc_version": mc_version or "-",
                "mod_version": mod_version or "-",
                "mod_name": mod_name or file.stem,
                "status": "확인 중"
            })
        except Exception as e:
            print(f"[경고] 모드 파일 '{file.name}'을(를) 읽는 중 오류 발생: {e}")
            mods.append({
                "file": file.name,
                "loader": "오류",
                "mc_version": "오류",
                "mod_version": "오류",
                "mod_name": file.name,
                "status": "파일 손상됨"
            })
    return mods
