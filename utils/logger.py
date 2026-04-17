#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志模块
支持多级别日志、时间戳、模块标识
"""

import logging
import sys
from datetime import datetime
from typing import Optional

LOG_COLORS = {
    'DEBUG': '\033[36m',
    'INFO': '\033[37m',
    'SUCCESS': '\033[32m',
    'WARNING': '\033[33m',
    'ERROR': '\033[31m',
    'RESET': '\033[0m'
}

_gui_logger_instance: Optional['GUILogger'] = None


def set_gui_logger(logger):
    """设置GUI日志实例"""
    global _gui_logger_instance
    _gui_logger_instance = logger


def get_gui_logger():
    """获取GUI日志实例"""
    return _gui_logger_instance


def _should_use_colors() -> bool:
    """判断是否应该使用颜色输出"""
    import os
    if os.environ.get('NO_COLOR') or os.environ.get('TERM') == 'dumb':
        return False
    try:
        if sys.stdout is None:
            return False
        return sys.stdout.isatty()
    except:
        return False


class AppLogger:
    """应用统一日志器"""
    
    def __init__(self, name: str = "App"):
        self.name = name
        self._console_enabled = True
        self._gui_enabled = False
        self._context = {}
    
    def bind(self, **kwargs) -> 'AppLogger':
        """添加上下文信息，返回新实例"""
        new_logger = AppLogger(self.name)
        new_logger._console_enabled = self._console_enabled
        new_logger._gui_enabled = self._gui_enabled
        new_logger._context = {**self._context, **kwargs}
        return new_logger
    
    def _format_message(self, level: str, message: str) -> str:
        """格式化日志消息"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        parts = [f"[{timestamp}]", f"[{level}]"]
        if self.name != "App":
            parts.append(f"[{self.name}]")
        if self._context:
            ctx = " ".join(f"{k}={v}" for k, v in self._context.items())
            parts.append(f"[{ctx}]")
        parts.append(message)
        return " ".join(parts)
    
    def _log(self, level: str, message: str, gui_level: str = "info"):
        """内部日志方法"""
        formatted = self._format_message(level, message)
        
        if self._console_enabled:
            if _should_use_colors():
                color = LOG_COLORS.get(level, LOG_COLORS['INFO'])
                reset = LOG_COLORS['RESET']
                print(f"{color}{formatted}{reset}")
            else:
                print(formatted)
        
        if self._gui_enabled and _gui_logger_instance:
            _gui_logger_instance.log(message, gui_level)
    
    def debug(self, message: str):
        """调试级别日志"""
        self._log("DEBUG", message, "info")
    
    def info(self, message: str):
        """信息级别日志"""
        self._log("INFO", message, "info")
    
    def success(self, message: str):
        """成功级别日志"""
        self._log("SUCCESS", message, "success")
    
    def warning(self, message: str):
        """警告级别日志"""
        self._log("WARNING", message, "warning")
    
    def error(self, message: str):
        """错误级别日志"""
        self._log("ERROR", message, "error")
    
    def enable_gui(self, enabled: bool = True):
        """启用/禁用GUI日志"""
        self._gui_enabled = enabled
    
    def enable_console(self, enabled: bool = True):
        """启用/禁用控制台日志"""
        self._console_enabled = enabled


_loggers = {}


def get_logger(name: str = "App") -> AppLogger:
    """获取或创建日志器"""
    if name not in _loggers:
        _loggers[name] = AppLogger(name)
    return _loggers[name]


def log_debug(message: str, module: str = "App"):
    """调试日志"""
    get_logger(module).debug(message)


def log_info(message: str, module: str = "App"):
    """信息日志"""
    get_logger(module).info(message)


def log_success(message: str, module: str = "App"):
    """成功日志"""
    get_logger(module).success(message)


def log_warning(message: str, module: str = "App"):
    """警告日志"""
    get_logger(module).warning(message)


def log_error(message: str, module: str = "App"):
    """错误日志"""
    get_logger(module).error(message)
