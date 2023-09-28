import os
import re
import requests
import subprocess
from os.path import splitext
from bs4 import BeautifulSoup
import pandas as pd

list_1 = []
list_2 = []
list_3 = []
list_5 = []

current_directory = os.getcwd()
file_name = os.path.join(current_directory, f"{current_directory}.html")
with open(file_name, 'r', encoding='utf-8') as file:
    html_content = file.read()
soup = BeautifulSoup(html_content, 'html.parser')

## 获得头图URI
div_elements = soup.find_all('div', class_='img-list-wrapper')
for div in div_elements:
	img_elements = div.find_all('img')
	for img in img_elements:
		list_1.append(img['data-sf-original-src']) 
		#当使用singlefile 采集页面时用data-sf-original-src 属性采集 普通方式采集的页面用 src 获取头图
		
## 获得色卡名称
prop_item_wrappers = soup.find_all('div', class_='prop-item-wrapper')
for prop_item_wrapper in prop_item_wrappers:
    prop_names = prop_item_wrapper.find_all('div', class_='prop-name')
    for prop_name in prop_names:
        list_2.append(prop_name.get_text())

## 对头图和色卡名称进行拼合
num_new_lines = len(list_1) - len(list_2)
if num_new_lines > 0:
    list_2 = list_2[::-1] + ['T_{}'.format(i+1) for i in range(num_new_lines)]
    list_1 = list_1[::-1]
    list_2 = ["\n out=" + line for line in list_2]
    
for uri, line in zip(list_1, list_2):
    extension = splitext(uri)[1]
    line += extension
    list_5.append(uri + line)

## 获得详情图
content_details = soup.find_all('div', class_='content-detail')
for detail in content_details:
	images = detail.find_all('img')
	for img in images:
		try:
			list_3.append(img['data-lazyload-src'])
			new_list = [re.sub(r'\?.*$', '', uri) for uri in list_3]
			for i, uri in enumerate(new_list):
				new_uri = f"\n out=C_" + str(i) + splitext(uri)[1]
				new_list[i] += new_uri
			list_5.append(new_list[i])
		except:
			list_3.append(img['data-sf-original-src'])
			new_list = [re.sub(r'\?.*$', '', uri) for uri in list_3]
			for i, uri in enumerate(new_list):
				new_uri = f"\n out=C_" + str(i) + splitext(uri)[1]
				new_list[i] += new_uri
			list_5.append(new_list[i])

list_5 = [url for url in list_5 if 'lazyload.png' not in url]

## 将获得图片链接写入下载列表
with open('down.txt', 'w' ,encoding='utf-8') as file:
    for item in list_5:
        file.write("%s\n" % item)

## 获得页面中的视频
video_tags = soup.find_all('video')
for idx, video in enumerate(video_tags, start=1):
	data_sf_original_src = video.get('data-sf-original-src')
	if data_sf_original_src:
		if not data_sf_original_src.startswith("http"):
			data_sf_original_src = "https:" + data_sf_original_src
		with open('down.txt', 'a') as file:
			file.write(f"{data_sf_original_src}\n out=video_{idx}.mp4\n")
			
## 获得商品属性并简化保存到
offer_attr_list = soup.find('div', class_='od-pc-attribute')
offer_attr_items = offer_attr_list.find_all('div', class_='offer-attr-item')
data = []
for item in offer_attr_items:
    name = item.find('span', class_='offer-attr-item-name').get_text()
    value = item.find('span', class_='offer-attr-item-value').get_text()
    data.append((name, value))
df = pd.DataFrame(data, columns=['Name', 'Value'])
output_html = df.to_html(index=False)
with open('attribute.html', 'w') as file:
    file.write(output_html)

## 呼叫外部程序aria2c 批量下载 并生成下载日志
subprocess.run(['aria2c', '--console-log-level=warn', '-i', 'down.txt>>down_log.txt'], shell=True) 
