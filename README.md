# 1688
1688详情页单页图片采集，反爬虫本地计算，批量下载图片。

主程序采用 Python 版本3.11下测试通过
辅助工具：浏览器（Firefox edge等）安装扩展 [SingleFile](https://github.com/gildas-lormeau/SingleFile/releases) 下载使用 [Aria2c](https://github.com/aria2/aria2/releases)
运行环境：Win下
批处理程序：用于建立存放的页面的目录下载路径,并启动分析用的 Python 脚本

用法：
1. 使用安装好的 SingleFile 的浏览器，打开目标页面（例如：[https://detail.1688.com/offer/{*}.html]()) 点击浏览器上的SingleFile按钮保存。（SingleFile选项默认值保存的文件过大需要调整设置选项）
2. 弹出的保存文件窗口，建议用URL中{*}部分的数字命名保存的文件名。
3. 将保存的"数字.html"文件拖放到 start1688.bat上启动该批处理。

处理过程简要说明：
因阿里系页面都有非常强大的反爬虫机制，直接调用python、webdriver、web scraper等过于麻烦。换条思路，直接解析本地已经渲染的页面，断开反爬虫机制。奈我如何。

1688-1.py
> 用到BeautifulSoup splitext 请通过 pip 安装
> 调用os re requests subprocess
> 当通过 start1688.bat 调用此脚本后 会分析引用的 "数字.html" 
> 分析出三个部分内容 头图的图像链接 颜色选项卡文本 详情页内的图片链接
> 头图链接会进一步与头图文本进行拼合 放入 aria2c 用下载列表 （存放在对应的目录内down.txt文件）
> 详情页图片链接添加下载后重命名序列信息 放入 arai2c 用下载列表
> 分析完成后 调用外部命令 aria2c 下载上面所制作的内容 （为什么不用 python aria2p? 这货太慢或者说我不会调）
> 下载完成后会在对应目录内生成引用文件的原始URL地址的快捷方式 #URL.url文件
> 2023/09/18 添加了目标页面的视频下载 添加了目标页面的商品属性提取为单独文件

todo list：
给图片按用途分类存放 比如按 头图 SKU 正文等适应在其他平台上架使用。

还有什么使用建议欢迎留言，该项目编码由AI代劳本人仅仅监工。
注：代码由AI代劳人工测试通过。
>（此处声明感谢：文心一言 chatgpt替代品其一）
