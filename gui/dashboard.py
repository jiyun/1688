import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import os

st.set_page_config(
    page_title="1688采集数据看板",
    page_icon="📊",
    layout="wide"
)

@st.cache_resource
def get_db_connection():
    db_path = 'products.duckdb'
    if not os.path.exists(db_path):
        return None
    return duckdb.connect(db_path, read_only=True)

conn = get_db_connection()

st.title("📊 1688采集数据看板")
st.caption(f"数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.markdown("---")

if conn is None:
    st.error("❌ 未找到数据库文件 `products.duckdb`，请确认文件存在")
    st.stop()

st.sidebar.header("🔍 筛选条件")

try:
    platforms = conn.execute(
        "SELECT DISTINCT platform FROM products WHERE platform IS NOT NULL"
    ).fetchdf()['platform'].tolist()
    selected_platforms = st.sidebar.multiselect("平台", platforms, default=platforms)
except:
    selected_platforms = []
    st.sidebar.info("暂无平台数据")

try:
    categories = conn.execute(
        "SELECT DISTINCT main_category FROM products WHERE main_category IS NOT NULL AND main_category != ''"
    ).fetchdf()['main_category'].tolist()
    selected_categories = st.sidebar.multiselect("类目", categories, default=categories)
except:
    selected_categories = []

date_range = st.sidebar.date_input(
    "采集日期范围",
    value=(datetime.now() - timedelta(days=30), datetime.now())
)

where_clauses = []
if selected_platforms:
    platforms_str = "', '".join(selected_platforms)
    where_clauses.append(f"platform IN ('{platforms_str}')")
if selected_categories:
    categories_str = "', '".join(selected_categories)
    where_clauses.append(f"main_category IN ('{categories_str}')")
if date_range and len(date_range) == 2:
    where_clauses.append(
        f"DATE(created_at) BETWEEN '{date_range[0]}' AND '{date_range[1]}'"
    )

where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

st.markdown("### 📈 核心指标")

col1, col2, col3, col4, col5, col6 = st.columns(6)

try:
    total_products = conn.execute(f"SELECT COUNT(*) FROM products WHERE {where_sql}").fetchone()[0]
    col1.metric("商品总数", f"{total_products:,}")
except:
    total_products = 0
    col1.metric("商品总数", "0")

try:
    total_shops = conn.execute(f"""
        SELECT COUNT(DISTINCT shop_id) FROM products 
        WHERE shop_id IS NOT NULL AND shop_id != '' AND {where_sql}
    """).fetchone()[0]
    col2.metric("供应商数", f"{total_shops:,}")
except:
    col2.metric("供应商数", "0")

try:
    total_resources = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    col3.metric("资源总数", f"{total_resources:,}")
except:
    total_resources = 0
    col3.metric("资源总数", "0")

try:
    downloaded = conn.execute("SELECT COUNT(*) FROM resources WHERE downloaded = TRUE").fetchone()[0]
    download_rate = downloaded / total_resources * 100 if total_resources > 0 else 0
    col4.metric("已下载", f"{downloaded:,}", f"{download_rate:.1f}%")
except:
    col4.metric("已下载", "0", "0%")

try:
    avg_price = conn.execute(f"""
        SELECT AVG(unit_price) FROM products 
        WHERE unit_price > 0 AND unit_price < 100000 AND {where_sql}
    """).fetchone()[0] or 0
    col5.metric("平均单价", f"¥{avg_price:.2f}")
except:
    col5.metric("平均单价", "¥0.00")

try:
    avg_sales = conn.execute(f"""
        SELECT AVG(sales_count) FROM products 
        WHERE sales_count > 0 AND {where_sql}
    """).fetchone()[0] or 0
    col6.metric("平均销量", f"{avg_sales:,.0f}")
except:
    col6.metric("平均销量", "0")

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📊 平台分析", "📦 库存分析", "🗺️ 地域分析", "📋 商品列表"])

with tab1:
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("平台分布")
        try:
            platform_data = conn.execute(f"""
                SELECT 
                    CASE 
                        WHEN platform IN ('alibaba', '1688') THEN '1688'
                        WHEN platform = 'jd' THEN '京东'
                        ELSE COALESCE(platform, '未知')
                    END as platform_name,
                    COUNT(*) as count
                FROM products
                WHERE {where_sql}
                GROUP BY platform_name
                ORDER BY count DESC
            """).df()
            
            if not platform_data.empty:
                fig = px.pie(platform_data, values='count', names='platform_name',
                           title='商品平台分布', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暂无平台分布数据")
        except Exception as e:
            st.error(f"加载平台分布失败: {e}")
    
    with col_right:
        st.subheader("价格分布")
        try:
            price_data = conn.execute(f"""
                SELECT unit_price FROM products 
                WHERE unit_price > 0 AND unit_price < 10000 AND {where_sql}
            """).df()
            
            if not price_data.empty:
                fig = px.histogram(price_data, x='unit_price', nbins=30,
                                  title='商品单价分布',
                                  labels={'unit_price': '价格(¥)', 'count': '商品数量'},
                                  color_discrete_sequence=['#3B8ED0'])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暂无价格分布数据")
        except Exception as e:
            st.error(f"加载价格分布失败: {e}")
    
    st.subheader("采集趋势（近30天）")
    try:
        trend_data = conn.execute(f"""
            SELECT DATE(created_at) as date, COUNT(*) as new_products
            FROM products
            WHERE created_at >= CURRENT_DATE - INTERVAL '30 days' AND {where_sql}
            GROUP BY DATE(created_at)
            ORDER BY date
        """).df()
        
        if not trend_data.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trend_data['date'], y=trend_data['new_products'],
                mode='lines+markers', fill='tozeroy', name='新增商品'
            ))
            fig.update_layout(title='每日采集量趋势', xaxis_title='日期', yaxis_title='新增商品数')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无采集趋势数据")
    except Exception as e:
        st.error(f"加载采集趋势失败: {e}")

