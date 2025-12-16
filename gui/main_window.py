from PySide6.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem, QCheckBox, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QProgressBar, QApplication, QHeaderView, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, QPropertyAnimation, Signal, Slot
from PySide6.QtGui import QColor
from gui.loader_worker import LoaderWorker
from gui.log_viewer import LogViewerDialog
from gui.update_worker import UpdateWorker # Import UpdateWorker
import sys

class MainWindow(QWidget):
    initial_load_finished = Signal()
    initial_load_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.is_first_load = True
        self.setWindowTitle("Minecraft Mod Manager")
        self.resize(900, 700)
        self.loading = None
        self.update_worker = None # Initialize update_worker

        # 테이블
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["선택", "파일", "로더", "MC 버전", "상태"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch) # 파일 이름이 길 수 있으므로
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        # 버튼
        self.refresh_btn = QPushButton("새로고침")
        self.refresh_btn.clicked.connect(self.load_mods)
        self.update_btn = QPushButton("업데이트")
        self.update_btn.clicked.connect(self.update_selected_mods)
        self.log_btn = QPushButton("로그 보기")
        self.log_btn.clicked.connect(self.show_log_dialog)

        # 버튼 레이아웃
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 10, 0, 0)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.update_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.log_btn)

        # 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        layout.addWidget(self.table)
        layout.addLayout(btn_layout)

        # LoaderWorker
        self.worker = None

        self.load_mods()

    def load_mods(self):
        if self.worker and self.worker.isRunning():
            return

        # 이전 worker 정리
        if self.worker:
            self.worker.quit()
            self.worker.wait()

        self.worker = LoaderWorker()
        self.worker.progress.connect(self._on_progress)
        self.worker.message.connect(self._on_message)
        self.worker.eta.connect(self._on_eta)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_worker_error) # Connect error signal
        self.worker.start()
        self.show_loading("모드 정보 로딩중...") # Pass initial message

    def show_log_dialog(self):
        dialog = LogViewerDialog(self)
        # The dialog returns Accepted only if a rollback was successful
        if dialog.exec() == QDialog.Accepted:
            self.load_mods()


    def _on_worker_error(self, error_message):
        if self.loading:
            self.loading.close() # Close loading overlay if error occurs during loading

        if self.is_first_load:
            self.is_first_load = False
            self.initial_load_failed.emit(error_message)
        else:
            QMessageBox.critical(
                self, 
                "오류 발생!", 
                f"작업 중 오류가 발생했습니다: {error_message}\n\n도움이 필요하시면 Discord 서버에 문의해주세요:\nhttps://discord.gg/ERB7HUuG"
            )
        
        self.refresh_btn.setEnabled(True)
        self.update_btn.setEnabled(True)
        self.worker = None # Ensure worker is reset
        self.update_worker = None # Ensure worker is reset


    # -------------------- 로딩 UI --------------------
    def show_loading(self, initial_message="로딩중..."): # Accept initial message
        if self.loading is None:
            self.loading = QWidget(self, Qt.Dialog | Qt.FramelessWindowHint)
            self.loading.setObjectName("loadingWidget") # For styling if needed
            
            # 화면 정 중앙 배치
            screen = QApplication.primaryScreen().geometry()
            w, h = 350, 150 # 고정 크기
            x = screen.center().x() - w // 2
            y = screen.center().y() - h // 2
            self.loading.setGeometry(x, y, w, h)

            vbox = QVBoxLayout(self.loading)
            vbox.setAlignment(Qt.AlignCenter)

            self.loading_label = QLabel(initial_message) # Use initial message
            self.loading_label.setAlignment(Qt.AlignCenter)
            self.progress_bar = QProgressBar()
            self.progress_bar.setMaximum(100)
            self.eta_label = QLabel("")
            self.eta_label.setAlignment(Qt.AlignCenter)

            vbox.addWidget(self.loading_label)
            vbox.addSpacing(10)
            vbox.addWidget(self.progress_bar)
            vbox.addSpacing(6)
            vbox.addWidget(self.eta_label)

            # 페이드 인 애니메이션
            self.fade_anim = QPropertyAnimation(self.loading, b"windowOpacity", self.loading)
            self.fade_anim.setStartValue(0.0)
            self.fade_anim.setEndValue(1.0)
            self.fade_anim.setDuration(300)

        self.loading.show()
        self.fade_anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.loading and self.loading.isVisible():
            # 로딩 창을 화면 정 중앙에 유지
            screen = QApplication.primaryScreen().geometry()
            w, h = 350, 150
            x = screen.center().x() - w // 2
            y = screen.center().y() - h // 2
            self.loading.setGeometry(x, y, w, h)

    def _on_progress(self, value):
        if self.loading:
            self.progress_bar.setValue(value)

    def _on_message(self, msg):
        if self.loading:
            self.loading_label.setText(msg)

    def _on_eta(self, msg):
        if self.loading:
            self.eta_label.setText(msg)

    # -------------------- 테이블 업데이트 --------------------
    def _on_loaded(self, mods: list):
        self.mods = mods
        try:
            self.table.setRowCount(len(mods))
            for row, mod in enumerate(mods):
                # --- 체크박스 ---
                box_widget = QWidget()
                box_layout = QHBoxLayout(box_widget)
                box_layout.setContentsMargins(0, 0, 0, 0)
                box_layout.setAlignment(Qt.AlignCenter)
                checkbox = QCheckBox()
                box_layout.addWidget(checkbox)
                self.table.setCellWidget(row, 0, box_widget)

                # --- 나머지 셀 ---
                self.table.setItem(row, 1, QTableWidgetItem(mod.get("file", "")))
                self.table.setItem(row, 2, QTableWidgetItem(mod.get("loader", "")))
                self.table.setItem(row, 3, QTableWidgetItem(mod.get("mc_version", "")))
                
                # 모든 셀 편집 불가능하게
                for col in range(1, 4):
                    self.table.item(row, col).setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

                # --- 상태 컬럼 ---
                status = mod.get("status", "")
                status_item = QTableWidgetItem(status)
                status_item.setTextAlignment(Qt.AlignCenter)
                
                # 상태에 따라 텍스트 색상 변경
                if status == "업데이트 가능":
                    status_item.setForeground(QColor("#f1c40f")) # 노란색 계열
                    # 업데이트 가능 팝업은 사용자 경험을 해치므로 제거
                    # QMessageBox.information(self, "업데이트 가능", f"{mod['mod_name']}의 최신 버전이 있습니다.")
                elif status in ["Modrinth 확인됨", "캐시됨"]:
                    status_item.setForeground(QColor("#2ecc71")) # 녹색 계열
                elif status == "Modrinth 오류":
                    status_item.setForeground(QColor("#e74c3c")) # 빨간색 계열
                else: # 확인 중, 파일에서 추출됨 등
                    status_item.setForeground(QColor("#95a5a6")) # 회색 계열
                
                status_item.setToolTip(status)
                self.table.setItem(row, 4, status_item)
                self.table.item(row, 4).setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            
            self.table.resizeColumnsToContents() # Add this line
        except Exception as e:
            print(f"테이블 업데이트 오류: {e}")

        if self.loading:
            # 페이드 아웃 애니메이션
            fade_out = QPropertyAnimation(self.loading, b"windowOpacity", self.loading)
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            fade_out.setDuration(300)
            fade_out.finished.connect(self.loading.close)
            fade_out.finished.connect(self.activateWindow)
            fade_out.start()
        
        if self.is_first_load:
            self.is_first_load = False
            self.initial_load_finished.emit()

        self.worker = None

    def update_selected_mods(self):
        selected_rows = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0).layout().itemAt(0).widget()
            if checkbox.isChecked():
                selected_rows.append(row)
        if not selected_rows:
            QMessageBox.warning(self, "경고", "업데이트할 모드를 선택하세요.")
            return
        
        # UX 개선: 여러 모드 업데이트 시 한 번만 확인
        mods_to_update = []
        for row in selected_rows:
            mod = self.mods[row]
            if mod.get("status") == "업데이트 가능":
                mods_to_update.append(mod)

        if not mods_to_update:
            QMessageBox.information(self, "알림", "선택된 모드 중 업데이트 가능한 항목이 없습니다.")
            return

        mod_names = ", ".join([f"'{m['mod_name']}'" for m in mods_to_update])
        reply = QMessageBox.question(self, "업데이트 확인", f"{mod_names} 모드를 업데이트하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # UpdateWorker 사용
            if self.update_worker and self.update_worker.isRunning():
                return
            
            self.refresh_btn.setEnabled(False)
            self.update_btn.setEnabled(False)

            self.update_worker = UpdateWorker(mods_to_update)
            self.update_worker.progress.connect(self._on_progress)
            self.update_worker.message.connect(self._on_message)
            self.update_worker.eta.connect(self._on_eta)
            self.update_worker.finished.connect(self._on_update_finished)
            self.update_worker.error.connect(self._on_worker_error) # Connect error signal
            self.update_worker.start()
            self.show_loading(f"{len(mods_to_update)}개 모드 업데이트 중...") # Show update loading

    def _on_update_finished(self):
        if self.loading:
            fade_out = QPropertyAnimation(self.loading, b"windowOpacity", self.loading)
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            fade_out.setDuration(300)
            fade_out.finished.connect(self.loading.close)
            fade_out.finished.connect(self.activateWindow)
            fade_out.start()
        
        self.refresh_btn.setEnabled(True)
        self.update_btn.setEnabled(True)
        QMessageBox.information(self, "완료", "모드 업데이트가 완료되었습니다.")
        self.load_mods() # 모든 업데이트 후 한 번만 새로고침
        self.update_worker = None