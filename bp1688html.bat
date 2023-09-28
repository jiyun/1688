@echo off
setlocal enabledelayedexpansion
title 对抗反爬虫方案批量处理本地渲染页面中数据图像视频提取
set "interval=1"
for %%F in (*.HTML) do (
    echo 正在处理项目 %%F
    CALL start1688.bat %%FF
    timeout /t !interval! >nul
    cd %CD%
)
timeout /t !interval! >nul
