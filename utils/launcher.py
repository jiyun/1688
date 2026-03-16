#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动方式检测模块

检测程序是从资源管理器双击启动还是从命令行启动：
- 双击启动：自动进入GUI模式
- 命令行启动：使用CLI模式
"""

import sys
import os


def is_launched_from_explorer() -> bool:
    """
    检测是否从资源管理器双击启动
    
    Returns:
        bool: True表示从资源管理器双击启动，False表示从命令行启动
    """
    try:
        import psutil
        parent = psutil.Process().parent()
        if parent:
            parent_name = parent.name().lower()
            if sys.platform == 'win32':
                return parent_name == 'explorer.exe'
            elif sys.platform == 'darwin':
                return parent_name == 'finder'
            else:
                return parent_name in ('nautilus', 'dolphin', 'thunar', 'pcmanfm', 'nemo')
    except ImportError:
        pass
    except Exception:
        pass
    
    return _is_launched_from_explorer_fallback()


def _is_launched_from_explorer_fallback() -> bool:
    """
    检测是否从资源管理器双击启动（备用方法，无需psutil）
    
    Returns:
        bool: True表示从资源管理器双击启动，False表示从命令行启动
    """
    if sys.platform == 'win32':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            
            parent_pid = kernel32.GetCurrentProcessId()
            
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_VM_READ = 0x0010
            
            h_process = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, parent_pid)
            if h_process:
                try:
                    import ctypes.wintypes
                    MAX_PATH = 260
                    exe_name = ctypes.create_unicode_buffer(MAX_PATH)
                    kernel32.QueryFullProcessImageNameW(h_process, 0, exe_name, ctypes.byref(ctypes.wintypes.DWORD(MAX_PATH)))
                    kernel32.CloseHandle(h_process)
                    exe_path = exe_name.value.lower()
                    return 'explorer.exe' in exe_path
                except:
                    kernel32.CloseHandle(h_process)
        except Exception:
            pass
        
        try:
            if hasattr(sys, 'frozen'):
                return True
            
            if sys.stdin is None or not sys.stdin.isatty():
                return True
        except:
            pass
    
    elif sys.platform == 'darwin':
        try:
            if sys.stdin is None or not sys.stdin.isatty():
                return True
        except:
            pass
    
    else:
        try:
            if sys.stdin is None or not sys.stdin.isatty():
                return True
        except:
            pass
    
    return False


def should_start_gui() -> bool:
    """
    判断是否应该启动GUI模式
    
    Returns:
        bool: True表示应该启动GUI模式
    """
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg in ('--gui', '-g'):
                return True
            if arg in ('--help', '-h', '--version', '-v'):
                return False
            if arg == '--cli':
                return False
    
    return is_launched_from_explorer()
