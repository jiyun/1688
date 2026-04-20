@echo off
chcp 936 >nul
set PYTHONDONTWRITEBYTECODE=1
title __pycache__ �������
echo ����ɨ�� __pycache__ Ŀ¼...
set count=0
for /d /r "%~dp0.." %%d in (__pycache__) do (
    if exist "%%d" (
        echo   ɾ��: %%d
        rd /s /q "%%d" 2>nul
        set /a count+=1
    )
)
if %count%==0 (
    echo δ���� __pycache__ Ŀ¼����Ŀ�������
) else (
    echo ������ %count% �� __pycache__ Ŀ¼
)
pause