with tab2:
    st.subheader("库存健康度分析")
    
    try:
        inventory_data = conn.execute("""
            SELECT 
                p.product_id, p.title, p.platform,
                COUNT(r.id) as resource_count,
                SUM(CASE WHEN r.downloaded THEN 1 ELSE 0 END) as downloaded_count,
                CASE 
                    WHEN COUNT(r.id) = 0 THEN '无资源'
                    WHEN SUM(CASE WHEN r.downloaded THEN 1 ELSE 0 END) = COUNT(r.id) 
                    THEN '已完成'
                    ELSE '下载中'
                END as status
            FROM products p
            LEFT JOIN resources r ON p.product_id = r.product_id
            GROUP BY p.product_id, p.title, p.platform
            ORDER BY resource_count DESC
            LIMIT 100
        """).df()
        
        if not inventory_data.empty:
            status_counts = inventory_data['status'].value_counts().reset_index()
            status_counts.columns = ['status', 'count']
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(status_counts, x='status', y='count',
                           title='商品状态分布', color='status')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.metric("已完成下载", len(inventory_data[inventory_data['status'] == '已完成']))
                st.metric("下载中", len(inventory_data[inventory_data['status'] == '下载中']))
                st.metric("无资源", len(inventory_data[inventory_data['status'] == '无资源']))
        else:
            st.info("暂无库存数据")
    except Exception as e:
        st.error(f"加载库存分析失败: {e}")

