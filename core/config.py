# -*- coding: utf-8 -*-
import json
from pathlib import Path
from core.app_path import get_app_data_dir

CONFIG_FILE_PATH = get_app_data_dir() / "config.json"

def load_config() -> dict:
    """설정 파일을 불러옵니다. 파일이 없으면 빈 딕셔너리를 반환합니다."""
    if not CONFIG_FILE_PATH.exists():
        return {}
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_config(config_data: dict):
    """설정 파일에 저장합니다."""
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
    except IOError:
        # TODO: Log this error
        pass

def load_selected_version() -> str | None:
    """저장된 마인크래프트 버전을 불러옵니다."""
    config = load_config()
    return config.get("selected_mc_version")

def save_selected_version(version: str):
    """선택된 마인크래프트 버전을 저장합니다."""
    config = load_config()
    config["selected_mc_version"] = version
    save_config(config)
