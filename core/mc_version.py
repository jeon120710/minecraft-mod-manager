import zipfile
import json
import re
from pathlib import Path
import toml

def detect_mc_version_and_name(filename: str, mods_dir: Path):
    jar_path = mods_dir / filename

    mc_version = None
    mod_name = None
    mod_version = None

    try:
        with zipfile.ZipFile(jar_path, "r") as z:
            # Fabric/Quilt
            for f in ["fabric.mod.json", "quilt.mod.json"]:
                if f in z.namelist():
                    data = json.loads(z.read(f).decode("utf-8"))
                    mod_name = data.get("name") or data.get("id")
                    mod_version = data.get("version")
                    mc_dep = data.get("depends", {}).get("minecraft")
                    if mc_dep:
                        match = re.search(r"(\d+\.\d+(?:\.\d+)?)", mc_dep)
                        if match:
                            mc_version = match.group(1)
                    return mod_name, mc_version, mod_version

            # Forge
            if "META-INF/mods.toml" in z.namelist():
                data = toml.loads(z.read("META-INF/mods.toml").decode("utf-8"))
                mods_list = data.get("mods", [])
                if mods_list:
                    mod_name = mods_list[0].get("displayName") or mods_list[0].get("modId")
                    mod_version = mods_list[0].get("version")
                    # minecraft 의존성 확인
                    dependencies = data.get("dependencies", {}).get(mods_list[0].get("modId"), [])
                    for dep in dependencies:
                        if dep.get("modId") == "minecraft":
                            mc_version = dep.get("versionRange", "").split(",")[0].strip("[]")
                            match = re.search(r"(\d+\.\d+(?:\.\d+)?)", mc_version)
                            if match:
                                mc_version = match.group(1)
                            break
                    return mod_name, mc_version, mod_version
    except Exception as e:
        raise RuntimeError(f"버전 감지 오류 ({filename}): {e}")

    # 파일명 fallback
    mod_name = filename.replace(".jar","")
    mod_name = re.sub(r"-(fabric|quilt|forge|neoforge)$","",mod_name, flags=re.IGNORECASE)
    mod_name = re.sub(r"-\d+(\.\d+){1,2}$","",mod_name)
    if not mc_version:
        match = re.search(r"(\d+\.\d+(?:\.\d+)?)", filename)
        if match:
            mc_version = match.group(1)
    # mod_version fallback from filename
    match_ver = re.search(r'(\d+(?:\.\d+)+)', filename)
    if match_ver:
        mod_version = match_ver.group(1)

    return mod_name, mc_version, mod_version
