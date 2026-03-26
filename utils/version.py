#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本信息模块
从 version.json 读取版本信息
"""

import os
import json

def _load_version_info():
    """从 version.json 加载版本信息"""
    version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'version.json')
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            "version": "0.0.0",
            "release_date": "",
            "min_python": "3.11"
        }

_version_info = _load_version_info()

__version__ = _version_info.get("version", "0.0.0")
__author__ = "急云"
__release_date__ = _version_info.get("release_date", "")

VERSION_INFO = {
    "version": __version__,
    "author": __author__,
    "release_date": __release_date__,
    "python_min": _version_info.get("min_python", "3.11"),
}