with tab3:
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("发货地分布")
        try:
            location_data = conn.execute(f"""
                SELECT ship_from, COUNT(*) as count
                FROM products
                WHERE ship_from IS NOT NULL AND ship_from != '' AND {where_sql}
                GROUP BY ship_from
                ORDER BY count DESC
                LIMIT 15
            """).df()
            
            if not location_data.empty:
                fig = px.bar(location_data, x='ship_from', y='count',
                           title='发货地分布 TOP15',
                           labels={'ship_from': '发货地', 'count': '商品数量'},
                           color_discrete_sequence=['#2ECC71'])
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暂无发货地数据")
        except Exception as e:
            st.error(f"加载发货地分布失败: {e}")
    
    with col_right:
        st.subheader("销量分布")
        try:
            sales_data = conn.execute(f"""
                SELECT sales_count FROM products 
                WHERE sales_count > 0 AND {where_sql}
            """).df()
            
            if not sales_data.empty:
                fig = px.histogram(sales_data, x='sales_count', nbins=30,
                                  title='商品销量分布',
                                  labels={'sales_count': '销量', 'count': '商品数量'},
                                  color_discrete_sequence=['#E74C3C'])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暂无销量数据")
        except Exception as e:
            st.error(f"加载销量分布失败: {e}")
    
    st.subheader("扩展数据概览")
    try:
        ext_stats = conn.execute(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN pe.category IS NOT NULL THEN 1 ELSE 0 END) as has_category,
                SUM(CASE WHEN pe.monthly_sales IS NOT NULL THEN 1 ELSE 0 END) as has_monthly_sales,
                SUM(CASE WHEN pe.positive_rate IS NOT NULL THEN 1 ELSE 0 END) as has_positive_rate,
                SUM(CASE WHEN pe.features IS NOT NULL THEN 1 ELSE 0 END) as has_features,
                SUM(CASE WHEN pe.supplier_highlights IS NOT NULL THEN 1 ELSE 0 END) as has_supplier,
                SUM(CASE WHEN pe.estimated_delivery IS NOT NULL THEN 1 ELSE 0 END) as has_delivery,
                AVG(pe.positive_rate) as avg_positive_rate,
                AVG(pe.shop_return_rate) as avg_return_rate,
                AVG(pe.shop_service_score) as avg_service_score
            FROM products p
            LEFT JOIN product_extended pe ON p.product_id = pe.product_id
            WHERE {where_sql}
        """).df()
        
        if not ext_stats.empty:
            row = ext_stats.iloc[0]
            ext_col1, ext_col2, ext_col3, ext_col4 = st.columns(4)
            ext_col1.metric("好评率", f"{row['avg_positive_rate']:.1f}%" if row['avg_positive_rate'] else "-")
            ext_col2.metric("回头率", f"{row['avg_return_rate']:.1f}%" if row['avg_return_rate'] else "-")
            ext_col3.metric("服务分", f"{row['avg_service_score']:.1f}" if row['avg_service_score'] else "-")
            ext_col4.metric("有扩展数据", f"{int(row['has_category'] or 0)}/{int(row['total'])}")
    except Exception as e:
        st.info(f"扩展数据暂不可用: {e}")

with tab4:
    st.subheader("商品列表")
    
    try:
        page_size = 50
        page = st.number_input("页码", min_value=1, value=1, step=1)
        offset = (page - 1) * page_size
        
        products_df = conn.execute(f"""
            SELECT 
                p.product_id,
                p.title,
                p.platform,
                p.main_category,
                p.unit_price,
                p.sales_count,
                p.min_order,
                p.ship_from,
                p.product_url,
                p.created_at
            FROM products p
            WHERE {where_sql}
            ORDER BY p.created_at DESC
            LIMIT {page_size} OFFSET {offset}
        """).df()
        
        if not products_df.empty:
            display_df = products_df.copy()
            if 'product_url' in display_df.columns:
                display_df['链接'] = display_df['product_url'].apply(
                    lambda x: f"[打开]({x})" if x and pd.notna(x) else ""
                )
            
            st.dataframe(
                display_df,
                column_config={
                    "product_id": "商品ID",
                    "title": st.column_config.TextColumn("商品标题", width="large"),
                    "platform": "平台",
                    "main_category": "类目",
                    "unit_price": st.column_config.NumberColumn("单价", format="¥%.2f"),
                    "sales_count": st.column_config.NumberColumn("销量", format="%d"),
                    "min_order": st.column_config.NumberColumn("起订量", format="%d"),
                    "ship_from": "发货地",
                    "product_url": None,
                    "链接": st.column_config.LinkColumn("链接"),
                    "created_at": "采集时间"
                },
                use_container_width=True,
                hide_index=True
            )
            
            if st.button("📥 导出当前筛选结果"):
                export_data = conn.execute(f"SELECT * FROM products WHERE {where_sql}").df()
                csv = export_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="下载CSV",
                    data=csv,
                    file_name=f"products_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("暂无商品数据")
    except Exception as e:
        st.error(f"加载商品列表失败: {e}")

st.markdown("---")
st.caption("1688详情页资源采集工具 © 2025")
