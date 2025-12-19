# -*- coding: utf-8 -*-
import zipfile
import json
import requests
import difflib
import re
import toml
from pathlib import Path

MODRINTH = "https://api.modrinth.com/v2"

# -----------------------------
# 1. jar에서 정보 추출
# -----------------------------

def extract_fabric_info(jar):
    """fabric.mod.json에서 모드 정보를 추출합니다."""
    data = json.loads(jar.read("fabric.mod.json").decode("utf-8"))
    
    mc_version = None
    if "minecraft" in data.get("depends", {}):
        mc_dep = str(data["depends"]["minecraft"])
        match = re.search(r"(\d+\.\d+(?:\.\d+)?)", mc_dep)
        if match:
            mc_version = match.group(1)

    return {
        "name": data.get("name"),
        "modid": data.get("id"),
        "version": data.get("version"),
        "mc_version": mc_version,
        "loaders": ["fabric"],
    }

def extract_forge_info(jar):
    """
    1. TOML 라이브러리로 파싱 (최상위, [[mods]] 내부 모두 확인)
    2. 실패 시 정규표현식으로 폴백
    """
    name = None
    modid = None
    loader = "forge"
    
    try:
        text = jar.read("META-INF/mods.toml").decode(errors="ignore")

        # 1. TOML 라이브러리로 분석 시도
        try:
            data = toml.loads(text)
            if "neoforge" in text.lower():
                loader = "neoforge"

            # 최상위 레벨에서 먼저 찾아보기
            if not modid:
                modid = data.get("modId")
            if not name:
                name = data.get("displayName")

            # [[mods]] 테이블 내부에서 찾아보기
            if not modid and "mods" in data and isinstance(data.get("mods"), list):
                for mod_table in data["mods"]:
                    if mod_table.get("modId"):
                        modid = mod_table.get("modId")
                        name = mod_table.get("displayName", name) # 이름이 있으면 갱신
                        break
            
        except Exception:
            pass # TOML 분석 실패 시, 아래의 정규표현식으로 넘어감

        # 2. 정규표현식으로 폴백
        if not modid:
            match = re.search(r'modId\s*=\s*"([^"]+)"', text)
            if match:
                modid = match.group(1)
    
        if not name:
            match = re.search(r'displayName\s*=\s*"([^"]+)"', text)
            if match:
                name = match.group(1)

    except Exception:
        # jar 파일에서 mods.toml을 읽는 것 자체를 실패한 경우
        return { "name": None, "modid": None, "loaders": ["forge"] }

    return {"name": name, "modid": modid, "loaders": [loader]}


def extract_mod_info(jar_path):
    """jar 파일에서 메타데이터를 추출합니다."""
    try:
        with zipfile.ZipFile(jar_path) as jar:
            if "fabric.mod.json" in jar.namelist():
                return extract_fabric_info(jar)
            if "META-INF/mods.toml" in jar.namelist():
                return extract_forge_info(jar)
    except (zipfile.BadZipFile, json.JSONDecodeError, toml.TomlDecodeError):
        return {} # 손상된 파일이거나 분석할 수 없는 경우
    return {}

# -----------------------------
# 2. Modrinth 검색 공통
# -----------------------------

def modrinth_search(query):
    """Modrinth에서 이름/ID로 검색합니다."""
    if not query: return []
    try:
        r = requests.get(f"{MODRINTH}/search", params={"query": query, "limit": 10}, timeout=10)
        r.raise_for_status()
        return r.json().get("hits", [])
    except requests.exceptions.RequestException:
        return []

def pick_best_match(query, hits):
    """검색 결과에서 가장 유사도가 높은 항목을 선택합니다."""
    best = None
    score = 0.0
    for h in hits:
        s1 = difflib.SequenceMatcher(None, query.lower(), h["title"].lower()).ratio()
        s2 = difflib.SequenceMatcher(None, query.lower(), h["slug"].lower()).ratio()
        s = max(s1, s2)
        if s > score:
            score = s
            best = h
    return best if score >= 0.7 else None

