import os
import re
import requests
import subprocess
from os.path import splitext
from bs4 import BeautifulSoup

list_1 = []
list_2 = []
list_3 = []
list_5 = []

current_directory = os.getcwd()
print(f"当前目录名: {current_directory}")

file_name = os.path.join(current_directory, f"{current_directory}.html")
print(f"正在分析文件: {file_name}")

with open(file_name, 'r', encoding='utf-8') as file:
    html_content = file.read()
    soup = BeautifulSoup(html_content, 'html.parser')

    div_elements = soup.find_all('div', class_='img-list-wrapper')
    
    for div in div_elements:
        img_elements = div.find_all('img')
        for img in img_elements:
            list_1.append(img['data-sf-original-src']) 
			#当使用singlefile 采集页面时用data-sf-original-src 属性采集 普通方式采集的页面用 src 获取头图

prop_item_wrappers = soup.find_all('div', class_='prop-item-wrapper')
for prop_item_wrapper in prop_item_wrappers:
    prop_names = prop_item_wrapper.find_all('div', class_='prop-name')
    for prop_name in prop_names:
        list_2.append(prop_name.get_text())

num_new_lines = len(list_1) - len(list_2)

if num_new_lines > 0:
    list_2 = list_2[::-1] + ['T_{}'.format(i+1) for i in range(num_new_lines)]
    list_1 = list_1[::-1]
    list_2 = ["\n out=" + line for line in list_2]
    
for uri, line in zip(list_1, list_2):
    extension = splitext(uri)[1]
    line += extension
    list_5.append(uri + line)

content_details = soup.find_all('div', class_='content-detail')
for detail in content_details:
    paragraphs = detail.find_all('p') #或者div 与 P 可选
    for paragraph in paragraphs:
        images = paragraph.find_all('img')
        for img in images:
            list_3.append(img['data-lazyload-src'])
            new_list = [re.sub(r'\?.*$', '', uri) for uri in list_3]
            for i, uri in enumerate(new_list):
                new_uri = f"\n out=C_" + str(i) + splitext(uri)[1]
                new_list[i] += new_uri
            list_5.append(new_list[i])
with open('down.txt', 'w' ,encoding='utf-8') as file:
    for item in list_5:
        file.write("%s\n" % item)
subprocess.run(['aria2c', '-i', 'down.txt'], shell=True) 

