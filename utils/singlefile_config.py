#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入 SingleFile 配置到浏览器
"""

import json
import os

# SingleFile 推荐配置 - 保存完整HTML
SINGLEFILE_CONFIG = {
    "profiles": {
        "__Default_Settings__": {
            # 不阻止任何资源
            "blockScripts": False,
            "blockStylesheets": False,
            "blockImages": False,
            "blockAudios": False,
            "blockVideos": False,
            "blockFonts": False,
            
            # 保留所有内容
            "removeFrames": False,
            "removeHiddenElements": False,
            "removeUnusedStyles": False,
            "removeUnusedFonts": False,
            "removeAlternativeImages": False,
            "removeAlternativeFonts": False,
            "removeAlternativeMedias": False,
            
            # 保存原始页面
            "saveRawPage": True,
            "saveOriginalURLs": True,
            "compressHTML": False,
            "compressContent": False,
            "compressCSS": False,
            
            # 加载延迟图片
            "loadDeferredImages": True,
            "loadDeferredImagesMaxIdleTime": 3000,
            "loadDeferredImagesBeforeFrames": True,
            
            # 文件名设置
            "filenameTemplate": "{page-title} ({date-locale}).{filename-extension}",
            "filenameConflictAction": "uniquify",
            "confirmFilename": False,
            
            # 其他设置
            "displayInfobar": True,
            "logsEnabled": True,
            "backgroundSave": True,
            "autoSaveDelay": 1,
            "maxResourceSize": 10,
            "maxResourceSizeEnabled": False,
            "networkTimeout": 0,
            "saveFavicon": True,
            "resolveLinks": True,
            "groupDuplicateImages": True,
            "moveStylesInHead": True,
            "insertMetaCSP": True,
            "insertSingleFileComment": True
        }
    },
    "rules": [],
    "maxParallelWorkers": 20,
    "processInForeground": False
}

def get_singlefile_config():
    """获取 SingleFile 配置"""
    return SINGLEFILE_CONFIG

def get_singlefile_config_json():
    """获取 SingleFile 配置 JSON 字符串"""
    return json.dumps(SINGLEFILE_CONFIG, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    print("SingleFile 推荐配置:")
    print(get_singlefile_config_json())
