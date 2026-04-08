# 1688详情页资源采集工具

![Version](https://img.shields.io/badge/version-0.4.3-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-orange)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

## 项目简介

这是一个用于采集1688详情页资源的工具，通过解析本地已渲染的页面来避开阿里的反爬虫机制，实现对商品图片、视频和属性的批量下载和管理。

## 版本信息 

- 当前版本：0.4.3
- 作者：急云
- 项目地址：https://github.com/jiyun/1688/
- 发布日期：2026-04-08
- [查看完整更新日志](CHANGELOG.md)

## 核心功能

- **资源采集**：提取商品头图、详情图、视频和属性信息
- **批量下载**：使用aria2c高效批量下载资源
- **自动分类**：按类型（主图、详情图、视频）自动分类保存文件
- **快捷操作**：支持将HTML文件拖放到批处理文件上启动处理
- **URL快捷方式**：自动生成包含原始商品链接的快捷方式
- **重建功能**：提供重建脚本，可重新下载和处理资源
- **图片处理**：支持详情图拼接和切割，自动处理宽高比
- **资源打包**：支持将资源打包为压缩文件，HTML文件放在根目录，其他文件放在子目录
- **数据挖掘**：自动提取商品标题、店铺信息、发货地、销量等数据
- **价格管理**：支持SKU价格提取、成本计算、阶梯价格生成
- **数据库管理**：使用DuckDB存储商品数据，支持搜索和筛选

## 系统要求

- **操作系统**：Windows
- **Python版本**：Python 3.11+
- **外部工具**：
  - [aria2c](https://github.com/aria2/aria2/releases)（用于批量下载）
- **浏览器扩展**：
  - [SingleFile](https://github.com/gildas-lormeau/SingleFile/releases)（用于保存完整HTML页面）
- **Python依赖库**：
  - BeautifulSoup4 (`pip install beautifulsoup4`)
  - requests (`pip install requests`)
  - Pillow (`pip install Pillow`)
  - duckdb (`pip install duckdb`)

- **可选依赖库**（用于增强GUI体验）：
  - tkinterweb (`pip install tkinterweb`)  # 用于Markdown渲染
  - markdown (`pip install markdown`)  # 用于Markdown解析
  - customtkinter (`pip install customtkinter`)  # 用于现代GUI界面

## 安装步骤

1. **安装Python**：从[Python官网](https://www.python.org/)下载并安装Python 3.11+
2. **安装依赖库**：打开命令提示符，运行以下命令：
   ```bash
   pip install beautifulsoup4 requests Pillow duckdb customtkinter
   ```
3. **下载aria2c**：从[aria2c官网](https://github.com/aria2/aria2/releases)下载最新版本，解压后将`aria2c.exe`文件复制到项目根目录
4. **安装SingleFile扩展**：在浏览器中安装SingleFile扩展
5. **下载项目**：将本项目下载到本地任意目录

## 使用方法

### 基本使用

1. **保存商品页面**：
   - 使用安装了SingleFile扩展的浏览器打开1688商品详情页（如：`https://detail.1688.com/offer/{商品ID}.html`）
   - 点击浏览器上的SingleFile按钮，保存完整HTML页面
   - 在SingleFile扩展配置中重点关注 
      - ![#c5f015](https://placehold.co/15x15/c5f015/c5f015.png) **配置-> HTML内容->保存嵌入资源的原始网址** 的复选框勾选
      - ![#c5f015](https://placehold.co/15x15/c5f015/c5f015.png) **配置->文件名->模板 填入{url-last-segment}.{filename-extension}**
   - 其他配置选项能不保存就不保存用不上

2. **启动处理**：
   - 将保存的HTML文件拖放到`start1688.bat`批处理文件上
   - 程序会自动创建以商品ID命名的目录，并开始处理

3. **查看结果**：
   - 处理完成后，在商品ID目录中会生成以下内容：
     - 存放主图
     - 存放色卡图
     - 存放详情图
     - 存放视频
     - `attributes/`：存放商品属性HTML文件
     - `#URL.url`：商品原始链接的快捷方式
     - `rebuild.bat`：重建脚本，可重新下载和处理资源

### 批量处理

- 对于多个商品页面，可逐个将HTML文件拖放到`start1688.bat`上进行处理。
- 或者直接启用 `BP1688html.bat` 批量将当前目录全部html提交给`start1688.bat`队列处理
- 支持 GUI 模式，运行 `python main.py --gui` 可打开图形化界面，在窗体中添加文件或目录添加到队列，点击执行处理资源采集。注部分功能受限比如资源重建。

### 重建资源

如果需要重新下载和处理资源，可：
1. 进入商品ID目录
2. 双击运行`rebuild.bat`脚本
3. 程序会删除现有文件并重新下载和处理

### 图片处理

如果需要拼接和切割详情图，可：
1. 进入商品ID目录
2. 运行`rebuild.bat`脚本并选择选项2 "详情图拼接"
3. 程序会自动处理图片，包括：
   - 收集目录中所有 `C_` 开头的图片文件
   - 按自然排序（如 C_1, C_2, C_11）排列图片
   - 移除宽度低于 750px 的图片
   - 判定数量最多的宽度作为主队列，移除其他宽度的图片
   - 按照主队列首张图片的宽度拼接图片
   - 按照宽高比小于 1:2 的比例切割图片
   - 如果最后一张切割图小于 200px，则平均分配切割高度
4. 处理完成后，会在当前目录生成：
   - `拼接结果.jpg`：所有图片拼接后的完整图片
   - `new_C_1.jpg`, `new_C_2.jpg` 等：切割后的图片（前缀可在 config.py 中配置）

### 资源打包

如果需要将资源打包为压缩文件，可：
1. 进入商品ID目录
2. 运行`rebuild.bat`脚本并选择选项4 "封包该资源"
3. 程序会自动打包资源，生成的压缩文件结构如下：
   - 根目录：包含 `{商品ID}.html` 文件
   - `{商品ID}/` 子目录：包含所有下载的资源文件（图片、视频、属性等）

## 项目结构

```
1688/
├── main.py             # 主脚本（支持命令行和GUI模式）
├── config.py           # 配置文件
├── start1688.bat       # 启动批处理文件
├── start-gui.bat       # GUI模式启动文件
├── bp1688html.bat      # 批处理HTML文件
├── gui/                # GUI模块
│   ├── __init__.py     # GUI包初始化
│   ├── app.py          # GUI应用主程序
│   ├── commands.py     # 上下文菜单命令
│   ├── logging.py      # 日志处理
│   ├── menu.py         # 菜单管理
│   ├── queue.py        # 队列管理
│   ├── utils.py        # GUI工具函数
│   ├── dnd.py          # 拖放功能
│   ├── pricing_gui.py  # 价格计算工具
│   └── tiered_price_generator.py # 阶梯价格生成器
├── utils/              # 工具模块
│   ├── parser.py       # HTML解析兼容层
│   ├── database.py     # DuckDB数据库模块
│   ├── shared_cache.py # 共享内存缓存
│   ├── downloader.py   # 下载管理工具
│   ├── file_handler.py # 文件处理工具
│   ├── tool_downloader.py # aria2c下载工具
│   ├── image_utils.py  # 图像处理基础工具
│   ├── image_processor.py # 图像处理流程
│   ├── price_extractor.py # 价格提取器
│   ├── resource_downloader.py # 资源下载器
│   ├── launcher.py     # 启动器
│   ├── logger.py       # 日志模块
│   ├── updater.py      # 版本检测升级模块
│   └── parsers/        # 平台解析器
│       ├── __init__.py
│       ├── base_parser.py   # 解析器基类
│       ├── alibaba_parser.py # 1688解析器
│       └── jd_parser.py     # 京东解析器
├── version.json        # 版本配置文件
├── ROADMAP.md          # 项目路线图
├── LICENSE             # 许可证文件
└── README.md           # 说明文档
```

### 模块说明

- **main.py**：主脚本，整合所有功能，处理完整流程，支持命令行模式和GUI模式（通过 `--gui` 参数启用）
- **config.py**：配置文件，包含下载参数、文件命名规则、图片处理配置、GUI配置和价格计算配置等
- **gui/app.py**：GUI应用主程序，创建主窗口和各个组件
- **gui/commands.py**：上下文菜单命令，执行图像优化、资源打包、重新采集等操作
- **gui/logging.py**：日志处理，显示处理进度和结果
- **gui/menu.py**：菜单管理，创建和管理上下文菜单
- **gui/queue.py**：队列管理，管理待处理文件列表
- **gui/utils.py**：GUI工具函数，提供辅助功能
- **gui/pricing_gui.py**：价格计算工具，基于成本数据自动计算商品价格
- **gui/tiered_price_generator.py**：阶梯价格生成器，支持统一倍率和统一利润率定价策略
- **utils/parser.py**：HTML解析工具，提取页面中的资源链接和属性
- **utils/downloader.py**：下载管理工具，生成下载列表，调用aria2c下载
- **utils/file_handler.py**：文件处理工具，创建目录，保存属性，生成快捷方式和批处理脚本
- **utils/tool_downloader.py**：aria2c下载工具，检查和下载aria2c工具
- **utils/image_utils.py**：图像处理基础工具，提供图片放大、切割、动图转换、文件收集、并行处理等功能
- **utils/image_processor.py**：图像处理流程模块，实现主图、详情图、色卡图、混合图片的完整处理流程
- **utils/database.py**：数据库模块，使用SQLite存储商品数据、价格信息
- **utils/price_extractor.py**：价格提取器，从HTML中提取SKU价格信息
- **utils/version.py**：版本信息模块，管理当前版本号和版本信息
- **utils/updater.py**：版本检测升级模块，支持自动检测更新、GitHub/Gitee双源切换、下载更新包

## 性能说明

- **处理速度**：单个商品页面处理约需 10-30 秒（取决于资源数量和网络状况）
- **资源占用**：内存占用约 50-100MB，CPU占用取决于并行线程数
- **网络要求**：需要稳定的网络连接下载资源
- **磁盘空间**：每个商品约占用 10-50MB（取决于图片和视频数量）
- **并行处理**：默认使用2线程并行处理图片，可在 config.py 中调整

## 安全性与隐私

- ✅ 本工具在本地运行，不上传任何数据到服务器
- ✅ 所有数据保存在本地，用户完全掌控
- ✅ 不包含任何追踪或统计代码
- ✅ 不收集用户个人信息
- ⚠️ 请勿用于商业用途，遵守相关法律法规
- ⚠️ 下载和使用他人商品图片时，请确保获得授权

## 常见问题

### 1. 为什么需要使用SingleFile保存页面？

- 1688页面采用动态加载技术，直接使用Python请求获取的HTML不包含完整的资源信息
- SingleFile扩展会保存页面的完整渲染结果，包括所有图片、视频和属性信息
- 解析本地已渲染的页面可以避开阿里的反爬虫机制

### 2. 为什么下载的文件大小为0？

- 可能是因为网络连接问题或资源链接失效
- 程序会自动删除小于5KB的文件，以过滤掉无效资源

### 3. 为什么某些图片没有被下载？

- 可能是因为图片链接格式不被支持
- 程序会过滤掉占位图（如`lazyload.png`）
- 请确保使用SingleFile保存的页面包含完整的资源信息

### 4. 如何处理批量商品？

- 可以逐个将HTML文件拖放到`start1688.bat`上进行处理
- 每个商品会创建独立的目录，不会互相干扰

### 5. 压缩包中的文件结构是怎样的？

- 压缩包根目录：包含 `{商品ID}.html` 文件
- `{商品ID}/` 子目录：包含所有下载的资源文件（图片、视频、属性等）

## 后续优化方向

1. **v0.5.0 数据看板**：Streamlit/Flask+Vue 数据可视化看板
2. **配置向导**：首次启动引导配置aria2c路径、输出目录等
3. **支持更多电商平台**：扩展支持淘宝、京东等电商平台HTML解析
4. **图片水印处理**：支持批量添加/去除水印
5. **导出报表功能**：支持Excel格式导出商品数据报表
6. **图片批量重命名**：自定义命名规则，批量重命名资源文件
7. **商品数据对比**：对比不同版本商品信息，追踪价格变化
8. **快捷键自定义**：支持用户自定义快捷键绑定
9. **数据备份恢复**：本地数据库备份与恢复功能

详见 [ROADMAP.md](ROADMAP.md)

## 注意事项

- 本工具仅用于个人学习和研究目的，请勿用于商业用途
- 请遵守相关法律法规，尊重他人知识产权
- 下载和使用他人商品图片时，请确保获得授权
- 本工具可能会随着1688页面结构的变化而需要更新

## 致谢

本项目的开发离不开以下开源项目：

- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) - HTML解析
- [aria2](https://github.com/aria2/aria2) - 高速下载工具
- [SingleFile](https://github.com/gildas-lormeau/SingleFile) - 页面保存扩展
- [Pillow](https://python-pillow.org/) - 图像处理库
- [DuckDB](https://duckdb.org/) - 嵌入式分析数据库
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - 现代GUI组件
- [pandas](https://pandas.pydata.org/) - 数据处理库
- [requests](https://docs.python-requests.org/) - HTTP请求库

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 联系方式

如有问题或建议，欢迎联系项目维护者。
