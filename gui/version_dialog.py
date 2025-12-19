# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QDialogButtonBox,
    QMessageBox
)
from core.app_path import get_installed_mc_versions

class VersionSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("마인크래프트 버전 선택")
        self.setMinimumWidth(400)
        
        self.selected_version = None
        self.versions = get_installed_mc_versions()

        layout = QVBoxLayout(self)
        
        if not self.versions:
            # 설치된 버전을 찾을 수 없는 경우
            self.label = QLabel("마인크래프트 설치를 찾을 수 없거나,\nversions 폴더에 유효한 버전이 없습니다.")
            self.label.setWordWrap(True)
            layout.addWidget(self.label)
            
            button_box = QDialogButtonBox(QDialogButtonBox.Ok)
            button_box.accepted.connect(self.accept) # Ok 버튼 누르면 그냥 닫힘
            layout.addWidget(button_box)

        else:
            # 설치된 버전이 있는 경우
            self.label = QLabel("분석할 마인크래프트 버전을 선택하세요.\n(이 버전 기준으로 모드 업데이트를 확인합니다)")
            self.label.setWordWrap(True)
            layout.addWidget(self.label)

            self.list_widget = QListWidget()
            self.list_widget.addItems(self.versions)
            self.list_widget.setCurrentRow(0) # 첫 번째 항목을 기본으로 선택
            self.list_widget.itemDoubleClicked.connect(self.accept)
            layout.addWidget(self.list_widget)

            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(self.accept)
            button_box.rejected.connect(self.reject)
            layout.addWidget(button_box)

    def accept(self):
        """OK 버튼을 누르거나 항목을 더블클릭했을 때 호출됩니다."""
        if not self.versions:
            super().accept()
            return

        current_item = self.list_widget.currentItem()
        if current_item:
            self.selected_version = current_item.text()
            super().accept()
        else:
            # 혹시 모를 예외상황
            QMessageBox.warning(self, "선택 필요", "목록에서 버전을 선택해주세요.")

    @staticmethod
    def get_selected_version(parent=None):
        """
        다이얼로그를 띄우고 사용자가 선택한 버전 이름을 반환하는 static-method.
        선택하지 않거나 취소하면 None을 반환합니다.
        """
        dialog = VersionSelectionDialog(parent)
        if dialog.exec() == QDialog.Accepted:
            return dialog.selected_version
        return None
