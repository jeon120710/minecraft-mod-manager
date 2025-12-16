from PySide6.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem, QCheckBox, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QProgressBar, QApplication, QHeaderView, QMessageBox, QDialog,
    QFileDialog
)
from PySide6.QtCore import Qt, QPropertyAnimation, Signal, Slot
from PySide6.QtGui import QColor, QFont
from pathlib import Path
from gui.loader_worker import LoaderWorker
from gui.log_viewer import LogViewerDialog
from gui.update_worker import UpdateWorker
from core.mod_scanner import get_mods_dir
import sys

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minecraft Mod Manager")
        self.resize(900, 700)
        self.loading = None
        self.update_worker = None

        # --- 중앙 정보 라벨 ---
        self.info_label = QLabel(self)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setWordWrap(True)
        font = QFont()
        font.setPointSize(12)
        self.info_label.setFont(font)
        self.info_label.hide()

        # --- 테이블 ---
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["선택", "파일", "로더", "MC 버전", "상태"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        # --- 버튼 ---
        self.refresh_btn = QPushButton("새로고침")
        self.refresh_btn.clicked.connect(self.load_mods)
        self.update_btn = QPushButton("업데이트")
        self.update_btn.clicked.connect(self.update_selected_mods)
        self.log_btn = QPushButton("로그 보기")
        self.log_btn.clicked.connect(self.show_log_dialog)
        self.select_folder_btn = QPushButton("모드 폴더 선택...")
        self.select_folder_btn.clicked.connect(self._select_mods_folder)
        self.select_folder_btn.hide()

        # 버튼 레이아웃
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setContentsMargins(0, 10, 0, 0)
        self.btn_layout.addWidget(self.refresh_btn)
        self.btn_layout.addWidget(self.update_btn)
        self.btn_layout.addWidget(self.select_folder_btn)
        self.btn_layout.addStretch()
        self.btn_layout.addWidget(self.log_btn)

        # --- 메인 레이아웃 ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        layout.addWidget(self.info_label)
        layout.addWidget(self.table)
        layout.addLayout(self.btn_layout)
        
        self.info_label.hide()
        self.table.show()

        self.worker = None
        self.load_mods()

    def load_mods(self, mods_dir_path: str = None):
        if self.worker and self.worker.isRunning():
            return

        # UI 초기화
        self.info_label.hide()
        self.select_folder_btn.hide()
        self.refresh_btn.show()
        self.update_btn.show()
        self.table.show()
        self.table.clearContents()
        self.table.setRowCount(0)

        if self.worker:
            self.worker.quit()
            self.worker.wait()

        self.worker = LoaderWorker(mods_dir_path)
        self.worker.progress.connect(self._on_progress)
        self.worker.message.connect(self._on_message)
        self.worker.eta.connect(self._on_eta)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_worker_error)
        self.worker.mods_folder_not_found.connect(self._on_mods_folder_not_found)
        self.worker.start()
        self.show_loading("모드 정보 로딩중...")

    def _select_mods_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "모드 폴더를 선택하세요", str(Path.home()))
        if dir_path:
            self.load_mods(mods_dir_path=dir_path)

    def show_log_dialog(self):
        dialog = LogViewerDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.load_mods()

    def _on_worker_error(self, error_message):
        if self.loading:
            self.loading.close()

        QMessageBox.critical(self, "오류 발생!", f"작업 중 오류가 발생했습니다: {error_message}")
        
        self.refresh_btn.setEnabled(True)
        self.update_btn.setEnabled(True)
        self.worker = None
        self.update_worker = None

    def _on_mods_folder_not_found(self):
        if self.loading:
            self.loading.close()
        
        mods_path = get_mods_dir()
        self.table.hide()
        self.refresh_btn.hide()
        self.update_btn.hide()

        self.info_label.setText(
            f"모드 폴더를 찾을 수 없습니다.\n\n"
            f"기본 경로: {mods_path}\n\n"
            f"다른 경로에 모드 폴더가 있다면 직접 선택해주세요."
        )
        self.info_label.show()
        self.select_folder_btn.show()
        self.worker = None

    def show_loading(self, initial_message="로딩중..."):
        if self.loading is None:
            self.loading = QWidget(self, Qt.Dialog | Qt.FramelessWindowHint)
            self.loading.setObjectName("loadingWidget")
            
            screen = QApplication.primaryScreen().geometry()
            w, h = 350, 150
            x = screen.center().x() - w // 2
            y = screen.center().y() - h // 2
            self.loading.setGeometry(x, y, w, h)

            vbox = QVBoxLayout(self.loading)
            vbox.setAlignment(Qt.AlignCenter)

            self.loading_label = QLabel(initial_message)
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

            self.fade_anim = QPropertyAnimation(self.loading, b"windowOpacity", self.loading)
            self.fade_anim.setStartValue(0.0)
            self.fade_anim.setEndValue(1.0)
            self.fade_anim.setDuration(300)

        self.loading.show()
        self.fade_anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.info_label.setGeometry(0, 0, self.width(), self.height() - self.btn_layout.sizeHint().height() - 30)
        
        if self.loading and self.loading.isVisible():
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

    def _on_loaded(self, mods: list):
        if self.loading:
            fade_out = QPropertyAnimation(self.loading, b"windowOpacity", self.loading)
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            fade_out.setDuration(300)
            fade_out.finished.connect(self.loading.close)
            fade_out.finished.connect(self.activateWindow)
            fade_out.start()

        if not mods:
            self.table.hide()
            self.info_label.setText("모드 폴더에 설치된 모드가 없습니다.")
            self.info_label.show()
            self.select_folder_btn.hide()
            self.refresh_btn.show()
            self.update_btn.show()
            self.worker = None
            return
        
        self.info_label.hide()
        self.table.show()
        self.mods = mods
        try:
            self.table.setRowCount(len(mods))
            for row, mod in enumerate(mods):
                box_widget = QWidget()
                box_layout = QHBoxLayout(box_widget)
                box_layout.setContentsMargins(0, 0, 0, 0)
                box_layout.setAlignment(Qt.AlignCenter)
                checkbox = QCheckBox()
                box_layout.addWidget(checkbox)
                self.table.setCellWidget(row, 0, box_widget)

                self.table.setItem(row, 1, QTableWidgetItem(mod.get("file", "")))
                self.table.setItem(row, 2, QTableWidgetItem(mod.get("loader", "")))
                self.table.setItem(row, 3, QTableWidgetItem(mod.get("mc_version", "")))
                
                for col in range(1, 4):
                    self.table.item(row, col).setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

                status = mod.get("status", "")
                status_item = QTableWidgetItem(status)
                status_item.setTextAlignment(Qt.AlignCenter)
                
                if status == "업데이트 가능":
                    status_item.setForeground(QColor("#f1c40f"))
                elif status in ["Modrinth 확인됨", "캐시됨", "프로젝트는 찾았으나, 호환 파일 없음"]:
                    status_item.setForeground(QColor("#2ecc71"))
                elif status == "Modrinth 오류":
                    status_item.setForeground(QColor("#e74c3c"))
                else:
                    status_item.setForeground(QColor("#95a5a6"))
                
                status_item.setToolTip(status)
                self.table.setItem(row, 4, status_item)
                self.table.item(row, 4).setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            
            self.table.resizeColumnsToContents()
        except Exception as e:
            print(f"테이블 업데이트 오류: {e}")
        
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
            if self.update_worker and self.update_worker.isRunning():
                return
            
            self.refresh_btn.setEnabled(False)
            self.update_btn.setEnabled(False)

            self.update_worker = UpdateWorker(mods_to_update)
            self.update_worker.progress.connect(self._on_progress)
            self.update_worker.message.connect(self._on_message)
            self.update_worker.eta.connect(self._on_eta)
            self.update_worker.finished.connect(self._on_update_finished)
            self.update_worker.error.connect(self._on_worker_error)
            self.update_worker.start()
            self.show_loading(f"{len(mods_to_update)}개 모드 업데이트 중...")

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
        self.load_mods()
        self.update_worker = None