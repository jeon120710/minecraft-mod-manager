import json
import time
from pathlib import Path
from core.app_path import get_app_data_dir

# 데이터 폴더 가져오기
APP_DATA_DIR = get_app_data_dir()
CACHE_FILE = APP_DATA_DIR / "modrinth.json"
CACHE_TTL = 60 * 60 * 6  # 6시간


def load_cache():
    if not CACHE_FILE.exists():
        return {}

    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        # TTL 체크는 loader_worker에서 개별 모드에 대해 하므로 여기선 제거
        # if time.time() - data.get("_time", 0) > CACHE_TTL:
        #     return {}
        return data.get("mods", {})
    except (json.JSONDecodeError, IOError) as e:
        print(f"[경고] 캐시({CACHE_FILE})를 읽는 중 오류가 발생하여, 캐시를 초기화합니다: {e}")
        return {}


def save_cache(mods: dict):
    try:
        # get_app_data_dir()이 디렉토리 생성을 보장하므로 mkdir은 필요 없음
        payload = {
            "_time": time.time(),
            "mods": mods
        }
        CACHE_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except IOError as e:
        print(f"[경고] 캐시({CACHE_FILE}) 저장에 실패했습니다: {e}")
