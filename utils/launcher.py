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
    
    双击 .py 文件时：
    - 父进程直接是 explorer.exe（Windows 10/11 新方式）
    - 或者父进程是 cmd.exe，祖父进程是 explorer.exe
    
    命令行运行 main.py 时：
    - 父进程是 cmd.exe/powershell.exe
    - 祖父进程也是 explorer.exe（因为终端窗口从资源管理器启动）
    
    关键区别：
    - 双击启动时，stdin 不是 tty（或为 None）
    - 命令行启动时，stdin 是 tty
    
    Returns:
        bool: True表示从资源管理器双击启动，False表示从命令行启动
    """
    if sys.platform == 'win32':
        try:
            import ctypes
            from ctypes import wintypes
            
            kernel32 = ctypes.windll.kernel32
            
            TH32CS_SNAPPROCESS = 0x00000002
            
            class PROCESSENTRY32W(ctypes.Structure):
                _fields_ = [
                    ('dwSize', wintypes.DWORD),
                    ('cntUsage', wintypes.DWORD),
                    ('th32ProcessID', wintypes.DWORD),
                    ('th32DefaultHeapID', wintypes.ULONG),
                    ('th32ModuleID', wintypes.DWORD),
                    ('cntThreads', wintypes.DWORD),
                    ('th32ParentProcessID', wintypes.DWORD),
                    ('pcPriClassBase', wintypes.LONG),
                    ('dwFlags', wintypes.DWORD),
                    ('szExeFile', wintypes.WCHAR * 260),
                ]
            
            current_pid = kernel32.GetCurrentProcessId()
            
            h_snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            if h_snapshot:
                pe32 = PROCESSENTRY32W()
                pe32.dwSize = ctypes.sizeof(PROCESSENTRY32W)
                
                processes = {}
                if kernel32.Process32FirstW(h_snapshot, ctypes.byref(pe32)):
                    while True:
                        processes[pe32.th32ProcessID] = (pe32.th32ParentProcessID, pe32.szExeFile)
                        if not kernel32.Process32NextW(h_snapshot, ctypes.byref(pe32)):
                            break
                
                kernel32.CloseHandle(h_snapshot)
                
                if current_pid in processes:
                    parent_pid, parent_name = processes[current_pid]
                    parent_name_lower = parent_name.lower()
                    
                    if 'explorer.exe' in parent_name_lower:
                        return True
                    
                    if parent_name_lower in ('python.exe', 'pythonw.exe', 'python3.exe', 'python3.13.exe'):
                        return True
                    
                    if parent_pid in processes:
                        grandparent_pid, grandparent_name = processes[parent_pid]
                        grandparent_name_lower = grandparent_name.lower()
                        
                        if 'explorer.exe' in grandparent_name_lower:
                            if sys.stdin is None:
                                return True
                            try:
                                if not sys.stdin.isatty():
                                    return True
                            except (ValueError, OSError):
                                return True
        except Exception:
            pass
        
        try:
            if hasattr(sys, 'frozen'):
                return True
            
            if sys.stdin is None:
                return True
            
            try:
                if not sys.stdin.isatty():
                    return True
            except (ValueError, OSError):
                return True
        except:
            pass
    
    elif sys.platform == 'darwin':
        try:
            if sys.stdin is None:
                return True
            try:
                if not sys.stdin.isatty():
                    return True
            except (ValueError, OSError):
                return True
        except:
            pass
    
    else:
        try:
            if sys.stdin is None:
                return True
            try:
                if not sys.stdin.isatty():
                    return True
            except (ValueError, OSError):
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
    
    return is_launched_from_explorer()
