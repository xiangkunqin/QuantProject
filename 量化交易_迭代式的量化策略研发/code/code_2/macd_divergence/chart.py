# coding=utf-8
from __future__ import unicode_literals
import math
import re

from pyecharts import Bar, configure, Grid
from pyecharts import Page
import pandas as pd

"""
普量学院量化投资课程系列案例源码包
普量学院版权所有
仅用于教学目的，严禁转发和用于盈利目的，违者必究
Plouto-Quants All Rights Reserved

普量学院助教微信：niuxiaomi3
"""

"""
绘制统计图
"""

# 更换运行环境内所有图表主题
configure(global_theme='dark')


def draw_echarts(df, slices):
    # 初始化一个画图的页面.每一种信号画一张图片
    page = Page()
    columns = df.columns.values.tolist()
    # 所有统计的信号种类
    signal_items = list(set(df['signal_name'].tolist()))
    signal_items.sort()

    # 所有的N[第n个bar]
    bar_nos = []
    for col in columns:
        if re.match('chg_pct_', col):
            # 获取当前统计的是第几根bar的收益
            bar_nos.append(col.replace('chg_pct_', ''))

    for sig in signal_items:
        # 获取一种信号在M个bar内的收益统计
        bar = Bar(sig + "收益分布", title_text_size=14, width='100%')

        sdf = df[(df['signal_name'] == sig)]
        if sdf.empty:
            continue

        # 划分收益区间,从0开始往正负两端划分收益区间
        # 计算每个收益区间的大小
        max_profit = 0
        min_profit = 0
        for no in bar_nos:
            pcol = 'chg_pct_' + no
            profits = sdf[pcol].tolist()
            max_profit = max(max(profits), max_profit)
            min_profit = min(min(profits), min_profit)
        intervals = []
        if min_profit < 0:
            unit = round(max(max_profit, abs(min_profit)) / slices, 4)
            # 先划分小于0的区间
            for i in range(0, int(math.ceil(abs(min_profit) / unit))):
                intervals.append([round(-(i + 1) * unit, 4), round(-i * unit, 4)])
            intervals.reverse()
        else:
            unit = max_profit / slices

        for i in range(0, int(math.ceil(abs(max_profit) / unit))):
            intervals.append([i * unit, (i + 1) * unit])

        # 显示收益区间之前先格式化成百分比。
        format_intervals = ['%.2f%%~%.2f%%' % (i[0] * 100, i[1] * 100) for i in intervals]

        for no in bar_nos:
            # 计算第M个bar收益，落在某一个收益区间的概率
            win_ratios = []
            pcol = 'chg_pct_' + no
            for interval in intervals:
                # 统计在收益落在某个收益区间的概率
                conf = (sdf[pcol] > interval[0]) & (sdf[pcol] <= interval[1])
                # 避免int类型直接除之后返回的还是int,这里*1.0
                win_ratios.append(round(len(sdf[conf]) / (len(sdf) * 1.0), 2))
            bar.add("第%s个bar" % no, format_intervals, win_ratios,
                    xaxis_name='收益区间',
                    xaxis_name_pos='end',
                    xaxis_name_size=12,
                    xaxis_label_textsize=12,
                    xaxis_interval=1,
                    xaxis_rotate=45,
                    yaxis_name='概率',
                    yaxis_name_pos='end',
                    yaxis_name_size=12,
                    yaxis_label_textsize=12,
                    is_splitline_show=False,
                    # 默认为 X 轴，横向
                    is_datazoom_show=True,
                    datazoom_type="both",
                    datazoom_range=[40, 60],
                    # 额外的 dataZoom 控制条，纵向
                    # is_datazoom_extra_show=True,
                    # datazoom_extra_type="slider",
                    # datazoom_extra_range=[10, 25],
                    # is_toolbox_show=False,
                    )
        grid = Grid(width='100%')
        grid.add(bar, grid_bottom=120)
        page.add(grid)

    page.render()


if __name__ == '__main__':
    df = pd.read_csv('resources/signals.csv')
    if df.empty:
        raise Exception('没有任何信号')
    draw_echarts(df, 50)
