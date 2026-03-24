@echo off
chcp 936 >nul
set PYTHONDONTWRITEBYTECODE=1
title 批量处理所有HTML文件
for %%F in (*.HTML) do (
    echo 正在处理: %%F
    call start1688.bat "%%F"
    timeout /t 1 >nul
)
echo 批量处理完成
pause
