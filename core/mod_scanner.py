import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.mc_version import detect_mc_version_and_name

class ModsFolderNotFoundError(Exception):
    """모드 폴더를 찾을 수 없을 때 발생하는 예외."""
    pass

def get_minecraft_dir() -> Path:
    """운영체제에 맞는 마인크래프트 기본 설치 경로를 반환합니다."""
    if sys.platform == "win32":
        return Path.home() / "AppData/Roaming/.minecraft"
    elif sys.platform == "darwin":
        return Path.home() / "Library/Application Support/minecraft"
    else:  # Linux and other Unix-like OS
        return Path.home() / ".minecraft"

def scan_mods(mods_dir_path: str = None):
    """지정된 경로 또는 기본 경로에서 활성화/비활성화된 모드를 모두 스캔합니다."""
    if mods_dir_path:
        mods_dir = Path(mods_dir_path)
    else:
        mods_dir = get_minecraft_dir() / "mods"
    
    if not mods_dir.exists():
        raise ModsFolderNotFoundError(f"모드 폴더를 찾을 수 없습니다: {mods_dir}")
    
    mod_files = [f for f in os.listdir(mods_dir) if f.endswith((".jar", ".jar.disabled"))]
    installed_mods = []

    with ThreadPoolExecutor() as executor:
        future_to_filename = {executor.submit(detect_mc_version_and_name, filename, mods_dir): filename for filename in mod_files}
        
        for future in as_completed(future_to_filename):
            filename = future_to_filename[future]
            is_enabled = not filename.endswith(".jar.disabled")
            try:
                (mod_name, mc_version, mod_version, project_id, 
                 loaders, detection_source, all_mc_versions) = future.result()
                
                installed_mods.append({
                    "file": filename,
                    "enabled": is_enabled,
                    "mod_name": mod_name or Path(filename).stem,
                    "mc_version": mc_version or "-",
                    "mod_version": mod_version or "-",
                    "project_id": project_id,
                    "loaders": loaders,
                    "detection_source": detection_source,
                    "all_mc_versions": all_mc_versions,
                })
            except Exception as e:
                # Add a placeholder for failed scans
                installed_mods.append({
                    "file": filename, 
                    "enabled": is_enabled,
                    "mod_name": Path(filename).stem.replace(".jar", ""),
                    "mc_version": "오류", 
                    "mod_version": "오류", 
                    "project_id": None, 
                    "loaders": [],
                    "detection_source": "스캔 오류",
                    "all_mc_versions": [],
                })
    
    # Sort mods by name for consistent order
    installed_mods.sort(key=lambda x: x['mod_name'].lower())
    return installed_mods
