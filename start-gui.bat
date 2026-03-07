@echo off
chcp 65001 >nul
set "PYTHON=python"
set "MAIN_SCRIPT=main.py"

:: 检查Python是否可用
%PYTHON% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：未找到Python解释器
    echo 请确保Python已安装并添加到系统环境变量
    pause
    exit /b 1
)

:: 检查main.py是否存在
if not exist %MAIN_SCRIPT% (
    echo 错误：未找到main.py文件
    echo 请确保此批处理文件与main.py在同一目录
    pause
    exit /b 1
)

:: 启动GUI模式
echo 正在启动1688详情页资源采集工具 - GUI模式...
%PYTHON% %MAIN_SCRIPT% --gui
