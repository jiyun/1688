@echo off
chcp 936 >nul
set PYTHONDONTWRITEBYTECODE=1
if "%1" == "" (
	cls
	echo ��ʾ: ��Ҫ�û��������뽫��������HTML�ļ��Ϸŵ����������ļ��ϡ�
	echo Ŀ��HTML�ļ���Ҫʹ��singlefile�����չԤ�����档
	echo ������ʹ��Aria2c��Python��ؿ⣺requests��subprocess��splitext��BeautifulSoup��pandas
	echo ----------
	echo ʹ�÷�������HTML�ļ��Ϸŵ����������ļ��Ͽ�ʼ������
	echo ����ͬʱ�ϷŶ���ļ�ִ�����������ļ���
	echo ��Ҫ��ǰ��װ�����ᵽ�ı�Ҫ������չ��
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
	set var=������ɣ������˳� 
	for /l %%i in (2,-1,1) do (  
	@echo %var%%%i ...
	ping -n 2 127.1>nul
	)
	cd ..
)
