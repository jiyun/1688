@echo off
chcp 936 >nul
if "%1" == "" (
	cls
	echo 警告: 不要在没有参数的情况下运行此批处理文件！
	echo 目标HTML文件需要使用singlefile浏览器扩展预处理。
	echo 此程序使用Aria2c、Python和相关库：requests、subprocess、splitext、BeautifulSoup、pandas
	echo ----------
	echo 使用方法：将HTML文件拖放到此批处理文件上开始处理。
	echo 如需批量处理，请执行另一个批处理文件。
	echo 不要忘记安装上述提到的必要程序和扩展。
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
	set var=处理完成，倒计时 
	for /l %%i in (2,-1,1) do (  
	@echo %var%%%i ...
	ping -n 2 127.1>nul
	)
	cd ..
)