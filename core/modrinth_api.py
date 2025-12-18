import requests
import re
from packaging.version import parse as parse_version

def _sanitize_mod_name_for_search(name: str) -> str:
    s = re.sub(r"[\s_\.\-]+", " ", name)
    s = s.lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def check_mod_for_update(mod: dict) -> str:
    """
    Modrinth API를 사용하여 모드의 최신 버전 정보를 확인하고 상태를 반환합니다.

    :param mod: 모드 정보를 담은 딕셔너리
    :return: "업데이트 가능", "최신 버전", "Modrinth 확인됨", "프로젝트 못찾음", "호환 버전 없음", "Modrinth API 오류"
    """
    mod_name_for_search = _sanitize_mod_name_for_search(mod["mod_name"])
    
    try:
        # 1. 프로젝트 검색
        search_params = {"query": mod_name_for_search, "limit": 1}
        r = requests.get("https://api.modrinth.com/v2/search", params=search_params, timeout=10)
        r.raise_for_status()
        search_results = r.json()
        
        if not search_results.get("hits"):
            return "프로젝트 못찾음"
        
        project_id = search_results["hits"][0]["project_id"]

        # 2. 게임 버전에 맞는 최신 버전 검색
        version_params = {
            "loaders": [mod["loader"].lower()],
            "game_versions": [mod["mc_version"]]
        }
        r_ver = requests.get(f"https://api.modrinth.com/v2/project/{project_id}/version", params=version_params, timeout=10)
        r_ver.raise_for_status()
        versions = r_ver.json()

        if not versions:
            return "호환 버전 없음"

        latest_version_info = versions[0]
        latest_version_number = latest_version_info["version_number"]

        # 3. 버전 비교 (로컬 버전과 최신 버전)
        local_version = mod.get("mod_version", "0.0.0")

        # 버전 문자열 비교를 위해 'parse_version' 사용
        if parse_version(latest_version_number) > parse_version(local_version):
            mod["latest_version"] = latest_version_number
            mod["download_url"] = latest_version_info["files"][0]["url"]
            mod["latest_filename"] = latest_version_info["files"][0]["filename"]
            return "업데이트 가능"
        else:
            return "최신 버전"

    except requests.exceptions.RequestException:
        return "Modrinth API 오류"
    except Exception:
        return "확인 오류"
