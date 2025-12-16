from PySide6.QtCore import QThread, Signal
import time
from core.update_mod import update_mod

class UpdateWorker(QThread):
    progress = Signal(int)
    message = Signal(str)
    eta = Signal(str)
    finished = Signal()
    error = Signal(str) # Add error signal

    def __init__(self, mods):
        super().__init__()
        self.mods = mods

    def run(self):
        start = time.time()
        total = len(self.mods)
        for i, mod in enumerate(self.mods, 1):
            self.message.emit(f"업데이트 중: {mod['mod_name']}")
            try:
                update_mod(mod)
            except Exception as e:
                self.error.emit(f"모드 업데이트 오류: {mod['mod_name']}: {e}")
                # Continue with other mods even if one fails
            
            progress_value = int(i / total * 100)
            self.progress.emit(progress_value)
            elapsed = time.time() - start
            remain = int(elapsed / i * (total - i)) if i > 0 else 0
            self.eta.emit(f"예상 시간: {remain}초")
        self.finished.emit()
