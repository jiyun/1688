# 1688/阿里巴巴详情页解析器
import re
from typing import List, Tuple, Dict, Optional
from .base_parser import BaseParser


class AlibabaParser(BaseParser):
    """1688/阿里巴巴详情页解析器"""
    
    PLATFORM = 'alibaba'
    
    def __init__(self, html_content: str, keep_avif: bool = False, webp_support: bool = False):
        super().__init__(html_content)
        self.keep_avif = keep_avif
        self.webp_support = webp_support
    
    @staticmethod
    def detect_platform(html_content: str) -> bool:
        """检测是否为1688/阿里巴巴页面"""
        indicators = [
            '1688.com',
            'alicdn.com',
            'alibaba.com',
            'O1CN01'
        ]
        return any(indicator in html_content for indicator in indicators)
    
    def _extract_image_id(self, url: str) -> Optional[str]:
        """从URL中提取图片唯一标识ID"""
        match = re.search(r'O1CN01\w+', url)
        return match.group() if match else None
    
    def _normalize_url(self, url: str) -> str:
        """标准化URL，移除后缀参数"""
        if url.endswith('_.webp'):
            url = url[:-6]
        if '.jpg_sum' in url:
            url = url.replace('.jpg_sum', '')
        return url
    
    def _apply_webp_format(self, url: str) -> str:
        """应用WebP格式（阿里平台专用）
        
        阿里平台图片支持WebP格式，通过在URL末尾添加_.webp后缀获取
        """
        if not self.webp_support:
            return url
        
        # 如果URL已经包含_.webp，不再重复添加
        if url.endswith('_.webp'):
            return url
        
        # 移除现有的扩展名后缀（如.jpg），然后添加_.webp
        # 阿里CDN图片URL格式：https://cbu01.alicdn.com/img/ibank/O1CN01xxx_.webp
        if re.search(r'\.(jpg|jpeg|png|gif)(_\w+)?$', url, re.IGNORECASE):
            # 移除扩展名及其后缀
            url = re.sub(r'\.(jpg|jpeg|png|gif)(_\w+)?$', '', url, flags=re.IGNORECASE)
        
        return url + '_.webp'
    
    def _get_color_card_urls(self) -> Tuple[List[str], set]:
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
    
    def get_main_images(self) -> List[str]:
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
                    
                    # 方法1: 查找 od-gallery-turn-item-wrapper 结构
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
                    
                    # 方法2: 查找 ant-image 结构 (新版HTML结构)
                    if not main_area_all_urls:
                        ant_images = element.find_all('img', class_=lambda x: x and 'ant-image-img' in x.split() if x else False)
                        for img in ant_images:
                            if 'video-icon' in img.get('class', []):
                                continue
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
        
        # 统计主图区中有多少张图片在色卡区
        main_area_color_card_count = 0
        for main_url in main_area_all_urls:
            main_id = self._extract_image_id(main_url)
            if main_id and main_id in color_card_ids:
                main_area_color_card_count += 1
        
        # 主图数量 = 主图区总数 - 主图区中色卡图片数
        # 但要确保至少取5张（如果主图区有5张的话）
        if len(main_area_all_urls) == 5:
            # 主图区刚好5张，直接返回
            result = main_area_all_urls[:5]
            if self.webp_support:
                return [self._apply_webp_format(url) for url in result]
            return result
            return [self._apply_webp_format(url) for url in result] if self.webp_support else result
        
        # 计算非色卡图片数量
        non_color_card_count = len(main_area_all_urls) - main_area_color_card_count
        
        if non_color_card_count >= 5:
            # 非色卡图片足够5张，直接取前5张非色卡图片
            main_images = []
            for url in main_area_all_urls:
                img_id = self._extract_image_id(url)
                if img_id and img_id not in color_card_ids:
                    main_images.append(url)
                    if len(main_images) >= 5:
                        break
            return [self._apply_webp_format(url) for url in main_images] if self.webp_support else main_images
        
        # 非色卡图片不足5张，先取非色卡图片，再补充色卡图片
        main_images = []
        added_urls = set()
        
        # 先取非色卡图片
        for url in main_area_all_urls:
            img_id = self._extract_image_id(url)
            if img_id and img_id not in color_card_ids:
                if url not in added_urls:
                    main_images.append(url)
                    added_urls.add(url)
        
        # 再补充色卡图片凑够5张
        if len(main_images) < 5:
            for url in main_area_all_urls:
                img_id = self._extract_image_id(url)
                if img_id and img_id in color_card_ids:
                    if url not in added_urls:
                        main_images.append(url)
                        added_urls.add(url)
                        if len(main_images) >= 5:
                            break
        
        return [self._apply_webp_format(url) for url in main_images] if self.webp_support else main_images
    
    def get_color_options(self) -> List[Tuple[str, Optional[str]]]:
        """获取颜色选项"""
        color_options = []
        
        def sanitize_color_name(name: str) -> str:
            """清理色卡名称中的不安全字符"""
            if not name:
                return name
            # 替换文件名中的不安全字符
            unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
            result = name
            for char in unsafe_chars:
                result = result.replace(char, '-')
            return result
        
        sku_filter_buttons = self.soup.find_all('button', class_=lambda x: x and 'sku-filter-button' in x.split())
        if sku_filter_buttons:
            for button in sku_filter_buttons:
                label_name = button.find('span', class_=lambda x: x and 'label-name' in x.split() if x else False)
                if label_name:
                    color_name = sanitize_color_name(label_name.get_text().strip())
                    
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
                    color_name = sanitize_color_name(label_name.get_text().strip())
                elif item_label:
                    color_name = sanitize_color_name(item_label.get('title') or item_label.get_text().strip())
                
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
                    color_name = sanitize_color_name(prop_name.get_text().strip())
                    color_options.append((color_name, None))
        
        return color_options
    
    def get_detail_images(self) -> List[str]:
        """获取详情图链接
        
        从 HTML 标签提取，
        排除 imgextra 域名的图片（UI图标等无效图片）
        排除重复URL
        排除 _sum.jpg 后缀的缩略图
        排除 .webp 后缀（主图）
        排除父元素class包含 ant-image/v-image-wrap/label-image-wrap 的图片（主图/色卡图）
        排除评论区用户头像（!!0-0-cib.jpg 后缀）
        排除缩略图（_88x88q90 等后缀）
        """
        detail_images = []
        
        seen_urls = set()
        
        detail_div = self.soup.find('div', id='detail')
        if detail_div:
            img_tags = detail_div.find_all('img')
            for img in img_tags:
                usemap = img.get('usemap', '')
                if usemap and usemap.startswith('#_sdmap'):
                    src = img.get('src', '')
                    if src and src.startswith('http'):
                        if src not in seen_urls:
                            seen_urls.add(src)
                            detail_images.append(src)
        
        sf_imgs = self.soup.find_all('img', attrs={'data-sf-original-src': True})
        for img in sf_imgs:
            url = img.get('data-sf-original-src', '')
            if url and 'alicdn.com' in url:
                if 'imgextra' in url:
                    continue
                
                if '_sum.jpg' in url:
                    continue
                
                if '.webp' in url:
                    continue
                
                if '!!0-0-cib' in url:
                    continue
                
                if any(suffix in url for suffix in ['_88x88q90', '_120x120', '_60x60', '_100x100']):
                    continue
                
                parent = img.parent
                if parent:
                    parent_class = parent.get('class', [])
                    if isinstance(parent_class, list):
                        parent_class_str = ' '.join(parent_class)
                        if 'ant-image' in parent_class_str or 'v-image-wrap' in parent_class_str or 'label-image-wrap' in parent_class_str:
                            continue
                
                if url in seen_urls:
                    continue
                
                if '/img/ibank/' in url:
                    seen_urls.add(url)
                    detail_images.append(url)
        
        detail_images = [url for url in detail_images if url and 'lazyload.png' not in url and len(url) > 50]
        
        if self.webp_support:
            detail_images = [self._apply_webp_format(url) for url in detail_images]
        
        return detail_images
    
    def _extract_detail_images_from_context(self) -> Optional[List[str]]:
        """从 window.context 提取详情图
        
        Returns:
            详情图URL列表，如果提取失败返回None
        """
        try:
            html_content = str(self.soup)
            
            start_marker = 'window.context=(function(b,d){'
            end_marker = '})(window.contextPath,'
            
            start_idx = html_content.find(start_marker)
            if start_idx == -1:
                return None
            
            json_start = html_content.find(end_marker, start_idx)
            if json_start == -1:
                return None
            
            json_start += len(end_marker)
            
            brace_count = 0
            json_end = json_start
            
            for i in range(json_start, len(html_content)):
                char = html_content[i]
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
            
            json_str = html_content[json_start:json_end]
            
            try:
                import json
                data = json.loads(json_str)
            except json.JSONDecodeError:
                try:
                    import demjson3
                    data = demjson3.decode(json_str)
                except ImportError:
                    return None
            
            gallery = data.get('result', {}).get('data', {}).get('gallery', {}).get('fields', {})
            offer_img_list = gallery.get('offerImgList', [])
            
            if offer_img_list:
                return offer_img_list
            
            return None
            
        except Exception as e:
            return None
    
    def get_videos(self) -> List[str]:
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
    
    def get_attributes(self) -> List[Tuple[str, str]]:
        """获取商品属性"""
        attributes = []
        
        # 1. 优先处理用户提供的新表格结构
        # 查找包含商品属性的容器
        collapse_body = self.soup.select_one('div.antd-external-collapse.collapse-body')
        if collapse_body:
            # 使用更精确的方法提取属性
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
    
    def get_price(self) -> Optional[Dict]:
        """获取价格信息"""
        from utils.price_extractor import PriceExtractor
        
        extractor = PriceExtractor(self.html_content)
        return extractor.extract_all_prices()
    
    def get_sku_matrix(self) -> List[Dict]:
        """提取SKU矩阵数据（新版页面格式）
        
        从 skuInfoMapOriginal JSON数据中提取：
        - specAttrs: SKU名称（如：酒红色>均码M80-125）
        - price: 售价
        - discountPrice: 折扣价
        - canBookCount: 库存
        - skuId: SKU ID
        """
        sku_list = []
        
        # 方法1: 从JavaScript数据中提取skuInfoMapOriginal
        sku_pattern = r'"skuInfoMapOriginal"\s*:\s*(\{[^}]+\})'
        match = re.search(sku_pattern, self.html_content)
        
        if match:
            try:
                import json
                sku_json_str = match.group(1)
                # 处理JSON字符串
                sku_data = json.loads(sku_json_str)
                
                for spec_id, sku_info in sku_data.items():
                    sku_item = {
                        'sku_name': sku_info.get('specAttrs', ''),
                        'sku_id': str(sku_info.get('skuId', '')),
                        'price': float(sku_info.get('price', 0)),
                        'original_price': float(sku_info.get('discountPrice', 0)),
                        'stock': int(sku_info.get('canBookCount', 0))
                    }
                    sku_list.append(sku_item)
                
                return sku_list
            except (json.JSONDecodeError, ValueError) as e:
                pass
        
        # 方法2: 从全局变量中提取
        global_pattern = r'window\.__INIT_DATA__\s*=\s*({[^;]+});'
        match = re.search(global_pattern, self.html_content)
        
        if match:
            try:
                import json
                global_data = json.loads(match.group(1))
                
                # 尝试从不同路径获取SKU数据
                paths = [
                    ['globalData', 'offerBaseInfo', 'skuInfoMapOriginal'],
                    ['offerBaseInfo', 'skuInfoMapOriginal'],
                    ['skuInfoMapOriginal']
                ]
                
                for path in paths:
                    data = global_data
                    for key in path:
                        if isinstance(data, dict) and key in data:
                            data = data[key]
                        else:
                            data = None
                            break
                    
                    if data and isinstance(data, dict):
                        for spec_id, sku_info in data.items():
                            sku_item = {
                                'sku_name': sku_info.get('specAttrs', ''),
                                'sku_id': str(sku_info.get('skuId', '')),
                                'price': float(sku_info.get('price', 0)),
                                'original_price': float(sku_info.get('discountPrice', 0)),
                                'stock': int(sku_info.get('canBookCount', 0))
                            }
                            sku_list.append(sku_item)
                        
                        if sku_list:
                            return sku_list
            except (json.JSONDecodeError, ValueError):
                pass
        
        return sku_list
    
    def get_title(self) -> Optional[str]:
        """获取商品标题"""
        selectors = [
            'div.title-content h1',
            'div.module-od-title h1',
            'h1.title-text',
            'div.title-text h1',
            'div.mod-detail-title h1',
            'h1[class*="title"]',
            'span[class*="title-text"]'
        ]
        
        for selector in selectors:
            elem = self.soup.select_one(selector)
            if elem:
                title = elem.get_text().strip()
                if title:
                    return title
        
        title_elem = self.soup.find('title')
        if title_elem:
            title_text = title_elem.get_text().strip()
            if ' - ' in title_text:
                title_text = title_text.split(' - ')[0]
            if title_text and '阿里巴巴' not in title_text:
                return title_text
        
        title_match = re.search(r'"subject"\s*:\s*"([^"]+)"', self.html_content)
        if title_match:
            return title_match.group(1)
        
        return None
    
    def get_description(self) -> Optional[str]:
        """获取商品描述/卖点"""
        desc_selectors = [
            'div.desc-content',
            'div[class*="description"]',
            'div[class*="selling-point"]'
        ]
        
        for selector in desc_selectors:
            elem = self.soup.select_one(selector)
            if elem:
                text = elem.get_text().strip()
                if text and len(text) > 10:
                    return text[:500]
        
        return None
    
    def get_product_url(self) -> Optional[str]:
        """获取商品原始链接"""
        canonical = self.soup.find('link', rel='canonical')
        if canonical and canonical.get('href'):
            return canonical['href']
        
        og_url = self.soup.find('meta', property='og:url')
        if og_url and og_url.get('content'):
            return og_url['content']
        
        url_match = re.search(r'"offerUrl"\s*:\s*"([^"]+)"', self.html_content)
        if url_match:
            return url_match.group(1)
        
        return None
    
    def get_product_code(self) -> Optional[str]:
        """获取商品编码"""
        code_match = re.search(r'"货号"\s*[:：]\s*["\']?([^"\'<>\s,]+)', self.html_content)
        if code_match:
            return code_match.group(1)
        
        for text in ['货号', '商品编码']:
            elem = self.soup.find(string=re.compile(text))
            if elem:
                parent = elem.parent
                if parent:
                    next_elem = parent.find_next_sibling('span')
                    if next_elem:
                        return next_elem.get_text().strip()
                    next_elem = parent.find_next('span')
                    if next_elem:
                        return next_elem.get_text().strip()
        
        return None
    
    def get_shop_info(self) -> Optional[Dict]:
        """获取店铺信息"""
        shop_info = {}
        
        shop_link = self.soup.select_one('a[class*="shop-name"]')
        if not shop_link:
            shop_link = self.soup.select_one('a[href*="shop"]')
        
        if shop_link:
            shop_info['shop_name'] = shop_link.get_text().strip()
            shop_info['shop_url'] = shop_link.get('href', '')
            
            shop_id_match = re.search(r'shop/(\w+)', shop_info['shop_url'])
            if shop_id_match:
                shop_info['shop_id'] = shop_id_match.group(1)
        
        if not shop_info.get('shop_id'):
            shop_id_match = re.search(r'"shopId"\s*:\s*"?(\d+)"?', self.html_content)
            if shop_id_match:
                shop_info['shop_id'] = shop_id_match.group(1)
        
        rating_elem = self.soup.select_one('span[class*="rating"]')
        if rating_elem:
            rating_text = rating_elem.get_text().strip()
            rating_match = re.search(r'[\d.]+', rating_text)
            if rating_match:
                shop_info['shop_rating'] = float(rating_match.group())
        
        return shop_info if shop_info else None
    
    def get_ship_from(self) -> Optional[str]:
        """获取发货地"""
        ship_match = re.search(r'"sendGoodsAddress"\s*:\s*"([^"]+)"', self.html_content)
        if ship_match:
            return ship_match.group(1)
        
        location_elem = self.soup.select_one('span.location')
        if location_elem:
            return location_elem.get_text().strip()
        
        for text in ['发货地', '发货地址']:
            elem = self.soup.find(string=re.compile(text))
            if elem:
                parent = elem.parent
                if parent:
                    parent_text = parent.get_text()
                    match = re.search(r'发货[地地][：:]\s*([^\s<]+)', parent_text)
                    if match:
                        return match.group(1)
        
        return None
    
    def get_sales_count(self) -> int:
        """获取销量"""
        for selector in ['span[class*="sales"]', 'span[class*="sold"]', 'span.offer-sales']:
            try:
                elem = self.soup.select_one(selector)
                if elem:
                    text = elem.get_text()
                    match = re.search(r'[\d.]+[万kK]?', text)
                    if match:
                        num_str = match.group()
                        if '万' in num_str:
                            return int(float(num_str.replace('万', '')) * 10000)
                        elif 'k' in num_str.lower():
                            return int(float(num_str.lower().replace('k', '')) * 1000)
                        else:
                            num = int(float(num_str))
                            if num > 1000000:
                                continue
                            return num
            except:
                pass
        
        elem = self.soup.find(string=re.compile('成交'))
        if elem:
            parent = elem.parent
            if parent:
                text = parent.get_text()
                if '1688' in text and '成交' not in text[:10]:
                    return 0
                match = re.search(r'[\d.]+[万kK]?', text)
                if match:
                    num_str = match.group()
                    if '万' in num_str:
                        return int(float(num_str.replace('万', '')) * 10000)
                    elif 'k' in num_str.lower():
                        return int(float(num_str.lower().replace('k', '')) * 1000)
                    else:
                        num = int(float(num_str))
                        if num <= 1000000:
                            return num
        
        return 0
    
    def get_min_order(self) -> int:
        """获取起批量"""
        try:
            elem = self.soup.select_one('span[class*="min-order"]')
            if elem:
                text = elem.get_text()
                match = re.search(r'(\d+)', text)
                if match:
                    return int(match.group(1))
        except:
            pass
        
        for text in ['起批', '件起']:
            elem = self.soup.find(string=re.compile(text))
            if elem:
                parent = elem.parent
                if parent:
                    parent_text = parent.get_text()
                    match = re.search(r'(\d+)', parent_text)
                    if match:
                        return int(match.group(1))
        
        price_info = self.get_price()
        if price_info and price_info.get('main_price'):
            min_amount = price_info['main_price'].get('min_amount')
            if min_amount:
                return min_amount
        
        return 1
    
    def get_plugin_data(self) -> Dict:
        """获取1688采购助手插件数据
        
        Returns:
            包含类目、上架时间、成交数据等的字典
        """
        data = {}
        
        try:
            html_str = str(self.soup)
            
            # 使用正则表达式提取数据
            patterns = {
                'category': r'类目<span class=goods-operation-items>([^<]+)',
                'category_path': r'goods-operation-tooltip>([^<]+)</div></span>',
                'listing_date': r'上架时间<span>([^<]+)</span>',
                'monthly_sales': r'月成交<span>([^<]+)</span>',
                'monthly_dropship': r'月代销<span>([^<]+)</span>',
                'yearly_sales_pieces': r'年成交件数<span>([^<]+)</span>',
                'yearly_sales_orders': r'年成交笔数<span>([^<]+)</span>',
                'review_count': r'评论数<span>([^<]+)</span>',
                'positive_rate': r'好评率<span>([^<]+)</span>',
                'pickup_rate': r'揽收率<span>([^<]+)</span>',
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, html_str)
                if match:
                    data[key] = match.group(1).strip()
        
        except Exception as e:
            pass
        
        return data
    
    def get_aoxia_data(self) -> Dict:
        """获取遨虾数据（需要登录后才能看到）
        
        Returns:
            包含近4周采购量、功能亮点等的字典
        """
        data = {}
        
        try:
            sales_label = self.soup.find('span', class_='alphashop-pkg-od-banner-salesLabel')
            if sales_label and '近4周采购量' in sales_label.get_text():
                value_span = sales_label.find_next_sibling('span', class_='alphashop-pkg-od-banner-salesValue')
                if value_span:
                    data['four_week_purchases'] = value_span.get_text(strip=True)
            
            feature_title = self.soup.find('span', class_='alphashop-pkg-od-banner-featureTitle')
            if feature_title and '供应商亮点' in feature_title.get_text():
                tags = self.soup.find_all('span', class_='alphashop-pkg-od-banner-tagText')
                if tags:
                    data['supplier_highlights'] = [tag.get_text(strip=True) for tag in tags]
            
            feature_cards = self.soup.find_all('div', class_='alphashop-pkg-od-banner-featureCard')
            for card in feature_cards:
                title_elem = card.find('span', class_='alphashop-pkg-od-banner-featureTitle')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    
                    if '功能亮点' in title:
                        tags = card.find_all('span', class_='alphashop-pkg-od-banner-tagText')
                        if tags:
                            data['feature_highlights'] = [tag.get_text(strip=True) for tag in tags]
        
        except Exception as e:
            pass
        
        return data
    
    def get_trend_data(self) -> Dict:
        """获取商品成交趋势数据
        
        Returns:
            包含年销量、近30天销量、代发订单数、复购率、揽收率等的字典
        """
        data = {}
        
        try:
            sale_items = self.soup.find_all('div', class_='sale-item')
            for item in sale_items:
                cont = item.find('span', class_='cont')
                title = item.find('span', class_='title')
                
                if cont and title:
                    value = cont.get_text(strip=True)
                    title_text = title.get_text(strip=True)
                    
                    if '年销量' in title_text:
                        data['yearly_sales'] = value
                    elif '近30天销量' in title_text:
                        data['last_30_days_sales'] = value
                    elif '30天代发订单数' in title_text:
                        data['last_30_days_dropship'] = value
                    elif '复购率' in title_text:
                        data['repurchase_rate'] = value
                    elif '48小时揽收率' in title_text:
                        data['pickup_rate_48h'] = value
            
            update_time = self.soup.find('div', class_='update-time')
            if update_time:
                spans = update_time.find_all('span')
                for span in spans:
                    text = span.get_text(strip=True)
                    if '最早上架时间' in text:
                        match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
                        if match:
                            data['first_listing_date'] = match.group(1)
                    elif '最新发布时间' in text:
                        match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
                        if match:
                            data['latest_publish_date'] = match.group(1)
        
        except Exception as e:
            pass
        
        return data
