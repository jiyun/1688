@echo off
chcp 936 >nul
set PYTHONDONTWRITEBYTECODE=1
if "%1" == "" (
	cls
	echo 提示: 需要用户参数，请将处理过的HTML文件拖放到本批处理文件上。
	echo 目标HTML文件需要使用singlefile插件扩展预览保存。
	echo 本工具使用Aria2c和Python相关库：requests、subprocess、splitext、BeautifulSoup、pandas
	echo ----------
	echo 使用方法：将HTML文件拖放到本批处理文件上开始处理。
	echo 可以同时拖放多个文件执行批量处理文件。
	echo 需要提前安装上面提到的必要依赖扩展。
	pause >nul
) else (
	@echo y|Cacls %* /c /t /p Everyone:f 2>nul
	if not exist "%~n1" (
		mkdir "%~n1"
		cd "%~n1"
		python ..\main.py "%~f1"
	) else (
		if exist "%~n1\rebuild.bat" (
			cd "%~n1"
			call rebuild.bat
		) else (
			cd "%~n1"
			python ..\main.py "%~f1"
		)
	)
	@echo [DEFAULT]>>#URL.url
	@echo BASEURL=https://detail.1688.com/offer/%~n1.html>>#URL.url
	@echo [InternetShortcut]>>#URL.url
	@echo URL=https://detail.1688.com/offer/%~n1.html>>#URL.url
	@echo IconIndex=41>>#URL.url
	@echo IconFile=C:\WINDOWS\system32\shell32.dll>>#URL.url
	set var=处理完成，即将退出 
	for /l %%i in (2,-1,1) do (  
	@echo %var%%%i ...
	ping -n 2 127.1>nul
	)
	cd ..
)
