@echo off
title 1688 资源处理工具

:: 检查是否有拖放的图片文件
if "%~1" neq "" (
    echo 处理单张图片: %~1
    python ..\main.py "%~1"
    pause
    exit
)

:MENU
cls
echo ==============================
echo 1688 资源处理工具
echo ==============================
echo 1. 重建资源采集过程
echo 2. 详情图拼接与主图放大
echo 3. 清理无用文件
echo 4. 封包该资源
echo 5. 退出
echo ==============================
echo 请选择操作 [1-5]:
echo ==============================
set /p choice=

if "%choice%"=="1" goto REBUILD
if "%choice%"=="2" goto RECUTPIC
if "%choice%"=="3" goto CLEAN
if "%choice%"=="4" goto PACK
if "%choice%"=="5" goto EXIT
if "%choice%"=="0" goto EXIT

:: 无效选择
echo 无效选择，请重新输入！
pause
goto MENU

:REBUILD
cls
echo ==============================
echo 正在重建资源采集过程...
echo ==============================

echo 删除现有文件...
del C_*.* 2^>nul^&del T_*.* 2^>nul^&del video_*.* 2^>nul^&del *.jpg 2^>nul^&del *.png 2^>nul^&del *.gif 2^>nul^&del down*.txt 2^>nul

echo 获取当前目录名...
for %%i in (.) do set "dir_name=%%~ni"

echo 构建HTML文件路径...
set "html_file=..\%dir_name%.html"

echo 运行主程序...
python ..\main.py "%html_file%"

echo ==============================
echo 重建完成！
echo ==============================
echo 3秒后自动关闭...
ping -n 4 127.0.0.1 >nul
exit

:RECUTPIC
cls
echo ==============================
echo 正在处理详情图拼接...
echo ==============================

echo 运行主程序处理图片...
python ..\main.py --process-images

echo ==============================
echo 处理完成！
echo ==============================
echo 3秒后返回菜单...
ping -n 4 127.0.0.1 >nul
goto MENU

:CLEAN
cls
echo ==============================
echo 正在清理无用文件...
echo ==============================

echo 删除临时文件...
del down.txt 2^>nul
del down_log.txt 2^>nul

echo 检查拼接结果...
if exist "拼接结果.jpg" (
    echo 发现拼接结果.jpg，删除原采集的详情图和主图...
    del C_*.jpg 2^>nul
    del T_*.jpg 2^>nul
    del 拼接结果.jpg 2^>nul
) else (
    echo 未发现拼接结果.jpg，仅删除临时文件...
    del 拼接结果.jpg 2^>nul
)
echo ==============================
echo 清理完成！
echo ==============================
echo 3秒后返回菜单...
ping -n 4 127.0.0.1 >nul
goto MENU

:PACK
cls
echo ==============================
echo 正在封包该资源...
echo ==============================

:: 获取当前目录名
for %%i in (.) do set "dir_name=%%~ni"

:: 回到上级目录
cd ..

:: 检查是否存在目录名.html和目录名目录
if exist "%dir_name%.html" (
    if exist "%dir_name%" (
        echo 开始压缩...
        echo 执行压缩命令...
        :: 使用Python脚本执行压缩，这样可以更好地控制压缩过程
        python -c "import os, sys; sys.path.append(os.getcwd()); from utils.file_handler import FileHandler; file_handler = FileHandler({}); success = file_handler.pack_resources('%dir_name%'); print('压缩成功！' if success else '压缩失败！')"
        
        echo 压缩完成！
        
        echo 封包完成！
        echo 压缩包保存为: %dir_name%.zip
    ) else (
        echo 错误: 未找到 %dir_name% 目录！
        cd "%dir_name%"
    )
) else (
    echo 错误: 未找到 %dir_name%.html 文件！
    cd "%dir_name%"
)

echo ==============================
echo 封包完成！
echo ==============================
:: 自动关闭
cd "%dir_name%" 2^>nul
exit

:EXIT
cls
echo ==============================
echo 退出脚本...
echo ==============================
exit
