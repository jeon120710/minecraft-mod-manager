def apply_global_style(app):
    app.setStyleSheet("""
    /* 전역 설정 */
    QWidget {
        font-family: 'Pretendard';
        background-color: #1e1f22; /* 매우 어두운 배경 */
        color: #e0e1e6; /* 밝은 텍스트 */
        font-size: 14px; /* 가독성을 위한 폰트 크기 증가 */
        border: none;
    }

    /* 푸시 버튼 */
    QPushButton {
        background-color: #7289da; /* 선명한 강조색 */
        color: #ffffff;
        font-weight: 600; /* Pretendard-SemiBold */
        border-radius: 8px; /* 부드러운 모서리 */
        padding: 10px 20px; /* 넉넉한 여백 */
        margin: 4px;
    }
    QPushButton:hover {
        background-color: #5f73b8; /* 호버 시 약간 어둡게 */
    }
    QPushButton:pressed {
        background-color: #4e609c; /* 클릭 시 더 어둡게 */
    }
    /* 특정 버튼 (예: 닫기 버튼) */
    QPushButton#closeButton {
        background-color: #4f535c;
    }
    QPushButton#closeButton:hover {
        background-color: #6a6e78;
    }

    /* 테이블 위젯 */
    QTableWidget {
        background-color: #2d2f34; /* 배경보다 약간 밝은 색 */
        alternate-background-color: #33363c;
        gridline-color: #4f535c;
        selection-background-color: #7289da;
        selection-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #4f535c;
    }

    /* 테이블 헤더 */
    QHeaderView::section {
        background-color: #1e1f22;
        color: #e0e1e6;
        padding: 8px;
        font-weight: 700; /* Pretendard-Bold */
        border-bottom: 2px solid #7289da; /* 헤더 구분선 강조 */
        border-right: 1px solid #4f535c;
    }
    QHeaderView::section:last {
        border-right: none;
    }

    /* 프로그레스 바 */
    QProgressBar {
        background-color: #2d2f34;
        border: 1px solid #4f535c;
        border-radius: 8px;
        text-align: center;
        color: #e0e1e6;
    }
    QProgressBar::chunk {
        background-color: #7289da;
        border-radius: 6px;
    }

    /* 체크박스 */
    QCheckBox {
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border: 2px solid #4f535c;
        border-radius: 5px;
        background-color: #2d2f34;
    }
    QCheckBox::indicator:hover {
        border-color: #7289da;
    }
    QCheckBox::indicator:checked {
        background-color: #7289da;
        border-color: #7289da;
    }
    
    /* 메시지 박스 */
    QMessageBox {
        background-color: #2d2f34;
    }
    QMessageBox QLabel {
        color: #e0e1e6;
    }

    /* 다이얼로그 */
    QDialog {
        background-color: #1e1f22;
    }
    """)

