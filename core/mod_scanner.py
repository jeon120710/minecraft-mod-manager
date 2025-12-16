import sys
from pathlib import Path
from core.loader_detect import detect_loader
from core.mc_version import detect_mc_version_and_name

def get_minecraft_dir():
    """운영체제에 맞는 마인크래프트 기본 설치 경로를 반환합니다."""
    if sys.platform == "win32":
        return Path.home() / "AppData/Roaming/.minecraft"
    elif sys.platform == "darwin":
        return Path.home() / "Library/Application Support/minecraft"
    else:  # Linux and other Unix-like OS
        return Path.home() / ".minecraft"

def scan_mods():
    try:
        minecraft_dir = get_minecraft_dir()
        mods_dir = minecraft_dir / "mods"
        
        if not mods_dir.exists():
            return []

        mods = []
        for file in mods_dir.glob("*.jar"):
            mod_name, mc_version, mod_version = detect_mc_version_and_name(file.name, mods_dir)
            mods.append({
                "file": file.name,
                "loader": detect_loader(file.name),
                "mc_version": mc_version or "-",
                "mod_version": mod_version or "-",
                "mod_name": mod_name or file.stem,
                "status": "확인 중"
            })
        return mods
    except Exception as e:
        raise RuntimeError(f"모드 스캔 오류: {e}")
        return []
