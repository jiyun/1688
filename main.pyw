#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1688详情页资源采集工具 - GUI启动入口

双击此文件启动GUI界面，无控制台窗口
"""
import sys
import os

sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

if __name__ == '__main__':
    from gui.app import main as gui_main
    gui_main()
