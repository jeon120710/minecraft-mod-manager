import zipfile
import json
import re
from pathlib import Path
import toml
import hashlib
import requests
import os
from core.modrinth_cache import load_cache, save_cache, CACHE_TTL
import time
from packaging.version import parse as parse_version

MODRINTH_API_URL = "https://api.modrinth.com/v2"

def _get_file_hash(file_path: Path) -> str:
    """주어진 파일의 SHA512 해시를 계산합니다."""
    hasher = hashlib.sha512()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def _get_latest_mc_version(versions: list[str]) -> str | None:
    """
    주어진 버전 목록에서 가장 최신 버전을 찾아 반환합니다.
    """
    if not versions:
        return None

    release_pattern = re.compile(r"^\d+\.\d+")
    snapshot_pattern = re.compile(r"^\d{2}w\d{2}")

    release_versions = [v for v in versions if v and release_pattern.match(v)]
    snapshot_versions = [v for v in versions if v and snapshot_pattern.match(v)]

    if release_versions:
        try:
            release_versions.sort(key=parse_version, reverse=True)
            return release_versions[0]
        except Exception:
            return release_versions[0]
    
    if snapshot_versions:
        snapshot_versions.sort(reverse=True)
        return snapshot_versions[0]

    fallback_versions = [v for v in versions if v and not v[0].isalpha()]
    if fallback_versions:
        try:
            fallback_versions.sort(key=parse_version, reverse=True)
            return fallback_versions[0]
        except Exception:
            return fallback_versions[0]

    return None

def _get_mod_info_from_modrinth(file_hash: str) -> dict | None:
    """
    Modrinth API에서 파일 해시를 사용하여 모드 정보를 가져옵니다.
    정확한 API 호출 순서를 따릅니다: version_file -> version -> project
    """
    cache = load_cache()
    if file_hash in cache and time.time() - cache[file_hash].get("_time", 0) < CACHE_TTL:
        return cache[file_hash].get("mod_info")

    try:
        # 1. 해시로 version_id 찾기
        hash_res = requests.get(f"{MODRINTH_API_URL}/version_file/{file_hash}", params={'algorithm': 'sha512'}, timeout=5)
        if hash_res.status_code == 404:
            return None # Modrinth에 없는 모드
        hash_res.raise_for_status()
        version_file_data = hash_res.json()
        version_id = version_file_data.get("version_id")
        if not version_id:
            return None

        # 2. version_id로 상세 버전 정보 가져오기
        version_res = requests.get(f"{MODRINTH_API_URL}/version/{version_id}", timeout=5)
        version_res.raise_for_status()
        version_data = version_res.json()

        project_id = version_data.get("project_id")
        game_versions = version_data.get("game_versions")
        mod_version_num = version_data.get("version_number")
        
        # 3. project_id로 프로젝트 이름(mod_name) 가져오기
        mod_name = None
        if project_id:
            project_res = requests.get(f"{MODRINTH_API_URL}/project/{project_id}", timeout=5)
            project_res.raise_for_status()
            mod_name = project_res.json().get("title")

        mod_info = {
            "project_id": project_id,
            "mod_name": mod_name,
            "mod_version": mod_version_num,
            "mc_version": _get_latest_mc_version(game_versions),
        }
        
        cache[file_hash] = {"_time": time.time(), "mod_info": mod_info}
        save_cache(cache)
        
        return mod_info

    except requests.exceptions.RequestException as e:
        print(f"[경고] Modrinth API 요청 실패 (해시: {file_hash}): {e}")
        return None
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[경고] Modrinth API 응답 처리 실패 (해시: {file_hash}): {e}")
        return None

def detect_mc_version_and_name(filename: str, mods_dir: Path):
    jar_path = mods_dir / filename
    mod_name, mc_version, mod_version, project_id = None, None, None, None
    mod_version_file, mc_version_file = None, None

    # 1. 파일에서 메타데이터 추출 (폴백용)
    try:
        with zipfile.ZipFile(jar_path, "r") as z:
            if "fabric.mod.json" in z.namelist():
                data = json.loads(z.read("fabric.mod.json").decode("utf-8"))
                mod_name = data.get("name") or data.get("id")
                mod_version_file = data.get("version")
                if "minecraft" in data.get("depends", {}):
                    mc_dep = data["depends"]["minecraft"]
                    match = re.search(r"(\d+\.\d+(?:\.\d+)?)", mc_dep)
                    if match: mc_version_file = match.group(1)
            elif "META-INF/mods.toml" in z.namelist():
                data = toml.loads(z.read("META-INF/mods.toml").decode("utf-8"))
                if data.get("mods"):
                    mod_data = data["mods"][0]
                    mod_name = mod_data.get("displayName") or mod_data.get("modId")
                    mod_version_file = mod_data.get("version")
                    deps = data.get("dependencies", {}).get(mod_data["modId"], [])
                    for dep in deps:
                        if dep.get("modId") == "minecraft":
                            ver_range = dep.get("versionRange", "").split(",")[0].strip("[]()")
                            match = re.search(r"(\d+\.\d+(?:\.\d+)?)", ver_range)
                            if match: mc_version_file = match.group(1)
                            break
    except Exception as e:
        print(f"JAR 파일 메타데이터 처리 오류 {filename}: {e}")

    # 2. Modrinth에서 정보 조회 시도
    modrinth_data = None
    try:
        file_hash = _get_file_hash(jar_path)
        modrinth_data = _get_mod_info_from_modrinth(file_hash)
    except Exception as e:
        print(f"Modrinth 조회 중 오류 발생 {filename}: {e}")
    
    # 3. 정보 취합 (Modrinth 우선)
    if modrinth_data:
        project_id = modrinth_data.get("project_id")
        mod_name = modrinth_data.get("mod_name") or mod_name
        mod_version = modrinth_data.get("mod_version") or mod_version_file
        mc_version = modrinth_data.get("mc_version") or mc_version_file
    else:
        # Modrinth 조회 실패 시 파일 데이터 사용
        mod_version = mod_version_file
        mc_version = mc_version_file

    if not mod_name:
        mod_name = jar_path.stem.split('-')[0].replace('_', ' ').strip()

    return mod_name, mc_version, mod_version, project_id