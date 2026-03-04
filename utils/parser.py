# HTML解析工具
import re
from bs4 import BeautifulSoup
from os.path import splitext

class HTMLParser:
    def __init__(self, html_content):
        self.soup = BeautifulSoup(html_content, 'html.parser')
    
    def _extract_image_id(self, url):
        """从URL中提取图片唯一标识ID"""
        match = re.search(r'O1CN01\w+', url)
        return match.group() if match else None
    
    def _normalize_url(self, url):
        """标准化URL，移除后缀参数"""
        if url.endswith('_.webp'):
            url = url[:-6]
        if '.jpg_sum' in url:
            url = url.replace('.jpg_sum', '')
        return url
    
    def _get_color_card_urls(self):
        """获取色卡区所有图片URL（优先完整获取）"""
        color_card_urls = []
        color_card_ids = set()
        
        sku_filter_buttons = self.soup.find_all('button', class_=lambda x: x and 'sku-filter-button' in x.split())
        for button in sku_filter_buttons:
            img = button.find('img', class_=lambda x: x and 'ant-image-img' in x.split() if x else False)
            if img and 'data-sf-original-src' in img.attrs:
                color_url = self._normalize_url(img['data-sf-original-src'])
                img_id = self._extract_image_id(color_url)
                if img_id and img_id not in color_card_ids:
                    color_card_ids.add(img_id)
                    color_card_urls.append(color_url)
        
        expand_view_items = self.soup.find_all('div', class_=lambda x: x and 'expand-view-item' in x.split())
        for item in expand_view_items:
            img = item.find('img', class_=lambda x: x and 'ant-image-img' in x.split() if x else False)
            if img and 'data-sf-original-src' in img.attrs:
                color_url = self._normalize_url(img['data-sf-original-src'])
                img_id = self._extract_image_id(color_url)
                if img_id and img_id not in color_card_ids:
                    color_card_ids.add(img_id)
                    color_card_urls.append(color_url)
        
        return color_card_urls, color_card_ids
    
    def get_main_images(self):
        """获取主图链接
        
        逻辑：
        1. 先分析色卡区有多少张图
        2. 主图数量 = 主图区数量 - 色卡区数量
        3. 如果等于5，按顺序取前5张为主图
        4. 如果小于5，先取非色卡图片，再补充色卡图片（去重）
        """
        color_card_urls, color_card_ids = self._get_color_card_urls()
        
        main_area_all_urls = []
        
        selectors = [
            'div.img-list-wrapper',
            'ul.od-gallery-list',
            'div.module-od-picture-gallery'
        ]
        
        for selector in selectors:
            elements = self.soup.select(selector)
            if elements:
                for element in elements:
                    parent_classes = element.get('class', []) if element.name else []
                    if any('recommend-gallery' in c for c in parent_classes):
                        continue
                    
                    wrapper_elements = element.find_all('div', class_=lambda x: x and 'od-gallery-turn-item-wrapper' in x.split())
                    for wrapper in wrapper_elements:
                        if wrapper.find('div', class_='od-video-wrapper'):
                            continue
                        if wrapper.find(class_=lambda x: x and 'prepic-video' in x.split() if x else False):
                            img = wrapper.find('img', class_='od-gallery-img')
                            if img:
                                continue
                        if wrapper.find('img', class_='video-icon'):
                            continue
                        
                        img = wrapper.find('img', class_='od-gallery-img')
                        if img:
                            if 'data-sf-original-src' in img.attrs:
                                img_url = self._normalize_url(img['data-sf-original-src'])
                            elif 'src' in img.attrs and not img['src'].startswith('data:,'):
                                img_url = self._normalize_url(img['src'])
                            else:
                                continue
                            
                            main_area_all_urls.append(img_url)
                if main_area_all_urls:
                    break
        
        if not main_area_all_urls:
            return []
        
        main_image_count = len(main_area_all_urls) - len(color_card_urls)
        
        if main_image_count == 5:
            return main_area_all_urls[:5]
        
        if main_image_count < 5:
            main_images = []
            added_urls = set()
            
            for url in main_area_all_urls:
                img_id = self._extract_image_id(url)
                if img_id and img_id not in color_card_ids:
                    if url not in added_urls:
                        main_images.append(url)
                        added_urls.add(url)
                    if len(main_images) >= main_image_count:
                        break
            
            if len(main_images) < main_image_count:
                for url in main_area_all_urls:
                    img_id = self._extract_image_id(url)
                    if img_id and img_id in color_card_ids:
                        if url not in added_urls:
                            main_images.append(url)
                            added_urls.add(url)
                        if len(main_images) >= main_image_count:
                            break
            
            return main_images
        
        return main_area_all_urls[:5]
    
    def get_color_options(self):
        """获取颜色选项"""
        color_options = []
        
        sku_filter_buttons = self.soup.find_all('button', class_=lambda x: x and 'sku-filter-button' in x.split())
        if sku_filter_buttons:
            for button in sku_filter_buttons:
                label_name = button.find('span', class_=lambda x: x and 'label-name' in x.split() if x else False)
                if label_name:
                    color_name = label_name.get_text().strip()
                    
                    img = button.find('img', class_=lambda x: x and 'ant-image-img' in x.split() if x else False)
                    color_image = None
                    if img and 'data-sf-original-src' in img.attrs:
                        color_image = img['data-sf-original-src']
                        if '.jpg_sum' in color_image:
                            color_image = color_image.replace('.jpg_sum', '')
                    
                    color_options.append((color_name, color_image))
        
        if not color_options:
            expand_view_items = self.soup.find_all('div', class_=lambda x: x and 'expand-view-item' in x.split())
            for item in expand_view_items:
                label_name = item.find('span', class_=lambda x: x and 'label-name' in x.split() if x else False)
                item_label = item.find('span', class_=lambda x: x and 'item-label' in x.split() if x else False)
                
                color_name = None
                if label_name:
                    color_name = label_name.get_text().strip()
                elif item_label:
                    color_name = item_label.get('title') or item_label.get_text().strip()
                
                if color_name:
                    img = item.find('img', class_=lambda x: x and 'ant-image-img' in x.split() if x else False)
                    color_image = None
                    if img and 'data-sf-original-src' in img.attrs:
                        color_image = img['data-sf-original-src']
                        if '.jpg_sum' in color_image:
                            color_image = color_image.replace('.jpg_sum', '')
                    
                    color_options.append((color_name, color_image))
        
        if not color_options:
            prop_item_wrappers = self.soup.find_all('div', class_='prop-item-wrapper')
            for prop_item_wrapper in prop_item_wrappers:
                prop_names = prop_item_wrapper.find_all('div', class_='prop-name')
                for prop_name in prop_names:
                    color_name = prop_name.get_text().strip()
                    color_options.append((color_name, None))
        
        return color_options
    
    def get_detail_images(self):
        """获取详情图链接"""
        detail_images = []
        # 尝试多种选择器来找到详情图
        selectors = [
            'div.content-detail',
            'div#detail',
            'v-detail-p img',
            'div.module-od-product-description img'
        ]
        
        for selector in selectors:
            img_elements = self.soup.select(selector)
            for img in img_elements:
                if 'data-sf-original-src' in img.attrs:
                    detail_images.append(img['data-sf-original-src'])
                elif 'data-lazyload-src' in img.attrs:
                    detail_images.append(img['data-lazyload-src'])
                elif 'src' in img.attrs and not img['src'].startswith('data:,'):
                    detail_images.append(img['src'])
        
        # 过滤掉lazyload.png等占位图和空链接
        detail_images = [url for url in detail_images if url and 'lazyload.png' not in url]
        return detail_images
    
    def get_videos(self):
        """获取视频链接"""
        videos = []
        # 尝试多种方式找到视频
        # 1. 直接查找video标签
        video_tags = self.soup.find_all('video')
        for video in video_tags:
            if 'data-sf-original-src' in video.attrs:
                video_url = video['data-sf-original-src']
                if not video_url.startswith('http'):
                    video_url = 'https:' + video_url
                videos.append(video_url)
            elif 'src' in video.attrs:
                video_url = video['src']
                if not video_url.startswith('http'):
                    video_url = 'https:' + video_url
                videos.append(video_url)
        
        # 2. 查找包含视频链接的a标签
        if not videos:
            video_links = self.soup.select('a[href$=".mp4"]')
            for link in video_links:
                video_url = link['href']
                if not video_url.startswith('http'):
                    video_url = 'https:' + video_url
                videos.append(video_url)
        
        return videos
    
    def get_attributes(self):
        """获取商品属性"""
        attributes = []
        
        # 1. 优先处理用户提供的新表格结构
        # 查找包含商品属性的容器
        collapse_body = self.soup.select_one('div.antd-external-collapse.collapse-body')
        if collapse_body:
            # 使用更精确的方法提取属性
            import re
            # 首先获取整个collapse_body的HTML内容
            html_content = str(collapse_body)
            
            # 匹配所有的属性名和属性值，使用更宽松的模式处理不规范HTML
            # 简化的属性名匹配：查找<th>标签内的<span>内容
            name_pattern = r'<th[^>]*><span>([^<]+)</span>'
            names = re.findall(name_pattern, html_content)
            
            # 简化的属性值匹配：查找包含field-value的<span>内容
            value_pattern = r'<span\s+class=["\']?field-value["\']?>([^<]+)</span>'
            values = re.findall(value_pattern, html_content)
            
            # 确保属性名和属性值的数量匹配
            min_length = min(len(names), len(values))
            if min_length > 0:
                for name, value in zip(names[:min_length], values[:min_length]):
                    name = name.strip()
                    value = value.strip()
                    if name and value:
                        attributes.append((name, value))
        
        # 2. 尝试其他常见的属性结构
        # 尝试多种选择器来找到属性
        selectors = [
            ('div.od-pc-attribute', 'div.offer-attr-item', 'span.offer-attr-item-name', 'span.offer-attr-item-value'),
            ('div.module-od-product-attributes', 'tr.ant-descriptions-row', 'th.ant-descriptions-item-label', 'td.ant-descriptions-item-content'),
            ('div.core-attributes', 'li', 'p:first-child', 'p:last-child')
        ]
        
        for container_selector, item_selector, name_selector, value_selector in selectors:
            container = self.soup.select_one(container_selector)
            if container and not attributes:
                items = container.select(item_selector)
                for item in items:
                    # 处理标准的属性项
                    name_elem = item.select_one(name_selector)
                    value_elem = item.select_one(value_selector)
                    if name_elem and value_elem:
                        name = name_elem.get_text().strip()
                        value = value_elem.get_text().strip()
                        # 过滤掉空属性
                        if name and value:
                            attributes.append((name, value))
                if attributes:
                    break
        
        # 3. 作为最后手段，直接查找所有可能的属性结构
        if not attributes:
            # 查找所有包含属性的表格
            tables = self.soup.find_all('table')
            for table in tables:
                # 查找表格中的所有行
                rows = table.find_all('tr')
                for row in rows:
                    # 查找行中的所有 th 和 td
                    ths = row.find_all('th')
                    tds = row.find_all('td')
                    
                    # 确保 th 和 td 的数量匹配
                    if len(ths) == len(tds):
                        for th, td in zip(ths, tds):
                            # 提取属性名和值
                            name = th.get_text().strip()
                            value = td.get_text().strip()
                            # 过滤掉空属性
                            if name and value:
                                attributes.append((name, value))
                if attributes:
                    break
        
        # 4. 清理和去重属性
        cleaned_attributes = []
        seen_attributes = set()
        
        for name, value in attributes:
            # 去除多余的空白字符
            name = name.strip()
            value = value.strip()
            
            # 过滤掉空属性和重复属性
            if name and value:
                # 创建唯一键，避免重复
                attr_key = f"{name}:{value}"
                if attr_key not in seen_attributes:
                    seen_attributes.add(attr_key)
                    cleaned_attributes.append((name, value))
        
        return cleaned_attributes
