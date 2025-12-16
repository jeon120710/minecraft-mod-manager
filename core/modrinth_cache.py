import json
import time
from pathlib import Path

CACHE_DIR = Path(".cache")
CACHE_FILE = CACHE_DIR / "modrinth.json"
CACHE_TTL = 60 * 60 * 6  # 6시간


def load_cache():
    if not CACHE_FILE.exists():
        return {}

    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if time.time() - data.get("_time", 0) > CACHE_TTL:
            # TTL 초과 시 캐시 무효화
            return {}
        return data.get("mods", {})
    except Exception as e:
        raise IOError(f"캐시 로드 오류: {e}")


def save_cache(mods: dict):
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        payload = {
            "_time": time.time(),
            "mods": mods
        }
        CACHE_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        raise IOError(f"캐시 저장 오류: {e}")
