@echo off
if "%1" == "" (
	cls
	echo 注意：不要空运行此批处理！目标HTML需要使用singlefile浏览器插件进行预处理。
	echo 本程序调用了Aria2c 与 Python 以及相关库 requests、subprocess、splitext、BeautifulSoup、pandas
	echo ----------
	echo 用法：请将HTML文件拖放到这个批处理上启动。需要批量处理请执行另一个批处理。
	echo 别忘记安装上面要求的程序与扩展。
	pause >nul
) else (
	@echo y|Cacls %* /c /t /p Everyone:f 2>nul
	if not exist "%~n1" (
		mkdir "%~n1"&cd %~n1
		python ..\1688-1.py
	) else (
		if exist "%~n1\rebuild.bat" (
			cd %~n1
			call rebuild.bat
		) else (
			cd %~n1
			python ..\1688-1.py
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

	more +38 "%~f0" >>%~n1\rebuild.bat
	goto :eof
	@echo off
	title 正在重建...
	del C_*.* 2>nul&del T_*.* 2>nul&del video_*.* 2>nul&del *.jpg 2>nul&del *.png 2>nul&del *.gif 2>nul&del down*.txt 2>nul
	python ..\1688-1.py
)
