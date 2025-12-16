# 🧩 마인크래프트 모드 자동 설치 · 업데이트 프로그램

마인크래프트 모드를 **자동으로 설치하고 최신 상태로 유지**하기 위한 데스크톱 프로그램입니다.
수동으로 모드를 관리하면서 발생하는 버전 충돌, 의존성 문제, 번거로운 업데이트 과정을 최소화하는 것을 목표로 합니다.

---

## ✨ 주요 기능

* 📦 **모드 자동 설치**
  선택한 모드를 `.minecraft/mods` 폴더에 자동으로 설치

* 🔄 **모드 업데이트 자동화**
  기존 모드와 최신 버전을 비교하여 필요한 경우만 업데이트

* 🧠 **모드 파일 분석**
  JAR 메타데이터 기반으로 모드 ID, 버전, 로더 정보 분석

* 🧩 **의존성 및 호환성 검사**
  Minecraft 버전 / Fabric · Forge · Quilt 로더 호환 여부 확인

* 🖥️ **GUI 기반 인터페이스**
  콘솔이 아닌 직관적인 그래픽 UI 제공

---

## 🛠️ 사용 기술

* **Language**: Python 3.x
* **GUI**: Tkinter (추후 PySide / CustomTkinter 확장 가능)
* **File Handling**: zipfile, json, pathlib
* **Target Platform**: Windows (macOS / Linux 확장 가능)

---

## 📂 프로젝트 구조

```text
project-root/
├─ main.py                # 프로그램 진입점
├─ gui/
│  └─ main_window.py      # 메인 GUI 로직
├─ core/
│  ├─ mod_scanner.py      # 모드 파일 분석
│  ├─ version_checker.py # 버전 비교 로직
│  └─ installer.py       # 설치 · 업데이트 처리
├─ assets/                # 아이콘 및 리소스
└─ README.md
```

---

## 🚀 실행 방법

```bash
python main.py
```

> Python 3.9 이상 권장

---

## ⚠️ 주의 사항

* 이 프로그램은 **비공식 도구**이며 Mojang 또는 모드 제작자와 직접적인 관련이 없습니다.
* 모드 설치 전 기존 파일 백업을 권장합니다.

---

## 📜 라이선스

MIT License

자유롭게 사용, 수정, 배포할 수 있습니다.

---
