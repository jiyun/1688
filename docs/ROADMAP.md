# 项目路线图

## 当前版本: v0.4.4

在线采集增强、代码清理优化。

---

## v0.5.0 规划 - 数据看板

### 目标

建立综合数据看板，实现数据可视化展示与分析。

### GUI框架迁移规划

#### 背景

CustomTkinter 在 Python 3.12+ 存在兼容性问题，需要评估替代方案。

#### 替代方案对比

| 框架 | 兼容性 | 美观度 | 学习成本 | 体积 | 与看板契合度 |
|------|--------|--------|----------|------|--------------|
| ttkbootstrap | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 小 | ⭐⭐⭐ |
| PySide6 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ~50MB | ⭐⭐⭐ |
| **Flet** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ~25MB | ⭐⭐⭐⭐⭐ |

#### 推荐方案：Flet

**核心优势：一套代码，桌面+Web 双端运行**

```
┌─────────────────────────────────────────┐
│              Flet 应用代码               │
├─────────────────────────────────────────┤
│     ┌───────────┐    ┌───────────┐      │
│     │  桌面应用  │    │  Web应用   │      │
│     │ (Flutter) │    │ (FastAPI) │      │
│     └───────────┘    └───────────┘      │
│            ↓              ↓              │
│     ┌─────────────────────────┐         │
│     │      同一套 UI 代码      │         │
│     └─────────────────────────┘         │
└─────────────────────────────────────────┘
```

**Flet 特点：**
- Flutter 渲染，界面现代美观
- Python 原生，无需学习 Dart
- 内置热重载，开发效率高
- 桌面/Web 切换只需改一行代码
- 代码复用率高达 80%+

**示例代码：**
```python
import flet as ft

def main(page: ft.Page):
    page.title = "1688采集工具"
    
    def on_collect(e):
        status.value = "采集中..."
        page.update()
    
    btn = ft.ElevatedButton(
        "开始采集",
        icon=ft.icons.PLAY_ARROW,
        on_click=on_collect,
        style=ft.ButtonStyle(bgcolor=ft.colors.GREEN, color=ft.colors.WHITE)
    )
    
    page.add(btn)

# 桌面运行
ft.app(target=main)

# Web运行（只需改一行）
# ft.app(target=main, view=ft.WEB_BROWSER)
```

#### 迁移评估

| 当前组件 | Flet 对应 |
|----------|-----------|
| CTkButton | ft.ElevatedButton / ft.FilledButton |
| CTkLabel | ft.Text |
| CTkFrame | ft.Container / ft.Card |
| CTkEntry | ft.TextField |
| CTkTextbox | ft.TextField(multiline=True) |
| CTkComboBox | ft.Dropdown |
| CTkTabview | ft.Tabs |
| CTkProgressBar | ft.ProgressBar |

**预计改动量：** 400-600 行代码

#### 迁移路线

```
v0.4.x (当前)
    │
    ├── ctk 兼容性问题出现
    │
v0.5.0
    │
    ├── 评估 Flet demo 分支
    ├── 核心功能迁移
    ├── 桌面端完整功能
    │
v0.6.0
    │
    ├── Web 端数据看板
    ├── 远程监控功能
    └── 代码复用 80%+
```

### 技术方案对比

| 方案 | 技术栈 | 优点 | 缺点 | 适用场景 |
|------|--------|------|------|----------|
| **方案A: Web Dashboard** | Flask/FastAPI + Vue/React | 跨平台、界面美观、可远程访问 | 需要启动服务 | 多人协作、远程查看 |
| **方案B: 桌面应用增强** | Tkinter/PyQt + Matplotlib | 无需额外依赖、集成现有GUI | 界面相对简单 | 个人使用 |
| **方案C: Streamlit** | Python Streamlit | 开发极快、代码量少 | 自定义受限 | 快速原型、数据分析 |
| **方案D: Jupyter Notebook** | Jupyter + Plotly | 交互式分析、灵活 | 需要技术背景 | 深度数据分析 |
| **方案E: Electron 桌面应用** | Electron + ECharts | 界面精美、交互丰富 | 打包体积大 | 专业级产品 |

### 推荐方案

#### 首选：Streamlit（快速实现）

```python
# 示例代码 - 极简实现
import streamlit as st
import duckdb
import plotly.express as px

st.set_page_config(page_title="商品数据看板", layout="wide")

# 连接数据库
conn = duckdb.connect('products.duckdb')

# 统计卡片
col1, col2, col3, col4 = st.columns(4)
col1.metric("商品总数", conn.execute("SELECT COUNT(*) FROM products").fetchone()[0])
col2.metric("供应商数", conn.execute("SELECT COUNT(*) FROM shops").fetchone()[0])
col3.metric("资源总数", conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0])
col4.metric("下载完成", conn.execute("SELECT COUNT(*) FROM resources WHERE downloaded").fetchone()[0])

# 图表
df = conn.execute("SELECT platform, COUNT(*) as count FROM products GROUP BY platform").df()
fig = px.pie(df, values='count', names='platform', title='平台分布')
st.plotly_chart(fig)
```

