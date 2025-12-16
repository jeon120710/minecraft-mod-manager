from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, QPropertyAnimation


class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(0, 0, 0, 180), stop:1 rgba(20, 20, 20, 180));
            border-radius: 20px;
            border: 2px solid #666;
        """)
        self.setWindowFlags(Qt.FramelessWindowHint)

        self._fade_anim = None

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.status = QLabel("모드 검색 중...")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("font-size:16px; color: #e0e0e0; font-weight: 500;")

        self.progress = QProgressBar()
        self.progress.setFixedWidth(350)
        self.progress.setRange(0, 100)
        self.progress.setStyleSheet("""
            QProgressBar { background: #232323; border-radius: 8px; border: 1px solid #555; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0a84ff, stop:1 #0056b3); border-radius: 6px; }
        """)

        self.eta = QLabel("예상 시간 계산 중...")
        self.eta.setAlignment(Qt.AlignCenter)
        self.eta.setStyleSheet("color:#bbbbbb; font-size:12px;")

        layout.addWidget(self.status)
        layout.addSpacing(12)
        layout.addWidget(self.progress)
        layout.addSpacing(8)
        layout.addWidget(self.eta)

        self.resize(parent.size())
        self.move(0, 0)

        self.setWindowOpacity(0.0)

    def showEvent(self, event):
        super().showEvent(event)
        self._fade(0.0, 1.0, 300)

    def fade_out_and_close(self):
        self._fade(1.0, 0.0, 300, self.close)

    def _fade(self, start, end, duration, finished_cb=None):
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_anim.setStartValue(start)
        self._fade_anim.setEndValue(end)
        self._fade_anim.setDuration(duration)
        if finished_cb:
            self._fade_anim.finished.connect(finished_cb)
        self._fade_anim.start()
