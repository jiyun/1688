@echo off
chcp 936 >nul
title ��������HTML�ļ�
for %%F in (*.HTML) do (
    echo ������: %%F
    call start1688.bat "%%F"
    timeout /t 1 >nul
)
echo �����������
pause