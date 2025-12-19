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

def check_mod_for_update(mod: dict, target_mc_version: str) -> str:
    """
    Modrinth API를 사용하여 모드의 최신 버전 정보를 확인하고 상태를 반환합니다.

    :param mod: 모드 정보를 담은 딕셔너리
    :param target_mc_version: 사용자가 선택한 마인크래프트 버전
    :return: "업데이트 가능", "최신 버전", "버전 높음", "호환 버전 없음" 등
    """
    project_id = mod.get("project_id")
    if not project_id:
        return "프로젝트 ID 없음"

    loaders = mod.get("loaders", [])
    if not target_mc_version or not loaders:
        return "버전/로더 정보 부족"

    # Quilt는 Fabric 모드와 호환되므로 검색 시 Fabric도 포함
    search_loaders = list(loaders)
    if "quilt" in search_loaders and "fabric" not in search_loaders:
        search_loaders.append("fabric")

    # 1.20.1 -> 1.20 과 같이 주 버전을 추출
    major_mc_version = ".".join(target_mc_version.split(".")[:2])
    
    game_versions_to_check = list(dict.fromkeys([target_mc_version, major_mc_version]))

    try:
        versions = []
        # 1. 정확한 버전(e.g., 1.20.1)으로 먼저 검색, 없으면 주 버전(e.g., 1.20)으로 검색
        for gv in game_versions_to_check:
            params = {
                "loaders": json.dumps(search_loaders),
                "game_versions": json.dumps([gv])
            }
            res = requests.get(f"{MODRINTH_API_URL}/project/{project_id}/version", params=params, timeout=15)
            if res.status_code == 404: continue
            res.raise_for_status()
            
            versions = res.json()
            if versions:
                break

        if not versions:
            return "호환 버전 없음"

        latest_version_data = versions[0]
        latest_version_number = latest_version_data['version_number']
        current_version_str = mod.get('mod_version', '0').strip()

        # 현재 버전을 알 수 없는 경우, 업데이트 가능으로 처리
        if not current_version_str or current_version_str == '-' or current_version_str == '오류':
            mod["latest_version"] = latest_version_number
            latest_file = next((f for f in latest_version_data['files'] if f['primary']), latest_version_data['files'][0])
            mod['latest_filename'] = latest_file['filename']
            mod['download_url'] = latest_file['url']
            return "업데이트 가능"

        # 버전 비교
        try:
            normalized_latest = _normalize_version(latest_version_number)
            normalized_current = _normalize_version(current_version_str)
            
            latest_version = parse_version(normalized_latest)
            current_version = parse_version(normalized_current)

            if latest_version > current_version:
                latest_file = next((f for f in latest_version_data['files'] if f['primary']), latest_version_data['files'][0])
                mod["latest_version"] = latest_version_number
                mod['latest_filename'] = latest_file['filename']
                mod['download_url'] = latest_file['url']
                return "업데이트 가능"
            elif latest_version < current_version:
                return f"버전 높음" # ({current_version_str} > {latest_version_number})
            else:
                return "최신 버전"

        except Exception as e:
            # 버전 문자열 파싱에 실패하면, 단순 문자열 비교로 폴백
            if latest_version_number.lower() != current_version_str.lower():
                return "업데이트 확인" # 사용자가 직접 판단하도록 유도
            return "최신 버전"

    except requests.exceptions.RequestException:
        return "API 요청 실패"
    except (json.JSONDecodeError, IndexError, KeyError):
        return "API 응답 오류"


def get_compatible_version_details(project_id: str, loaders: list, target_mc_version: str) -> dict:
    """
    Modrinth API를 사용하여 주어진 Minecraft 버전에 호환되는 모드의 최신 버전 상세 정보를 가져옵니다.

    :param project_id: Modrinth 프로젝트 ID.
    :param loaders: 모드가 지원하는 로더 목록 (예: ["fabric"]).
    :param target_mc_version: 대상 마인크래프트 버전 (예: "1.20.1").
    :return: 최신 호환 버전의 상세 정보 (version_number, filename, download_url) 딕셔너리,
             없으면 빈 딕셔너리를 반환합니다.
    """
    if not project_id or not loaders or not target_mc_version:
        return {}

    search_loaders = list(loaders)
    if "quilt" in search_loaders and "fabric" not in search_loaders:
        search_loaders.append("fabric")

    major_mc_version = ".".join(target_mc_version.split(".")[:2])
    game_versions_to_check = list(dict.fromkeys([target_mc_version, major_mc_version])) # Prioritize exact match

    try:
        versions_data = []
        for gv in game_versions_to_check:
            params = {
                "loaders": json.dumps(search_loaders),
                "game_versions": json.dumps([gv]),
                "featured": "true" # Prioritize featured versions
            }
            res = requests.get(f"{MODRINTH_API_URL}/project/{project_id}/version", params=params, timeout=15)
            if res.status_code == 404: continue
            res.raise_for_status()
            
            current_gv_versions = res.json()
            if current_gv_versions:
                versions_data.extend(current_gv_versions)
            
        if not versions_data:
            return {}

        best_version_found = None
        for gv_search in [target_mc_version, major_mc_version]:
            for version_entry in versions_data:
                if gv_search in version_entry['game_versions'] and any(loader in search_loaders for loader in version_entry['loaders']):
                    best_version_found = version_entry
                    break # Found the latest compatible for this game_version_search
            if best_version_found:
                break # Found the best overall

        if not best_version_found:
            return {}

        latest_file = next((f for f in best_version_found['files'] if f['primary']), best_version_found['files'][0])
        
        return {
            "version_number": best_version_found['version_number'],
            "filename": latest_file['filename'],
            "download_url": latest_file['url']
        }

    except requests.exceptions.RequestException as e:
        print(f"Modrinth API 요청 실패: {e}")
        return {}
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        print(f"Modrinth API 응답 처리 오류: {e}")
        return {}


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
