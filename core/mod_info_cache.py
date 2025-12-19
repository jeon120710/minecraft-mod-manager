import json
import time
from pathlib import Path
from core.app_path import get_app_data_dir

# 캐시 디렉토리 경로
CACHE_DIR = get_app_data_dir() / "cache"
# 캐시 파일 경로 (Modrinth API 검색 결과 캐시)
MOD_INFO_CACHE_FILE = CACHE_DIR / "mod_info_cache.json"
# JAR 파일 메타데이터 캐시 경로
JAR_METADATA_CACHE_FILE = CACHE_DIR / "jar_metadata_cache.json"

# 캐시 유효 기간 (초) - 예: 1시간
MOD_INFO_CACHE_TTL = 3600  # 1 hour

def load_mod_info_cache() -> dict:
    """Modrinth API 검색 결과 캐시를 파일에서 로드합니다."""
    if not MOD_INFO_CACHE_FILE.exists():
        return {}
    try:
        with open(MOD_INFO_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_mod_info_cache(cache: dict):
    """Modrinth API 검색 결과 캐시를 파일에 저장합니다."""
    MOD_INFO_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MOD_INFO_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)

def load_jar_metadata_cache() -> dict:
    """JAR 파일 메타데이터 캐시를 파일에서 로드합니다."""
    if not JAR_METADATA_CACHE_FILE.exists():
        return {}
    try:
        with open(JAR_METADATA_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_jar_metadata_cache(cache: dict):
    """JAR 파일 메타데이터 캐시를 파일에 저장합니다."""
    JAR_METADATA_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(JAR_METADATA_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)