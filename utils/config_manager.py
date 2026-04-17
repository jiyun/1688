import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

_PROJECT_ROOT = Path(__file__).parent.parent


class ConfigManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._cache = {}
        self._json_configs = {}

    def get_json_config(self, name: str) -> Dict:
        if name in self._json_configs:
            return self._json_configs[name]
        path = _PROJECT_ROOT / "config" / f"{name}.json"
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = {}
        else:
            data = {}
        self._json_configs[name] = data
        return data

    def save_json_config(self, name: str, data: Dict) -> bool:
        path = _PROJECT_ROOT / "config" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._json_configs[name] = data
            return True
        except Exception:
            return False

    def invalidate(self, name: str = None) -> None:
        if name:
            self._json_configs.pop(name, None)
        else:
            self._json_configs.clear()

    @property
    def project_root(self) -> Path:
        return _PROJECT_ROOT

    @property
    def config_dir(self) -> Path:
        return _PROJECT_ROOT / "config"

    @property
    def data_dir(self) -> Path:
        return _PROJECT_ROOT / "data"


def get_config_manager() -> ConfigManager:
    return ConfigManager()
