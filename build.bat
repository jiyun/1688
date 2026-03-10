@echo off
chcp 936 >nul
set PYTHONDONTWRITEBYTECODE=1
echo ====================================
echo 1688详情页资源采集工具 v0.3.0 打包脚本
echo ====================================
echo.

REM 设置版本号
set VERSION=0.3.0
set PACKAGE_NAME=1688-v%VERSION%

REM 创建打包目录
if exist "dist" rmdir /s /q "dist"
mkdir "dist\%PACKAGE_NAME%"

echo 正在复制文件...

REM 复制主要Python文件
copy main.py "dist\%PACKAGE_NAME%\"
copy config.py "dist\%PACKAGE_NAME%\"

REM 复制批处理文件
copy start1688.bat "dist\%PACKAGE_NAME%\"
copy start-gui.bat "dist\%PACKAGE_NAME%\"
copy bp1688html.bat "dist\%PACKAGE_NAME%\"

REM 复制GUI模块
xcopy gui "dist\%PACKAGE_NAME%\gui\" /E /I /Y

REM 复制工具模块
xcopy utils "dist\%PACKAGE_NAME%\utils\" /E /I /Y

REM 复制文档
copy README.md "dist\%PACKAGE_NAME%\"
copy CHANGELOG.md "dist\%PACKAGE_NAME%\"
copy LICENSE "dist\%PACKAGE_NAME%\"

REM 复制.gitignore
copy .gitignore "dist\%PACKAGE_NAME%\"

echo.
echo 正在创建ZIP压缩包...
cd dist
powershell -Command "Compress-Archive -Path '%PACKAGE_NAME%' -DestinationPath '%PACKAGE_NAME%.zip' -Force"
cd ..

echo.
echo ====================================
echo 打包完成！
echo 输出文件: dist\%PACKAGE_NAME%.zip
echo ====================================
pause
