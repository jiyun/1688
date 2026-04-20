# -*- coding: utf-8 -*-
"""
商品成交趋势数据看板
展示销售统计、趋势图表等数据
"""

import customtkinter as ctk
from typing import Dict, Any, Optional


class TrendDashboard(ctk.CTkFrame):
    """商品成交趋势数据看板"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.data: Optional[Dict[str, Any]] = None
        self._create_widgets()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 标题
        self.title_label = ctk.CTkLabel(
            self,
            text="商品成交趋势",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.title_label.pack(pady=(10, 15))
        
        # 销售统计卡片区域
        self.stats_frame = ctk.CTkFrame(self)
        self.stats_frame.pack(fill="x", padx=10, pady=5)
        
        self.stats_cards: Dict[str, ctk.CTkFrame] = {}
        stats_config = [
            ('yearly_sales', '年销量', '件'),
            ('monthly_sales_30d', '近30天销量', '件'),
            ('dropship_orders_30d', '30天代发订单', '单'),
            ('repurchase_rate', '复购率', '%'),
            ('pickup_rate_48h', '48小时揽收率', '%'),
        ]
        
        for i, (key, label, unit) in enumerate(stats_config):
            card = self._create_stat_card(self.stats_frame, label, unit)
            card.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            self.stats_cards[key] = card
        
        # 配置网格权重
        for i in range(len(stats_config)):
            self.stats_frame.grid_columnconfigure(i, weight=1)
        
        # 上架信息区域
        self.info_frame = ctk.CTkFrame(self)
        self.info_frame.pack(fill="x", padx=10, pady=5)
        
        self.first_listing_label = ctk.CTkLabel(
            self.info_frame,
            text="最早上架时间: --",
            font=ctk.CTkFont(size=11)
        )
        self.first_listing_label.pack(side="left", padx=10, pady=5)
        
        self.last_publish_label = ctk.CTkLabel(
            self.info_frame,
            text="最新发布时间: --",
            font=ctk.CTkFont(size=11)
        )
        self.last_publish_label.pack(side="right", padx=10, pady=5)
        
        # 趋势图表区域（预留）
        self.chart_frame = ctk.CTkFrame(self)
        self.chart_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.chart_label = ctk.CTkLabel(
            self.chart_frame,
            text="趋势图表区域\n（需要接入图表库如 matplotlib 或 pygal）",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.chart_label.pack(expand=True)
    
    def _create_stat_card(self, parent, label: str, unit: str) -> ctk.CTkFrame:
        """创建统计卡片"""
        card = ctk.CTkFrame(parent)
        
        # 数值标签
        value_label = ctk.CTkLabel(
            card,
            text="--",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        value_label.pack(pady=(10, 0))
        
        # 标题标签
        title_label = ctk.CTkLabel(
            card,
            text=label,
            font=ctk.CTkFont(size=11)
        )
        title_label.pack()
        
        # 单位标签
        unit_label = ctk.CTkLabel(
            card,
            text=unit,
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        unit_label.pack(pady=(0, 10))
        
        # 保存引用以便更新
        card.value_label = value_label
        card.unit_label = unit_label
        
        return card
    
    def update_data(self, trend_data: Dict[str, Any]):
        """更新看板数据"""
        self.data = trend_data
        
        if not trend_data:
            self._clear_display()
            return
        
        # 更新销售统计
        sales_stats = trend_data.get('sales_stats', {})
        for key, card in self.stats_cards.items():
            value = sales_stats.get(key)
            if value is not None:
                if isinstance(value, float):
                    card.value_label.configure(text=f"{value:.1f}")
                else:
                    card.value_label.configure(text=f"{value:,}")
            else:
                card.value_label.configure(text="--")
        
        # 更新上架信息
        listing_info = trend_data.get('listing_info', {})
        first_date = listing_info.get('first_listing_date')
        last_date = listing_info.get('last_publish_date')
        
        self.first_listing_label.configure(
            text=f"最早上架时间: {first_date or '--'}"
        )
        self.last_publish_label.configure(
            text=f"最新发布时间: {last_date or '--'}"
        )
        
        # 更新图表区域状态
        trend_charts = trend_data.get('trend_charts', {})
        if trend_charts.get('has_chart_data'):
            self.chart_label.configure(
                text="趋势图表数据已加载\n可在图表库支持下展示",
                text_color="green"
            )
        else:
            self.chart_label.configure(
                text="暂无图表数据\n（图表数据需通过API获取）",
                text_color="gray"
            )
    
    def _clear_display(self):
        """清空显示"""
        for card in self.stats_cards.values():
            card.value_label.configure(text="--")
        
        self.first_listing_label.configure(text="最早上架时间: --")
        self.last_publish_label.configure(text="最新发布时间: --")
        self.chart_label.configure(
            text="趋势图表区域\n（需要接入图表库如 matplotlib 或 pygal）",
            text_color="gray"
        )


class TrendDashboardDialog(ctk.CTkToplevel):
    """趋势数据看板对话框"""
    
    def __init__(self, parent, trend_data: Dict[str, Any] = None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.title("商品成交趋势")
        self.geometry("800x500")
        
        # 创建看板
        self.dashboard = TrendDashboard(self)
        self.dashboard.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 关闭按钮
        self.close_btn = ctk.CTkButton(
            self,
            text="关闭",
            command=self.destroy
        )
        self.close_btn.pack(pady=10)
        
        # 如果有数据则立即更新
        if trend_data:
            self.dashboard.update_data(trend_data)
        
        # 模态对话框
        self.transient(parent)
        self.grab_set()
        self.focus_set()


def show_trend_dashboard(parent, trend_data: Dict[str, Any]):
    """显示趋势数据看板"""
    dialog = TrendDashboardDialog(parent, trend_data)
    return dialog


if __name__ == '__main__':
    # 测试代码
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.geometry("900x600")
    
    # 测试数据
    test_data = {
        'sales_stats': {
            'yearly_sales': 2000,
            'monthly_sales_30d': 200,
            'dropship_orders_30d': 100,
            'repurchase_rate': 33.0,
            'pickup_rate_48h': 100.0,
        },
        'listing_info': {
            'first_listing_date': '2023-06-18 10:03:59',
            'last_publish_date': '2026-04-01 13:10:05',
        },
        'trend_charts': {
            'has_chart_data': True,
        }
    }
    
    dashboard = TrendDashboard(root)
    dashboard.pack(fill="both", expand=True, padx=20, pady=20)
    dashboard.update_data(test_data)
    
    root.mainloop()
