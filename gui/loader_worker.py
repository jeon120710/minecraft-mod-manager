from PySide6.QtCore import QThread, Signal
import time, requests, re
from core.mod_scanner import scan_mods, ModsFolderNotFoundError
from core.modrinth_cache import load_cache, save_cache

class LoaderWorker(QThread):
    progress = Signal(int)
    message = Signal(str)
    eta = Signal(str)
    finished = Signal(list)
    error = Signal(str)
    mods_folder_not_found = Signal()

    def __init__(self, mods_dir_path: str = None):
        super().__init__()
        self.mods_dir_path = mods_dir_path

    def run(self):
        start = time.time()
        try:
            mods = scan_mods(self.mods_dir_path)
        except ModsFolderNotFoundError:
            self.mods_folder_not_found.emit()
            return

        total = len(mods)

        cached_mods = load_cache()  # 캐시 로드

        for i, mod in enumerate(mods, 1):
            mod_key = mod['file']
            # 캐시 적용
            if mod_key in cached_mods:
                # Modrinth API로 항상 최신 정보 확인 (캐시가 최신인지 확인)
                # 캐시된 정보는 기본값으로만 사용
                cached_data = cached_mods[mod_key]
                mod.update(cached_data) # 캐시된 로더, mc_version 등 업데이트
                status = "캐시됨"
            else:
                status = "파일에서 추출됨"
            
            # 항상 Modrinth 검색
            self.message.emit(f"Modrinth 검색: {mod.get('mod_name', mod['file'])}")


            # mod 이름 전처리 (파일명에서 버전, 로더, 플랫폼 등 제거)
            mod_name = mod.get("mod_name", mod["file"])
            search_name = self._sanitize_mod_name_for_search(mod_name)
            file_base = mod["file"].replace('.jar','')
            # 버전/로더/플랫폼 패턴 제거 (단순화)
            file_base_clean = re.sub(r'(-fabric|-forge|-quilt|-neoforge|-mc)?[0-9][^\-]*', '', file_base, flags=re.IGNORECASE)
            file_base_clean = re.sub(r'-\d+(\.\d+){1,2}.*', '', file_base_clean)
            file_base_clean = re.sub(r'[-_]+$', '', file_base_clean)
            file_base_clean = file_base_clean.strip('-_')

            current_mod_mc_ver = mod.get("mc_version") # 파일에서 추출된 mc_version 저장

            try:
                hits = []
                # 1차: search_name 기반 검색
                search_query = search_name
                r = requests.get(
                    "https://api.modrinth.com/v2/search",
                    params={"query": search_query, "limit": 1},
                    timeout=5
                )
                r.raise_for_status()
                hits = r.json().get("hits", [])
                
                # 2차: 실패 시 file_base_clean 사용
                if not hits and file_base_clean:
                    r2 = requests.get(
                        "https://api.modrinth.com/v2/search",
                        params={"query": file_base_clean, "limit": 1},
                        timeout=5
                    )
                    r2.raise_for_status()
                    hits = r2.json().get("hits", [])
                
                if hits:
                    project_id = hits[0]["project_id"]
                    # 최신 모드 버전 가져오기
                    r_ver = requests.get(f"https://api.modrinth.com/v2/project/{project_id}/version", params={"loaders": [mod["loader"].lower()]}, timeout=5)
                    r_ver.raise_for_status()
                    versions = r_ver.json()
                    
                    if versions:
                        latest_mod_ver = versions[0]["version_number"]
                        current_mod_ver = mod.get("mod_version", "")
                        if current_mod_ver and latest_mod_ver != current_mod_ver:
                            # 버전 비교 (단순 문자열, 필요시 개선)
                            if latest_mod_ver > current_mod_ver: # This string comparison is still an issue. Will address later.
                                status = "업데이트 가능"
                                mod["latest_mod_version"] = latest_mod_ver
                        # 버전이 같거나, 로컬 버전을 알 수 없는 경우 상태를 덮어쓰지 않음
                        # else: Do not overwrite status like "파일에서 추출됨"
                    else:
                        status = "프로젝트는 찾았으나, 호환 파일 없음" # 버전은 없지만 프로젝트는 찾음
                else:
                    status = "Modrinth 찾기 실패" # 프로젝트를 찾지 못함 (1차/2차 모두)
            except requests.RequestException as e:
                status = "Modrinth 오류"
                self.error.emit(f"Modrinth API 요청 오류: {mod['file']}: {e}")
            except Exception as e:
                status = "알 수 없는 오류"
                self.error.emit(f"모드 처리 중 예상치 못한 오류: {mod['file']}: {e}")

            mod["status"] = status
            if current_mod_mc_ver and (not mod.get("mc_version") or mod["mc_version"] == "-"):
                mod["mc_version"] = current_mod_mc_ver # 오류 등으로 Modrinth에서 MC 버전 못 가져왔을 시, 파일에서 추출한 버전 유지

            # 다음 실행을 위해 캐시 업데이트
            cached_mods[mod_key] = {
                'mc_version': mod.get('mc_version'),
                'mod_name': mod.get('mod_name'),
                'loader': mod.get('loader'),
                'status': mod.get('status') # 캐시에 상태도 저장 (다음 로딩 시 빠르게 표시)
            }

            # 진행 표시 (0으로 나누기 방지)
            progress_value = int(i / total * 100) if total > 0 else 100
            self.progress.emit(progress_value)
            elapsed = time.time() - start
            remain = int(elapsed / i * (total - i)) if i > 0 else 0
            self.eta.emit(f"남은 시간 약 {remain}초")

        save_cache(cached_mods)
        self.finished.emit(mods)

    # ------------------ 헬퍼 ------------------
    def _sanitize_mod_name_for_search(self, name: str) -> str:
        """
        Modrinth 검색용 이름 전처리
        - 띄어쓰기, 언더바, 점, - → 공백
        - 소문자화
        - 연속 공백 제거
        - 양 끝 공백 제거
        """
        s = re.sub(r"[\s_\.\-]+", " ", name)
        s = s.lower()
        s = re.sub(r"\s+", " ", s)
        return s.strip()
