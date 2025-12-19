import requests
import json
import re
from packaging.version import parse as parse_version

MODRINTH_API_URL = "https://api.modrinth.com/v2"

def _normalize_version(version_str: str) -> str:
    """
    'v2.1-1.20.1' 또는 '5.0+mc1.20.1' 같은 복잡한 버전 문자열에서
    순수한 버전 번호(예: '2.1', '5.0')를 추출합니다.
    """
    if not version_str:
        return "0"
    
    # 0. 'fabric-1.2.3', 'forge-1.0' 같은 접두사 제거
    normalized = re.sub(r'^(?:fabric|forge|neoforge|quilt)-?', '', version_str, flags=re.IGNORECASE)

    # 1. Fabric API 같은 형식('0.140.0+1.21.11')에서 MC 버전을 먼저 제거
    # '+' 또는 '-' 뒤에 '1.x.x' 또는 '2xwx' 같은 MC 버전 문자열이 오는 경우
    normalized = re.sub(r'[+-](?=(?:\d{1,2}w\d{2,}|1\.\d{1,2}))', '#', normalized, 1).split('#')[0]

    # 2. 'mc1.20.4-0.5.4' 같은 형식에서 'mc...' 부분을 제거
    normalized = re.sub(r'^(?:mc)?\d+\.\d+(?:\.\d+)?-', '', normalized, 1)

    # 3. 남은 문자열에서 첫 번째 숫자 시퀀스(버전)를 찾고 그 이후는 버림
    match = re.search(r'(\d+(?:\.\d+)*)', normalized)
    if not match:
        return "0"  # 숫자로 시작하는 버전을 못 찾으면 0으로 처리
    normalized = match.group(1).rstrip('.')

    # 4. 'v' 또는 'V' 접두사 제거 (이미 정규식으로 처리되었을 수 있지만 안전장치)
    return normalized.lstrip('vV ')

def check_mod_for_update(mod: dict) -> str:
    """
    Modrinth API를 사용하여 모드의 최신 버전 정보를 확인하고 상태를 반환합니다.

    :param mod: 모드 정보를 담은 딕셔너리
    :return: "업데이트 가능", "최신 버전", "Modrinth 확인됨", "프로젝트 못찾음", "호환 버전 없음", "Modrinth API 오류"
    """
    project_id = mod.get("project_id")
    if not project_id:
        # 프로젝트 ID가 없으면 모드 이름으로 검색 시도 (Fallback)
        try:
            mod_name_for_search = mod.get("mod_name", "").lower().replace(" ", "-")
            search_params = {"query": mod_name_for_search, "limit": 1, "index": "relevance"}
            res = requests.get(f"{MODRINTH_API_URL}/search", params=search_params, timeout=10)
            res.raise_for_status()
            search_results = res.json()
            if search_results.get("hits"):
                project_id = search_results["hits"][0]["project_id"]
                mod["project_id"] = project_id # 찾은 ID를 mod 정보에 추가
            else:
                return "프로젝트 ID 없음" # 검색으로도 못 찾음
        except requests.exceptions.RequestException:
            return "프로젝트 ID 없음 (검색 실패)"

    mc_version = mod.get("mc_version")
    loaders = mod.get("loaders", [])

    if not mc_version or not loaders:
        return "버전/로더 정보 부족"

    # Quilt는 Fabric 모드와 호환되므로 검색 시 Fabric도 포함
    search_loaders = list(loaders)
    if "quilt" in search_loaders and "fabric" not in search_loaders:
        search_loaders.append("fabric")

    # 1.20.1 -> 1.20 과 같이 주 버전을 추출
    major_mc_version = ".".join(mc_version.split(".")[:2])
    
    # 검색할 게임 버전 목록 (예: ['1.20.1', '1.20'])
    # 중복을 제거하고 순서를 유지
    game_versions_to_check = list(dict.fromkeys([mc_version, major_mc_version]))

    try:
        versions = []
        # 1. 정확한 버전(e.g., 1.20.1)으로 먼저 검색
        # 2. 주 버전(e.g., 1.20)으로 다시 검색
        for gv in game_versions_to_check:
            params = {
                "loaders": json.dumps(search_loaders),
                "game_versions": json.dumps([gv])
            }
            res = requests.get(f"{MODRINTH_API_URL}/project/{project_id}/version", params=params, timeout=15)
            res.raise_for_status()
            versions = res.json()

            # 디버깅을 위해 불러온 정보를 콘솔에 표시
            if versions:
                break # 버전을 찾으면 루프 탈출

        # 모든 시도 후에도 버전이 없으면 호환 버전이 없는 것임
        if not versions:
            return "호환되는 최신 버전을 찾을 수 없음"

        # Find the latest version from the returned list
        latest_version_data = versions[0]
        latest_version_number = latest_version_data['version_number']
        current_version_str = mod.get('mod_version', '0').strip()

        # 비표준 버전 문자열을 처리하기 위해 정규화 후 버전 비교
        try:
            normalized_latest = _normalize_version(latest_version_number)
            normalized_current = _normalize_version(current_version_str)

            # 파싱 전에 문자열이 동일하면 바로 최신 버전으로 처리
            if normalized_latest == normalized_current:
                return "최신 버전"

            latest_version = parse_version(normalized_latest)
            current_version = parse_version(normalized_current)
        except Exception as e:
            print(f"[오류] 버전 비교 실패 ({mod.get('mod_name')}): '{current_version_str}' vs '{latest_version_number}' -> {e}")
            return "버전 비교 오류"

        if latest_version > current_version:
            # Find the primary file for the latest version
            latest_version_file = next((f for f in latest_version_data['files'] if f['primary']), latest_version_data['files'][0])
            
            mod["latest_version"] = latest_version_number
            mod['latest_filename'] = latest_version_file['filename']
            mod['download_url'] = latest_version_file['url']
            return "업데이트 가능"
        else:
            return "최신 버전"

    except requests.exceptions.RequestException as e:
        return f"API 요청 실패: {e}"
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        return f"API 응답 처리 오류: {e}"


def _fetch_versions_from_modrinth(project_id: str, loaders: list, game_versions: list, featured: bool) -> list:
    """Helper function to fetch versions from Modrinth."""
    try:
        params = {
            "loaders": json.dumps(loaders),
            "game_versions": json.dumps(game_versions),
            "featured": str(featured).lower()
        }
        res = requests.get(f"{MODRINTH_API_URL}/project/{project_id}/version", params=params, timeout=15)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"API 요청 실패 (params: {params}): {e}")
        return []
    except json.JSONDecodeError:
        print(f"API 응답 처리 오류 (params: {params})")
        return []
