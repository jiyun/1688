@echo y|Cacls %* /c /t /p Everyone:f
mkdir %~n1
cd %~n1
python ..\1688-1.py
@echo [DEFAULT]>>#URL.url
@echo BASEURL=https://detail.1688.com/offer/%~n1.html>>#URL.url
@echo [InternetShortcut]>>#URL.url
@echo URL=https://detail.1688.com/offer/%~n1.html>>#URL.url
@echo IconIndex=41>>#URL.url
@echo IconFile=C:\WINDOWS\system32\shell32.dll>>#URL.url

pause