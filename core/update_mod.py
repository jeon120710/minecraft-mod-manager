import requests
import os
import shutil
from pathlib import Path
from datetime import datetime
from core.mod_scanner import get_minecraft_dir

LOG_FILE = Path("update_log.txt")

def update_mod(mod):
    try:
        # Modrinth 프로젝트 검색
        r = requests.get("https://api.modrinth.com/v2/search", params={"query": mod["mod_name"], "limit": 1})
        r.raise_for_status()
        hits = r.json().get("hits", [])
        if not hits:
            raise Exception("프로젝트 찾기 실패")
        project_id = hits[0]["project_id"]
        
        # 최신 버전 가져오기
        r2 = requests.get(f"https://api.modrinth.com/v2/project/{project_id}/version", params={"loaders": [mod["loader"].lower()]})
        r2.raise_for_status()
        versions = r2.json()
        if not versions:
            raise Exception("버전 찾기 실패")
        latest = versions[0]
        download_url = latest["files"][0]["url"]
        
        # 다운로드
        mods_dir = get_minecraft_dir() / "mods"
        old_file = mods_dir / mod["file"]
        new_file = mods_dir / latest["files"][0]["filename"]
        
        # 백업
        backup_dir = get_minecraft_dir() / "mods_backup"
        backup_dir.mkdir(exist_ok=True)
        backup_file = backup_dir / mod["file"]
        if old_file.exists():
            shutil.copy2(old_file, backup_file)
        
        with requests.get(download_url, stream=True) as resp:
            resp.raise_for_status()
            with open(new_file, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        # 로그 기록
        with LOG_FILE.open('a', encoding='utf-8') as f:
            f.write(f"{datetime.now()}: {mod['mod_name']} {mod.get('mod_version', 'unknown')} -> {latest['version_number']} (file: {old_file.name} -> {new_file.name})\n")
        
        # 다운로드 성공 후 기존 파일 삭제
        if old_file.exists():
            old_file.unlink()
    except Exception as e:
        raise RuntimeError(f"업데이트 오류: {e}")


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