**优点**：
- 10分钟搭建完成
- 自动响应式布局
- 内置图表组件
- 支持筛选、搜索

#### 进阶：Flask + Vue（专业级）

```
项目结构:
dashboard/
├── app.py              # Flask 后端
├── api/
│   ├── products.py     # 商品 API
│   ├── shops.py        # 店铺 API
│   └── stats.py        # 统计 API
├── frontend/           # Vue 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── Dashboard.vue    # 总览页
│   │   │   ├── Products.vue     # 商品列表
│   │   │   └── Shops.vue        # 供应商分析
│   │   └── components/
│   │       ├── StatsCard.vue    # 统计卡片
│   │       └── Charts.vue       # 图表组件
```

**优点**：
- 界面精美、交互丰富
- 可扩展性强
- 支持多人协作

### 看板功能模块

```
┌─────────────────────────────────────────────────────────────┐
│                    商品数据看板                              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ 商品总数 │  │ 供应商数 │  │ 资源总数 │  │ 下载完成 │        │
│  │  1,234  │  │   56    │  │ 12,345  │  │  98.5%  │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │    平台分布饼图       │  │    发货地分布图       │        │
│  │   [1688: 80%]        │  │   [广州: 30%]        │        │
│  │   [JD: 20%]          │  │   [义乌: 25%]        │        │
│  └──────────────────────┘  └──────────────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   商品列表（可搜索/筛选）              │   │
│  │  标题 | 平台 | 供应商 | 价格 | 资源数 | 操作          │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  春夏T恤 | 1688 | XX服饰 | ¥25 | 12张 | [详情]       │   │
│  │  休闲裤 | 1688 | YY纺织 | ¥35 | 8张 | [详情]        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 图表类型推荐

| 数据类型 | 推荐图表 | 用途 |
|----------|----------|------|
| 平台分布 | 饼图/环形图 | 了解商品来源 |
| 发货地分布 | 地图/柱状图 | 供应链地理分析 |
| 价格分布 | 直方图/箱线图 | 价格区间分析 |
| 供应商评分 | 雷达图 | 供应商综合评估 |
| 时间趋势 | 折线图 | 采集趋势分析 |
| 商品列表 | 数据表格 | 详细数据查看 |

### 依赖安装

```bash
pip install streamlit plotly pandas
```

### 启动命令

```bash
streamlit run dashboard.py
```

---

## v0.4.x 当前重点 - 数据挖掘

### 已完成

- [x] 扩展数据库表结构（商品标题、描述、店铺信息等）
- [x] 新增 shops 表（供应商信息）
- [x] 增强 AlibabaParser 解析器
  - [x] get_title() - 商品标题
  - [x] get_description() - 商品描述
  - [x] get_product_url() - 商品链接
  - [x] get_product_code() - 商品编码
  - [x] get_shop_info() - 店铺信息
  - [x] get_ship_from() - 发货地
  - [x] get_sales_count() - 销量
  - [x] get_min_order() - 起批量
  - [x] get_all_info() - 获取所有信息
- [x] 新增数据库方法
  - [x] save_shop() - 保存店铺信息
  - [x] get_shop() - 获取店铺
  - [x] get_all_shops() - 获取所有店铺
  - [x] get_products_by_shop() - 按店铺获取商品
  - [x] update_product_info() - 更新商品详情
  - [x] get_statistics() - 获取统计数据
  - [x] search_products_full() - 综合搜索
- [x] 更新导入流程，调用新的解析方法
- [x] 更新 GUI 展示新增字段（店铺、发货地）

### 待完成

- [x] 测试新解析器的准确性
- [x] 优化选择器适配不同页面结构

### v0.4.2 新增

- [x] 数据库架构重构（product_extended、sku_prices表）
- [x] 数据库视图（v_product_full、v_resource_stats、v_price_stats）
- [x] 高级筛选功能（平台/发货地/状态）
- [x] 定价工具支持SKU价格矩阵
- [x] 数据库迁移脚本

---

## 历史版本

### v0.4.4 (2026-04-09)

- 新增"登陆平台"按钮
- 在线采集弹窗显示耗时
- 移除 raw.json/debug.html 文件保存
- 清理 __pycache__ 目录
- GUI框架迁移规划

### v0.4.3 (2026-04-08)

- 数据库页面重构（右键菜单、列排序）
- 价格矩阵选项卡
- 在线采集资源保存到数据库

### v0.4.2 (2026-03-29)

- 数据库架构重构
- SKU价格矩阵支持
- 高级筛选功能
- 定价工具优化

### v0.4.0 (2026-03-24)

- DuckDB 数据库支持
- 价格提取模块
- GUI 界面优化

### v0.3.x

- 多平台支持（1688、JD）
- 图片处理功能
- 批量下载

### v0.2.x

- 基础 HTML 解析
- 资源下载
- 本地存储
