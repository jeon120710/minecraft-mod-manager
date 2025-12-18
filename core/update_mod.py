import os
import shutil
from pathlib import Path
from datetime import datetime
import requests
from core.mod_scanner import get_minecraft_dir
from core.app_path import get_app_data_dir

APP_DATA_DIR = get_app_data_dir()
LOG_FILE = APP_DATA_DIR / "update_log.txt"

def update_mod(mod):
    """
    모드를 업데이트합니다. mod 딕셔너리에 'download_url'과 'latest_filename'이 포함되어 있어야 합니다.
    """
    mods_dir = get_minecraft_dir() / "mods"
    old_file_path = mods_dir / mod["file"]
    
    download_url = mod.get("download_url")
    new_file_name = mod.get("latest_filename")

    if not download_url or not new_file_name:
        raise ValueError("업데이트 정보가 부족합니다. 'download_url'과 'latest_filename'이 필요합니다.")

    new_file_path = mods_dir / new_file_name
    temp_file_path = new_file_path.with_suffix(new_file_path.suffix + '.tmp')

    try:
        # 백업 생성
        backup_dir = get_minecraft_dir() / "mods_backup"
        backup_dir.mkdir(exist_ok=True)
        if old_file_path.exists():
            shutil.copy2(old_file_path, backup_dir / mod["file"])

        # 1. 임시 파일로 다운로드
        with requests.get(download_url, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            with open(temp_file_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        # 2. 다운로드 성공 후, 기존 파일 삭제 (이름이 다른 경우)
        if old_file_path.exists() and old_file_path != new_file_path:
            old_file_path.unlink()

        # 3. 임시 파일을 최종 위치로 이동 (원자적 연산)
        os.replace(temp_file_path, new_file_path)
        temp_file_path = None

        # 4. 로그 기록
        with LOG_FILE.open('a', encoding='utf-8') as f:
            latest_version = mod.get('latest_version', 'N/A')
            f.write(f"{datetime.now()}: {mod['mod_name']} {mod.get('mod_version', 'unknown')} -> {latest_version} (file: {old_file_path.name} -> {new_file_path.name})\n")

    except Exception as e:
        raise RuntimeError(f"업데이트 오류: {e}")
    
    finally:
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink()


def rollback_mod(old_file_name: str, new_file_name: str) -> bool:
    """
    모드 업데이트를 롤백합니다.
    백업된 이전 파일을 복원하고, 현재 파일을 삭제합니다.
    """
    try:
        minecraft_dir = get_minecraft_dir()
        mods_dir = minecraft_dir / "mods"
        backup_dir = minecraft_dir / "mods_backup"

        backup_file = backup_dir / old_file_name
        current_file = mods_dir / new_file_name

        if not backup_file.exists():
            raise FileNotFoundError(f"백업 파일을 찾을 수 없습니다: {backup_file}")
        
        # 롤백: 백업 파일을 mods 폴더로 복사
        shutil.copy2(backup_file, mods_dir / old_file_name)

        # 현재 파일 삭제
        if current_file.exists():
            current_file.unlink()
        
        # 로그 기록
        with LOG_FILE.open('a', encoding='utf-8') as f:
            f.write(f"{datetime.now()}: [롤백] {new_file_name} -> {old_file_name}\n")
        
        return True
    except Exception as e:
        raise RuntimeError(f"롤백 오류: {e}")

