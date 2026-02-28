# 文件处理工具
import os
import pandas as pd

# 导入配置
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import EXCLUDE_FILES

class FileHandler:
    def __init__(self, config):
        self.config = config
    
    def save_attributes(self, attributes, filename='attribute.html', directory='.'):
        """保存属性到HTML文件"""
        if not attributes:
            print("没有属性数据")
            return False
        
        # 保存为HTML文件
        df = pd.DataFrame(attributes, columns=['Name', 'Value'])
        output_html = df.to_html(index=False)
        output_path = os.path.join(directory, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_html)
        
        print(f"属性保存到: {output_path}")
        return True
    
    def generate_url_shortcut(self, product_id, directory='.'):
        """生成URL快捷方式"""
        url = f"https://detail.1688.com/offer/{product_id}.html"
        
        # 根据操作系统生成不同格式的快捷方式
        import platform
        system = platform.system()
        
        if system == 'Windows':
            # Windows 平台：生成 .url 文件
            shortcut_path = os.path.join(directory, '#URL.url')
            with open(shortcut_path, 'w', encoding='utf-8') as f:
                f.write('[DEFAULT]\n')
                f.write('BASEURL=' + url + '\n')
                f.write('[InternetShortcut]\n')
                f.write('URL=' + url + '\n')
                f.write('IconIndex=41\n')
                f.write('IconFile=C:\\WINDOWS\\system32\\shell32.dll\n')
        else:
            # macOS/Linux 平台：生成 .webloc 文件（macOS 格式）
            shortcut_path = os.path.join(directory, '#URL.webloc')
            with open(shortcut_path, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>' + '\n')
                f.write('<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">' + '\n')
                f.write('<plist version="1.0">' + '\n')
                f.write('<dict>' + '\n')
                f.write('\t<key>URL</key>' + '\n')
                f.write('\t<string>' + url + '</string>' + '\n')
                f.write('</dict>' + '\n')
                f.write('</plist>' + '\n')
        
        print(f"URL快捷方式生成到: {shortcut_path}")
        return True
    
    def create_rebuild_script(self, directory='.'):
        """创建重建脚本"""
        # 生成 Windows 版本的批处理文件
        script_path_bat = os.path.join(directory, 'rebuild.bat')
        
        # 批处理文件内容
        bat_content = r'''@echo off
title 1688 资源处理工具

:: 检查是否有拖放的图片文件
if "%~1" neq "" (
    echo 处理单张图片: %~1
    python ..\main.py "%~1"
    pause
    exit
)

:MENU
cls
echo ==============================
echo 1688 资源处理工具
echo ==============================
echo 1. 重建资源采集过程
echo 2. 详情图拼接与主图放大
echo 3. 清理无用文件
echo 4. 封包该资源
echo 5. 退出
echo ==============================
echo 请选择操作 [1-5]:
echo ==============================
set /p choice=

if "%choice%"=="1" goto REBUILD
if "%choice%"=="2" goto RECUTPIC
if "%choice%"=="3" goto CLEAN
if "%choice%"=="4" goto PACK
if "%choice%"=="5" goto EXIT
if "%choice%"=="0" goto EXIT

:: 无效选择
echo 无效选择，请重新输入！
pause
goto MENU

:REBUILD
cls
echo ==============================
echo 正在重建资源采集过程...
echo ==============================

echo 删除现有文件...
del C_*.* 2^>nul^&del T_*.* 2^>nul^&del video_*.* 2^>nul^&del *.jpg 2^>nul^&del *.png 2^>nul^&del *.gif 2^>nul^&del down*.txt 2^>nul

echo 获取当前目录名...
for %%i in (.) do set "dir_name=%%~ni"

echo 构建HTML文件路径...
set "html_file=..\%dir_name%.html"

echo 运行主程序...
python ..\main.py "%html_file%"

echo ==============================
echo 重建完成！
echo ==============================
echo 3秒后自动关闭...
timeout /t 3 /nobreak ^>nul
exit

:RECUTPIC
cls
echo ==============================
echo 正在处理详情图拼接...
echo ==============================

echo 运行主程序处理图片...
python ..\main.py --process-images

echo ==============================
echo 处理完成！
echo ==============================
echo 3秒后返回菜单...
timeout /t 3 /nobreak ^>nul
goto MENU

:CLEAN
cls
echo ==============================
echo 正在清理无用文件...
echo ==============================

echo 删除临时文件...
del down.txt 2^>nul
del down_log.txt 2^>nul

echo 检查拼接结果...
if exist "拼接结果.jpg" (
    echo 发现拼接结果.jpg，删除原采集的详情图和主图...
    del C_*.jpg 2^>nul
    del T_*.jpg 2^>nul
    del 拼接结果.jpg 2^>nul
) else (
    echo 未发现拼接结果.jpg，仅删除临时文件...
    del 拼接结果.jpg 2^>nul
)
echo ==============================
echo 清理完成！
echo ==============================
echo 3秒后返回菜单...
timeout /t 3 /nobreak ^>nul
goto MENU

:PACK
cls
echo ==============================
echo 正在封包该资源...
echo ==============================

:: 获取当前目录名
for %%i in (.) do set "dir_name=%%~ni"

:: 回到上级目录
cd ..

:: 检查是否存在目录名.html和目录名目录
if exist "%dir_name%.html" (
    if exist "%dir_name%" (
        echo 开始压缩...
        echo 执行压缩命令...
        :: 使用Python脚本执行压缩，这样可以更好地控制压缩过程
        python -c "import os, sys; sys.path.append(os.getcwd()); from utils.file_handler import FileHandler; file_handler = FileHandler({}); success = file_handler.pack_resources('%dir_name%'); print('压缩成功！' if success else '压缩失败！')"
        
        echo 压缩完成！
        
        echo 封包完成！
        echo 压缩包保存为: %dir_name%.zip
    ) else (
        echo 错误: 未找到 %dir_name% 目录！
        cd "%dir_name%"
    )
) else (
    echo 错误: 未找到 %dir_name%.html 文件！
    cd "%dir_name%"
)

echo ==============================
echo 封包完成！
echo ==============================
:: 自动关闭
cd "%dir_name%" 2^>nul
exit

:EXIT
cls
echo ==============================
echo 退出脚本...
echo ==============================
exit
'''
        
        # 使用GBK编码写入文件，并将LF转换为CRLF
        with open(script_path_bat, 'wb') as f:
            # 将LF转换为CRLF
            bat_content_crlf = bat_content.replace('\n', '\r\n')
            # 编码为GBK并写入
            f.write(bat_content_crlf.encode('gbk', errors='replace'))
        
        print(f"Windows 重建脚本生成到: {script_path_bat}")
        
        return True
    
    def create_recutpic_script(self, directory='.'):
        """创建图片处理脚本"""
        # 由于我们已经将图片处理功能合并到 rebuild.bat 中，不再需要单独的 recutpic.bat 脚本
        # 这里我们直接返回，不生成 recutpic.bat 脚本
        return True
    
    def pack_resources(self, directory='.'):
        """打包资源"""
        import zipfile
        import os
        import shutil
        
        print("开始打包资源...")
        
        # 获取绝对路径
        abs_dir = os.path.abspath(directory)
        # 获取当前目录名
        dir_name = os.path.basename(abs_dir)
        # 回到上级目录
        parent_dir = os.path.dirname(abs_dir)
        os.chdir(parent_dir)
        
        try:
            # 检查是否存在目录名.html和目录名目录
            html_file = f"{dir_name}.html"
            if os.path.exists(html_file) and os.path.exists(dir_name):
                # 创建压缩包
                zip_path = f"{dir_name}.zip"
                
                # 生成文件列表
                file_list = []
                excluded_files = EXCLUDE_FILES.get('pack_exclude', ['down.txt', 'down_log.txt', 'rebuild.bat'])
                
                # 首先添加HTML文件到压缩包根目录
                file_list.append((html_file, os.path.basename(html_file)))
                
                # 然后遍历目录中的所有文件，排除rebuild.txt、down.txt、down_log.txt、rebuild.bat等文件
                for root, dirs, files in os.walk(dir_name):
                    for file in files:
                        if file not in excluded_files:
                            file_path = os.path.join(root, file)
                            # 计算相对于目录的路径，然后添加目录名作为前缀，确保所有文件都在子目录中
                            rel_path = os.path.relpath(file_path, dir_name)
                            arcname = os.path.join(dir_name, rel_path)
                            file_list.append((file_path, arcname))
                
                # 提交给压缩环节
                print(f"共找到 {len(file_list)} 个文件，准备压缩...")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path, arcname in file_list:
                        zipf.write(file_path, arcname)
                
                print(f"压缩成功: {zip_path}")
                
                # 删除原文件与目录
                os.remove(html_file)
                shutil.rmtree(dir_name)
                print("删除成功")
                
                return True
            else:
                print(f"错误: 未找到 {html_file} 文件或 {dir_name} 目录")
                return False
        except Exception as e:
            print(f"打包失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # 回到原目录（仅当目录存在时）
            if os.path.exists(directory):
                os.chdir(directory)