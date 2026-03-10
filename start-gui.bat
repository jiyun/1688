@echo off
chcp 936 >nul
set PYTHONDONTWRITEBYTECODE=1
set "PYTHON=python"
set "MAIN_SCRIPT=main.py"

%PYTHON% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：未找到Python解释器
    echo 请确保Python已安装并添加到系统环境变量
    pause
    exit /b 1
)

if not exist %MAIN_SCRIPT% (
    echo 错误：未找到main.py文件
    echo 请确保此批处理文件与main.py在同一目录
    pause
    exit /b 1
)

echo 正在启动1688详情页资源采集工具 - GUI模式...
start "" /wait %PYTHON% %MAIN_SCRIPT% --gui
if %errorlevel% neq 0 (
    echo.
    echo 程序异常退出，错误代码: %errorlevel%
    pause
)
