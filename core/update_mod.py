import requests
import os
import sys
from pathlib import Path
from datetime import datetime
from core.app_path import get_app_data_dir

APP_DATA_DIR = get_app_data_dir()
LOG_FILE = APP_DATA_DIR / "update_log.txt"

def get_minecraft_dir() -> Path:
    """운영체제에 맞는 마인크래프트 기본 설치 경로를 반환합니다."""
    if sys.platform == "win32":
        return Path.home() / "AppData/Roaming/.minecraft"
    elif sys.platform == "darwin":
        return Path.home() / "Library/Application Support/minecraft"
    else:  # Linux and other Unix-like OS
        return Path.home() / ".minecraft"

def update_mod(mod):
    """
    모드를 업데이트합니다. mod 딕셔너리에 'download_url'과 'latest_filename'이 포함되어 있어야 합니다.
    """
    mods_dir = get_minecraft_dir() / "mods"
    old_file_path = mods_dir / mod["file"]
    new_file_path = mods_dir / mod['latest_filename']
    backup_file_path = old_file_path.with_suffix(old_file_path.suffix + '.bak')

    try:
        # Download the new version
        res = requests.get(mod['download_url'], timeout=60) # Increase timeout for large files
        res.raise_for_status()

        with open(new_file_path, 'wb') as f:
            f.write(res.content)

        # Backup the old file instead of deleting it
        if old_file_path.exists():
            if backup_file_path.exists():
                os.remove(backup_file_path) # Remove old backup if it exists
            os.rename(old_file_path, backup_file_path)
            print(f"   -> 기존 파일 백업 완료: {backup_file_path.name}")

        # Log the update
        with LOG_FILE.open('a', encoding='utf-8') as f:
            latest_version = mod.get('latest_version', 'N/A')
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {mod['mod_name']} {mod.get('mod_version', 'unknown')} -> {latest_version} (file: {old_file_path.name} -> {new_file_path.name})\n")
    except Exception as e:
        raise RuntimeError(f"업데이트 오류: {e}")

def rollback_mod(old_file_name: str, new_file_name: str):
    """
    모드 업데이트를 롤백합니다.
    백업된 이전 파일을 복원하고, 현재 파일을 삭제합니다.
    """
    mods_dir = get_minecraft_dir() / "mods"
    backup_file = mods_dir / (old_file_name + '.bak')
    current_file = mods_dir / new_file_name
    restored_file = mods_dir / old_file_name

    if not backup_file.exists():
        raise FileNotFoundError(f"백업 파일을 찾을 수 없습니다: {backup_file}")

    # 롤백: 백업 파일을 원래 이름으로 복원
    # 복원하려는 파일이 이미 존재하면 덮어쓰기 방지를 위해 먼저 삭제
    if restored_file.exists() and not restored_file.samefile(backup_file):
         os.remove(restored_file)
    os.rename(backup_file, restored_file)

    # 현재 파일 삭제 (롤백된 파일과 다른 경우에만)
    if current_file.exists() and not current_file.samefile(restored_file):
        current_file.unlink()
    
    # 로그 기록
    with LOG_FILE.open('a', encoding='utf-8') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: [롤백] {new_file_name} -> {old_file_name}\n")
