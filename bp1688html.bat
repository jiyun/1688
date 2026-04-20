@echo off
chcp 936 >nul
set PYTHONDONTWRITEBYTECODE=1
title ���������ǰĿ¼HTML�ļ�
for %%F in (*.HTML) do (
    echo ���ڴ���: %%F
    call start1688.bat "%%F"
    timeout /t 1 >nul
)
echo �����������
pause
