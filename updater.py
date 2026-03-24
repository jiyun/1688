#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1688采集工具 - 自动更新脚本"""

import os
import sys
import shutil
import zipfile
import tempfile
import subprocess
import time

def main():
    print("=" * 40)
    print("1688采集工具 - 自动更新")
    print("=" * 40)
    print()
    
    if len(sys.argv) < 2:
        print("错误: 缺少更新包参数")
        input("按回车键退出...")
        sys.exit(1)
    
    update_zip = sys.argv[1]
    restart = sys.argv[2] if len(sys.argv) > 2 else ""
    
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"项目目录: {project_dir}")
    print(f"更新包: {update_zip}")
    print()
    
    if not os.path.exists(update_zip):
        print("错误: 更新包不存在")
        input("按回车键退出...")
        sys.exit(1)
    
    print("[1/4] 解压更新包...")
    temp_dir = tempfile.mkdtemp(prefix="1688_update_")
    print(f"临时目录: {temp_dir}")
    
    try:
        with zipfile.ZipFile(update_zip, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        print("解压完成")
    except Exception as e:
        print(f"错误: 解压失败 - {e}")
        input("按回车键退出...")
        sys.exit(1)
    
    print()
    print("[2/4] 查找更新文件...")
    items = os.listdir(temp_dir)
    if not items:
        print("错误: 未找到更新文件")
        input("按回车键退出...")
        sys.exit(1)
    
    source_dir = os.path.join(temp_dir, items[0])
    if not os.path.isdir(source_dir):
        source_dir = temp_dir
    print(f"源目录: {source_dir}")
    
    print()
    print("[3/4] 覆盖文件...")
    print(f"正在复制文件到: {project_dir}")
    
    try:
        for root, dirs, files in os.walk(source_dir):
            rel_dir = os.path.relpath(root, source_dir)
            dest_dir = os.path.join(project_dir, rel_dir) if rel_dir != '.' else project_dir
            
            for d in dirs:
                dest_path = os.path.join(dest_dir, d)
                os.makedirs(dest_path, exist_ok=True)
            
            for f in files:
                src_path = os.path.join(root, f)
                dest_path = os.path.join(dest_dir, f)
                shutil.copy2(src_path, dest_path)
        
        print("文件复制完成")
    except Exception as e:
        print(f"警告: 部分文件复制失败 - {e}")
    
    print()
    print("[4/4] 清理临时文件...")
    try:
        shutil.rmtree(temp_dir)
    except:
        pass
    try:
        os.remove(update_zip)
    except:
        pass
    
    print()
    print("=" * 40)
    print("更新完成!")
    print("=" * 40)
    print()
    
    if restart == "restart":
        print("正在启动程序...")
        os.chdir(project_dir)
        subprocess.Popen([sys.executable, "main.pyw"], creationflags=subprocess.CREATE_NO_WINDOW)
    
    time.sleep(2)
    sys.exit(0)

if __name__ == "__main__":
    main()
