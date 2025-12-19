import json
import time
from pathlib import Path
from core.app_path import get_app_data_dir

# 데이터 폴더 가져오기
APP_DATA_DIR = get_app_data_dir()
CACHE_FILE = APP_DATA_DIR / "modrinth.json"
CACHE_TTL = 60 * 60 * 6  # 6시간


def load_cache():
    """
    캐시를 비활성화하기 위해 항상 빈 딕셔너리를 반환합니다.
    """
    return {}


def save_cache(mods: dict):
    """
    캐시를 비활성화하기 위해 아무 작업도 수행하지 않습니다.
    """
    pass
