import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QPushButton, QApplication, QTableWidget, 
    QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt
from pathlib import Path
import re, os, shutil
from core.update_mod import rollback_mod
from core.app_path import get_app_data_dir

APP_DATA_DIR = get_app_data_dir()
LOG_FILE = APP_DATA_DIR / "update_log.txt"

class LogViewerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("업데이트 로그")
        self.resize(800, 600) # 창 크기 조절 (가로, 세로)

        # 테이블
        self.table = QTableWidget(0, 5)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(["날짜", "모드 이름", "변경 사항", "파일", "작업"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # 날짜
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # 모드 이름
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # 변경 사항
        header.setSectionResizeMode(3, QHeaderView.Stretch)       # 파일 (경로가 길 수 있으므로)
        header.setSectionResizeMode(4, QHeaderView.Fixed) # 작업
        self.table.verticalHeader().setDefaultSectionSize(50) # 행 높이를 50px로 증가
        
        self.close_btn = QPushButton("닫기")
        self.close_btn.setObjectName("closeButton") # QSS를 위한 Object Name
        self.close_btn.clicked.connect(self.close)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15) # 여백 추가
        layout.setSpacing(10) # 간격 추가
        layout.addWidget(self.table)
        layout.addWidget(self.close_btn, alignment=Qt.AlignRight)

        self.load_logs()

    def load_logs(self):
        self.table.setRowCount(0) # 테이블 초기화
        if not LOG_FILE.exists():
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("로그 파일이 없습니다."))
            self.table.setSpan(0, 0, 1, 5)
            return

        logs = LOG_FILE.read_text(encoding="utf-8").strip().split("\n")
        self.table.setRowCount(len(logs))

        # Regex to parse the log entry
        log_pattern = re.compile(
            r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}): "
            r"(?P<mod_name>.*?) ?"  # Mod name (non-greedy), space is optional
            r"(?P<versions>[\w.+-]+\s->\s[\w.+-]+)? ?" # Optional versions group
            r"\(file: (?P<old_file>.*?) -> (?P<new_file>.*?)\)\s*$" # File changes, with optional trailing space
        )

        for row, log_entry in enumerate(reversed(logs)): # Show newest first
            match = log_pattern.match(log_entry)

            if match:
                data = match.groupdict()
                versions = data.get("versions") or "N/A" # Use N/A if versions not found
                self.table.setItem(row, 0, QTableWidgetItem(data["timestamp"]))
                self.table.setItem(row, 1, QTableWidgetItem(data["mod_name"]))
                self.table.setItem(row, 2, QTableWidgetItem(versions))
                self.table.setItem(row, 3, QTableWidgetItem(f"{data.get('old_file', '')} -> {data.get('new_file', '')}"))

                rollback_btn = QPushButton("롤백")
                rollback_btn.setMinimumHeight(40) # 버튼 높이를 40px로 설정
                # Store the necessary info for the rollback action
                rollback_btn.setProperty("old_file", data["old_file"])
                rollback_btn.setProperty("new_file", data["new_file"])
                rollback_btn.clicked.connect(self.rollback_triggered)
                self.table.setCellWidget(row, 4, rollback_btn)
            else:
                # Handle non-matching log entries (e.g., rollbacks, older formats)
                # 정규식과 일치하지 않는 로그 처리 (예: 롤백 로그, 이전 형식의 로그)
                timestamp, _, message = log_entry.partition(':')
                self.table.setItem(row, 0, QTableWidgetItem(timestamp.strip()))
                self.table.setItem(row, 1, QTableWidgetItem(message.strip()))
                self.table.setSpan(row, 1, 1, 3) # Span message across 3 columns

        self.table.resizeColumnsToContents()
        # Manually adjust width for the "작업" column (index 4)
        # as resizeColumnsToContents might not account for QPushButton widgets correctly.
        # A width of around 80-100 pixels should be enough for "롤백" button.
        self.table.setColumnWidth(4, 120)



    def rollback_triggered(self):
        button = self.sender()
        old_file = button.property("old_file")
        new_file = button.property("new_file")

        reply = QMessageBox.question(
            self,
            "롤백 확인",
            f"'{new_file}'을(를) '{old_file}'(으)로 롤백하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                rollback_mod(old_file, new_file) # Call the re-added function
                QMessageBox.information(self, "성공", "롤백이 완료되었습니다.\n모드 목록을 새로고침하여 변경사항을 확인하세요.")
                self.load_logs() # Refresh the log view
                self.accept() # Close the dialog
            except Exception as e:
                QMessageBox.critical(self, "오류", f"롤백에 실패했습니다:\n{e}")
                print(f"롤백 오류: {e}")



if __name__ == '__main__':
    app = QApplication(sys.argv)
    # This is for testing the dialog independently
    # Create a dummy log file
    # Create a dummy log file with various log types
    dummy_log = """2025-12-14 14:30:05: Some Mod 1.2.3 -> 1.3.0 (file: some-mod-1.2.3.jar -> some-mod-1.3.0.jar)
2025-12-14 14:32:10: Another Mod 2.0.0 -> 2.1.0 (file: another-mod-2.0.jar -> another-mod-2.1.0.jar)
2025-12-14 14:35:00: ROLLBACK: Rolled back 'another-mod-2.1.0.jar' to 'another-mod-2.0.jar'
"""
    LOG_FILE.write_text(dummy_log, encoding="utf-8")
    
    dialog = LogViewerDialog()
    dialog.exec()
    
    # Clean up dummy file
    LOG_FILE.unlink()
    # Clean up dummy file if it exists
    if LOG_FILE.exists():
        LOG_FILE.unlink()
    
    sys.exit(app.exec())
