from PySide6.QtCore import QThread, Signal
import time
from core.mod_scanner import scan_mods, ModsFolderNotFoundError
from core.modrinth_api import check_mod_for_update
from core.modrinth_cache import load_cache, save_cache, CACHE_TTL

class LoaderWorker(QThread):
    progress = Signal(int)
    message = Signal(str)
    eta = Signal(str)
    finished = Signal(list)
    error = Signal(str)
    mods_folder_not_found = Signal()

    def __init__(self, target_mc_version: str, mods_dir_path: str = None):
        super().__init__()
        self.target_mc_version = target_mc_version
        self.mods_dir_path = mods_dir_path

    def run(self):
        start_time = time.time()
        
        # 1. 모드 스캔
        try:
            self.message.emit("모드 폴더를 스캔하는 중...")
            self.progress.emit(0)
            mods = scan_mods(self.mods_dir_path)
        except ModsFolderNotFoundError:
            self.mods_folder_not_found.emit()
            return
        except Exception as e:
            self.error.emit(f"모드 스캔 중 오류 발생: {e}")
            self.finished.emit([])
            return

        total = len(mods)
        if total == 0:
            self.progress.emit(100)
            self.message.emit("모드 정보 확인 완료")
            self.finished.emit([])
            return
            
        # 2. 캐시 로드
        self.message.emit(f"총 {total}개의 모드를 찾았습니다. 캐시된 정보 확인 중...")
        cache = load_cache()
        
        # 3. Modrinth에서 업데이트 확인
        self.message.emit("Modrinth에서 업데이트 확인 중...")
        
        updated_mods = []
        for i, mod in enumerate(mods):
            mod_key = f'{mod["mod_name"]}-{mod["mod_version"]}-{self.target_mc_version}'
            cached_mod = cache.get(mod_key)
            
            # ETA 계산
            elapsed_time = time.time() - start_time
            avg_time_per_mod = elapsed_time / (i + 1) if i > 0 else 0.5 # 첫번째는 0.5초로 가정
            remaining_mods = total - (i + 1)
            eta_seconds = remaining_mods * avg_time_per_mod
            self.eta.emit(f"남은 시간: {int(eta_seconds)}초")
            
            # 진행률 업데이트
            progress_percentage = int(((i + 1) / total) * 100)
            self.progress.emit(progress_percentage)
            self.message.emit(f"({i+1}/{total}) {mod['mod_name']} 확인 중...")
            
            if cached_mod and time.time() - cached_mod.get('_timestamp', 0) < CACHE_TTL:
                # 캐시가 유효하면 캐시된 데이터 사용
                mod.update(cached_mod)
                mod["status"] = cached_mod.get("status", "캐시됨")
            else:
                # 캐시가 없거나 만료되었으면 API 호출
                try:
                    status = check_mod_for_update(mod, self.target_mc_version)
                    mod["status"] = status
                    # 캐시 저장을 위해 현재 시간 기록
                    mod['_timestamp'] = time.time()
                    cache[mod_key] = mod
                except Exception as e:
                    mod["status"] = f"확인 오류: {e}"

            updated_mods.append(mod)

        # 4. 캐시 저장
        save_cache(cache)
        
        self.message.emit("모드 정보 확인 완료")
        self.finished.emit(updated_mods)