# -----------------------------
# 3. project_id → 버전 정보
# -----------------------------

def get_versions(project_id):
    """프로젝트의 모든 버전 정보를 가져옵니다."""
    try:
        r = requests.get(f"{MODRINTH}/project/{project_id}/version", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException:
        return []

def extract_loaders_mc_from_versions(versions):
    """버전 정보 목록에서 모든 로더와 MC 버전을 추출합니다."""
    loaders = set()
    mc_versions = set()
    for v in versions:
        loaders.update(v.get("loaders", []))
        mc_versions.update(v.get("game_versions", []))
    return sorted(list(loaders)), sorted(list(mc_versions))

# -----------------------------
# 4. 전체 파이프라인
# -----------------------------

def analyze_mod(jar_path):
    """jar 파일을 분석하여 Modrinth 프로젝트 정보와 모든 버전 목록을 반환합니다."""
    info = extract_mod_info(jar_path)
    name = info.get("name")
    modid = info.get("modid")
    project = None

    if name:
        hits = modrinth_search(name)
        project = pick_best_match(name, hits)
    if not project and modid:
        hits = modrinth_search(modid)
        project = pick_best_match(modid, hits)

    if not project:
        return {
            "status": "FAILED",
            "mod_name": name or modid or Path(jar_path).stem,
            "mod_version": info.get("version"),
            "mc_version": info.get("mc_version"),
            "all_mc_versions": [],
            "loaders": info.get("loaders"),
            "project_id": None,
            "detection_source": "File Only",
        }

    versions = get_versions(project["project_id"])
    all_loaders, all_mc_versions = extract_loaders_mc_from_versions(versions)

    # 파일에서 추출한 로더를 우선으로 하되, 없으면 Modrinth 정보 사용
    final_loaders = info.get("loaders") or all_loaders

    return {
        "status": "OK",
        "project_id": project["project_id"],
        "mod_name": project.get("title"),
        "mod_version": info.get("version"),
        "mc_version": info.get("mc_version"), # 파일에서 추출한 특정 MC 버전
        "all_mc_versions": all_mc_versions, # Modrinth의 모든 MC 버전
        "loaders": final_loaders,
        "detection_source": "Modrinth Search",
    }

# -----------------------------
# 5. 기존 코드와의 호환성을 위한 어댑터
# -----------------------------

def detect_mc_version_and_name(filename: str, mods_dir: Path):
    """`mod_scanner.py`에서 호출하는 함수. 결과를 기존 포맷에 맞춰 반환합니다."""
    jar_path = mods_dir / filename
    try:
        result = analyze_mod(jar_path)

        mod_name = result["mod_name"]
        mc_version = result["mc_version"]
        mod_version = result["mod_version"]
        project_id = result["project_id"]
        loaders = result["loaders"] or []
        detection_source = result["detection_source"]
        all_mc_versions = result["all_mc_versions"]

        # 파일 이름에서 MC 버전, 로더 정보 추출 (최후의 보루)
        if not mc_version:
            match = re.search(r'(?:[+_-]mc?|fabric-|forge-|-)(1\.\d{2,}(?:\.\d{1,2})?)', filename, re.IGNORECASE)
            if match: mc_version = match.group(1)
        if not loaders:
            fn_lower = filename.lower()
            if "fabric" in fn_lower: loaders.append("fabric")
            if "neoforge" in fn_lower: loaders.append("neoforge")
            if "forge" in fn_lower and "neoforge" not in fn_lower: loaders.append("forge")
            if "quilt" in fn_lower: loaders.append("quilt")

        return (mod_name, mc_version, mod_version, project_id, 
                list(set(loaders)), detection_source, all_mc_versions)
    
    except Exception as e:
        # 최종 예외 처리
        return Path(filename).stem, "오류", "오류", None, [], "Error", []
