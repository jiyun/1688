@echo off
chcp 65001 >nul
set PYTHONDONTWRITEBYTECODE=1
title ��������HTML�ļ�
for %%F in (*.HTML) do (
    echo ������: %%F
    call start1688.bat "%%F"
    timeout /t 1 >nul
)
echo �����������
pause