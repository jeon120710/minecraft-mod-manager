from PySide6.QtCore import QThread, Signal
import time
import requests
import shutil
from pathlib import Path
import os

from core.app_path import get_mods_dir
from core.modrinth_api import get_compatible_version_details

class OptimizeWorker(QThread):
    progress = Signal(int)
    message = Signal(str)
    eta = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, mods_to_optimize: list, target_mc_version: str):
        super().__init__()
        self.mods_to_optimize = mods_to_optimize
        self.target_mc_version = target_mc_version
        self.is_running = True

    def run(self):
        start_time = time.time()
        total_mods = len(self.mods_to_optimize)
        mods_dir = get_mods_dir()

        for i, mod in enumerate(self.mods_to_optimize):
            if not self.is_running:
                self.error.emit("버전 최적화 작업이 중단되었습니다.")
                return

            self.message.emit(f"({i+1}/{total_mods}) {mod['mod_name']} 버전 최적화 중...")
            self.progress.emit(int(((i + 1) / total_mods) * 100))

            # ETA 계산
            elapsed_time = time.time() - start_time
            avg_time_per_mod = elapsed_time / (i + 1) if i > 0 else 5 # 첫번째는 5초로 가정 (API 호출 및 다운로드)
            remaining_mods = total_mods - (i + 1)
            eta_seconds = remaining_mods * avg_time_per_mod
            self.eta.emit(f"남은 시간: {int(eta_seconds)}초")

            project_id = mod.get("project_id")
            loaders = mod.get("loaders", [])
            current_mod_filepath = mods_dir / mod["file"]

            if not project_id:
                self.message.emit(f"{mod['mod_name']}: 프로젝트 ID 없음. 건너뜁니다.")
                continue
            if not loaders:
                self.message.emit(f"{mod['mod_name']}: 로더 정보 없음. 건너뜁니다.")
                continue
            if not current_mod_filepath.exists():
                self.message.emit(f"{mod['mod_name']}: 모드 파일 '{mod['file']}'을(를) 찾을 수 없습니다. 건너뜁니다.")
                continue

            try:
                # 1. Modrinth에서 호환 버전 정보 가져오기
                compatible_version_details = get_compatible_version_details(
                    project_id, loaders, self.target_mc_version
                )

                if not compatible_version_details:
                    self.message.emit(f"{mod['mod_name']}: 현재 MC 버전({self.target_mc_version})에 호환되는 버전을 찾을 수 없습니다.")
                    continue
                
                download_url = compatible_version_details["download_url"]
                new_filename = compatible_version_details["filename"]
                new_version_number = compatible_version_details["version_number"]

                if not download_url:
                    self.message.emit(f"{mod['mod_name']}: 다운로드 URL을 찾을 수 없습니다. 건너뜁니다.")
                    continue

                # 2. 새로운 모드 파일 다운로드
                self.message.emit(f"{mod['mod_name']}: {new_version_number} 버전 다운로드 중...")
                response = requests.get(download_url, stream=True, timeout=30)
                response.raise_for_status()

                temp_download_path = mods_dir / f"{new_filename}.tmp"
                with open(temp_download_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not self.is_running:
                            self.error.emit("버전 최적화 작업이 중단되었습니다.")
                            return
                        f.write(chunk)
                
                # 3. 기존 모드 파일 삭제
                self.message.emit(f"{mod['mod_name']}: 기존 파일 삭제 중...")
                os.remove(current_mod_filepath)

                # 4. 다운로드된 파일 이름 변경
                final_mod_path = mods_dir / new_filename
                os.rename(temp_download_path, final_mod_path)

                self.message.emit(f"{mod['mod_name']}: {new_version_number} 버전으로 최적화 완료.")

            except requests.exceptions.RequestException as e:
                self.error.emit(f"{mod['mod_name']} API 요청 또는 다운로드 실패: {e}")
            except OSError as e:
                self.error.emit(f"{mod['mod_name']} 파일 작업 실패: {e}")
            except Exception as e:
                self.error.emit(f"{mod['mod_name']} 최적화 중 알 수 없는 오류: {e}")
        
        self.finished.emit()

    def quit(self):
        self.is_running = False
        super().quit()
