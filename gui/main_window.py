from PySide6.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem, QCheckBox, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QProgressBar, QApplication, QHeaderView, QMessageBox, QDialog,
    QFileDialog, QFrame, QMenu
)
from PySide6.QtCore import Qt, QPropertyAnimation
from PySide6.QtGui import QColor, QFont, QAction
from pathlib import Path
import os
from gui.loader_worker import LoaderWorker
from gui.log_viewer import LogViewerDialog
from gui.update_worker import UpdateWorker
from gui.optimize_worker import OptimizeWorker
from gui.version_dialog import VersionSelectionDialog
from core.app_path import get_mods_dir
from core.config import save_selected_version

class MainWindow(QWidget):
    def __init__(self, selected_mc_version: str):
        super().__init__()
        self.setWindowTitle("마인크래프트 모드 관리자")
        self.resize(900, 700)
        self.selected_mc_version = selected_mc_version
        self.loading = None
        self.update_worker = None
        self.optimize_worker = None

        # --- 상단 버전 선택 UI ---
        self.version_info_layout = QHBoxLayout()
        self.version_label = QLabel(f"대상 마인크래프트 버전: {self.selected_mc_version}")
        font = self.version_label.font()
        font.setPointSize(10)
        self.version_label.setFont(font)
        
        self.change_version_btn = QPushButton("버전 변경")
        self.change_version_btn.clicked.connect(self._change_mc_version)

        self.version_info_layout.addWidget(self.version_label)
        self.version_info_layout.addStretch()
        self.version_info_layout.addWidget(self.change_version_btn)
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)

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
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_table_context_menu)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        # --- 하단 버튼 ---
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
        self.optimize_btn = QPushButton("버전 최적화")
        self.optimize_btn.clicked.connect(self._optimize_selected_mods)
        self.btn_layout.addWidget(self.optimize_btn)
        self.btn_layout.addWidget(self.select_folder_btn)
        self.btn_layout.addStretch()
        self.btn_layout.addWidget(self.log_btn)

        # --- 메인 레이아웃 ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        layout.addLayout(self.version_info_layout)
        layout.addWidget(line)
        layout.addWidget(self.info_label)
        layout.addWidget(self.table)
        layout.addLayout(self.btn_layout)
        
        self.info_label.hide()
        self.table.show()

        self.worker = None
        self.show() # MainWindow를 먼저 표시
        self.load_mods()

    def _change_mc_version(self):
        new_version = VersionSelectionDialog.get_selected_version(self)
        if new_version and new_version != self.selected_mc_version:
            self.selected_mc_version = new_version
            save_selected_version(new_version)
            self.version_label.setText(f"대상 마인크래프트 버전: {self.selected_mc_version}")
            self.load_mods() # 버전 변경 시 자동 새로고침
    
    def show_table_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return

        mod = self.mods[row]
        is_enabled = mod.get("enabled", True)
        
        menu = QMenu()
        toggle_action = QAction("모드 비활성화" if is_enabled else "모드 활성화", self)
        toggle_action.triggered.connect(lambda: self._toggle_mod_state(row))
        menu.addAction(toggle_action)
        
        menu.exec(self.table.mapToGlobal(pos))

    def _toggle_mod_state(self, row):
        mod = self.mods[row]
        is_currently_enabled = mod["enabled"]

        mods_dir = get_mods_dir()
        current_path = mods_dir / mod["file"]

        if is_currently_enabled:
            # Disable: .jar -> .jar.disabled
            new_path = current_path.with_suffix(".jar.disabled")
        else:
            # Enable: .jar.disabled -> .jar
            new_path = current_path.with_suffix('')
        
        new_filename = new_path.name

        try:
            os.rename(current_path, new_path)
            # Update model data first
            mod["enabled"] = not is_currently_enabled
            mod["file"] = new_filename
            # Then update the view
            self._update_row_display(row)
        except OSError as e:
            QMessageBox.critical(self, "오류", f"파일 이름 변경 실패: {e}")

    def _update_row_display(self, row):
        mod = self.mods[row]
        is_enabled = mod.get("enabled", True)

        # Update checkbox state
        checkbox_widget = self.table.cellWidget(row, 0)
        if checkbox_widget:
            checkbox = checkbox_widget.layout().itemAt(0).widget()
            checkbox.setEnabled(is_enabled)
            if not is_enabled:
                checkbox.setChecked(False)

        # Update file name text
        file_item = self.table.item(row, 1)
        if file_item:
            file_item.setText(mod.get("file", ""))

        # --- Update Status and Colors ---
        status = mod.get("status", "")
        
        # Determine text and color for the status column
        if not is_enabled:
            status_text = "비활성화됨"
            display_color = QColor("#808080")  # Gray for disabled
            tooltip = f"원래 상태: {status}"
        else:
            status_text = status
            tooltip = status
            # Determine status-specific color
            if status == "업데이트 가능": display_color = QColor("#f1c40f")
            elif status in ["최신 버전", "Modrinth 확인됨", "캐시됨"]: display_color = QColor("#2ecc71")
            elif "버전 높음" in status: display_color = QColor("#3498db")
            elif status in ["프로젝트 못찾음", "호환 버전 없음", "API 요청 실패", "API 응답 오류"]: display_color = QColor("#e67e22")
            elif "오류" in status or "실패" in status: display_color = QColor("#e74c3c")
            else: display_color = QColor("#95a5a6")

        # Update status item
        status_item = self.table.item(row, 4)
        if status_item:
            status_item.setText(status_text)
            status_item.setForeground(display_color)
            status_item.setToolTip(tooltip)
        
        # Update foreground color for the entire row
        if not is_enabled:
            # Set all text to gray
            for col in range(1, self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setForeground(display_color)
        else:
            # Revert other columns to default text color
            default_text_color = self.palette().color(self.foregroundRole())
            for col in range(1, 4):
                item = self.table.item(row, col)
                if item:
                    item.setForeground(default_text_color)
            
            # Set color for status column
            if status_item:
                status_item.setForeground(display_color)


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

        self.worker = LoaderWorker(self.selected_mc_version, mods_dir_path)
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

        self.show()
        QMessageBox.critical(self, "오류 발생!", f"작업 중 오류가 발생했습니다: {error_message}")
        
        self.refresh_btn.setEnabled(True)
        self.update_btn.setEnabled(True)
        self.worker = None
        self.update_worker = None

    def _on_mods_folder_not_found(self):
        if self.loading:
            self.loading.close()
        
        self.show()
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
            fade_out.finished.connect(self.show)
            fade_out.finished.connect(self.activateWindow)
            fade_out.start()
        else:
            self.show()

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
                # 체크박스 설정
                checkbox = QCheckBox()
                if not mod.get("enabled", True):
                    checkbox.setEnabled(False)
                box_layout.addWidget(checkbox)
                self.table.setCellWidget(row, 0, box_widget)

                # 나머지 셀 아이템 생성
                file_item = QTableWidgetItem(mod.get("file", ""))
                loaders_item = QTableWidgetItem(", ".join(mod.get("loaders", [])))
                mc_version_item = QTableWidgetItem(mod.get("mc_version", "-"))
                
                self.table.setItem(row, 1, file_item)
                self.table.setItem(row, 2, loaders_item)
                self.table.setItem(row, 3, mc_version_item)

                # MC 버전 툴팁 설정
                all_mc_versions = mod.get("all_mc_versions", [])
                if all_mc_versions:
                    tooltip_text = "이 프로젝트가 지원하는 모든 버전:\n\n" + ", ".join(all_mc_versions)
                    mc_version_item.setToolTip(tooltip_text)
                
                # 상태 아이템 생성 및 설정
                is_enabled = mod.get("enabled", True)
                status = mod.get("status", "")
                tooltip_status = status
                if not is_enabled:
                    status_text = "비활성화됨"
                    status_color = QColor("#808080") # 회색
                    tooltip_status = f"원래 상태: {status}"
                else:
                    status_text = status
                    # 상태별 색상 결정
                    if status == "업데이트 가능": status_color = QColor("#f1c40f")
                    elif status in ["최신 버전", "Modrinth 확인됨", "캐시됨"]: status_color = QColor("#2ecc71")
                    elif "버전 높음" in status: status_color = QColor("#3498db")
                    elif status in ["프로젝트 못찾음", "호환 버전 없음", "API 요청 실패", "API 응답 오류"]: status_color = QColor("#e67e22")
                    elif "오류" in status or "실패" in status: status_color = QColor("#e74c3c")
                    else: status_color = QColor("#95a5a6")

                status_item = QTableWidgetItem(status_text)
                status_item.setTextAlignment(Qt.AlignCenter)
                status_item.setForeground(status_color)
                status_item.setToolTip(tooltip_status)
                self.table.setItem(row, 4, status_item)

                # 비활성화된 모드의 모든 셀 글자색 변경
                if not is_enabled:
                    for col in range(1, self.table.columnCount()):
                        self.table.item(row, col).setForeground(status_color)

                # 모든 셀은 선택만 가능하도록 설정 (체크박스 제외)
                for col in range(1, self.table.columnCount()):
                    self.table.item(row, col).setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            
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
            self.optimize_btn.setEnabled(False) # Disable optimize button during update

            self.update_worker = UpdateWorker(mods_to_update)
            self.update_worker.progress.connect(self._on_progress)
            self.update_worker.message.connect(self._on_message)
            self.update_worker.eta.connect(self._on_eta)
            self.update_worker.finished.connect(self._on_update_finished)
            self.update_worker.error.connect(self._on_worker_error)
            self.update_worker.start()
            self.show_loading(f"{len(mods_to_update)}개 모드 업데이트 중...")

    def _optimize_selected_mods(self):
        selected_rows = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0).layout().itemAt(0).widget()
            if checkbox.isChecked():
                selected_rows.append(row)
        if not selected_rows:
            QMessageBox.warning(self, "경고", "최적화할 모드를 선택하세요.")
            return
        
        mods_to_optimize = []
        for row in selected_rows:
            mod = self.mods[row]
            if "버전 높음" in mod.get("status", ""): # Check for "버전 높음" status
                mods_to_optimize.append(mod)

        if not mods_to_optimize:
            QMessageBox.information(self, "알림", "선택된 모드 중 최적화 가능한 (버전이 높은) 항목이 없습니다.")
            return

        mod_names = ", ".join([f"'{m['mod_name']}'" for m in mods_to_optimize])
        reply = QMessageBox.question(self, "버전 최적화 확인", f"{mod_names} 모드의 버전을 현재 마인크래프트 버전({self.selected_mc_version})에 맞게 최적화하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if self.optimize_worker and self.optimize_worker.isRunning():
                QMessageBox.warning(self, "경고", "이미 모드 최적화 작업이 진행 중입니다.")
                return
            
            self.refresh_btn.setEnabled(False)
            self.update_btn.setEnabled(False)
            self.optimize_btn.setEnabled(False)

            self.optimize_worker = OptimizeWorker(mods_to_optimize, self.selected_mc_version)
            self.optimize_worker.progress.connect(self._on_progress)
            self.optimize_worker.message.connect(self._on_message)
            self.optimize_worker.eta.connect(self._on_eta)
            self.optimize_worker.finished.connect(self._on_optimize_finished)
            self.optimize_worker.error.connect(self._on_worker_error)
            self.optimize_worker.start()
            self.show_loading(f"{len(mods_to_optimize)}개 모드 버전 최적화 중...")


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
        self.optimize_btn.setEnabled(True) # Re-enable optimize button
        QMessageBox.information(self, "완료", "모드 업데이트가 완료되었습니다.")
        self.load_mods()
        self.update_worker = None

    def _on_optimize_finished(self):
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
        self.optimize_btn.setEnabled(True)
        QMessageBox.information(self, "완료", "모드 버전 최적화가 완료되었습니다.")
        self.load_mods()
        self.optimize_worker = None