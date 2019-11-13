"""
有任何问题，可以联系普量学院助教微信：niuxiaomi3
"""

1. 注册并登录一创聚宽平台【https://ycjq.95358.com/】

2. 分别上传以下module【检测信号：金叉，死叉，背离】。
     点击投资研究 -> 进入投资研究页面 -> 点击上传按钮，分别上传以下文件：
	- jukuan_db.py 		                # 数据获取接口
	- jukuan_macd_config.py 	        # macd信号检测配置文件
	- jukuan_macd_signal.py 			# 历史数据缓存以及信号检测
	- signal_statistics.py              # 信号统计

3. 如何在策略中获取金叉、死叉、背离。在回测中检测信号的参考代码：strategy_demo.py。
    (1) 编写策略
         -  点击我的策略 -> 进入策略列表页面 -> 点击新建策略 -> 进入策略编写页面。

    (2)如何在策略中，获取module检测到的信号
        - 引入module：from jukuan_macd_signal import *

        - 在策略启动函数中:   初始化MacdCache对象，需要设置以下参数：
                1. 信号的检测周期
                2. 要检测的股票池【受限于回测平台的内存限制，建议不超过300支股票】

        - 在每根bar收盘后:  更新MacdCache对象,  以当前bar的时间更新：
                检测信号周期是30m，就在30分钟bar收盘后，更新MacdCache。

        - 获取信号
              1. 获取[顶/底]背离： macd_cache.divergences[code]
              2. 获取金叉：macd_cache.bars[code].iloc[-1]['gold']
              3. 获取死叉：macd_cache.bars[code].iloc[-1]['death']
              在获取信号时，首先需要判断缓存是否存在。

        **注意：如果检测的信号是分钟级别的，回测时必须选择每分钟。[新建策略页面--> 右侧选框,可选每天/每分钟]


4. 信号胜率和赔率统计(信号发生后m个bar内)
    (1) 统计数据
        - 在策略中引入信号module：from signal_statistics import *
        - 在初始化函数initialize,追加一行代码，定义保存信号的变量，例子：
            def initialize(context):
                g.signals = []

        - 记录需要统计的信号：在信号触发后，初始化一个Signal对象，并保存到g.signals中。以金叉为例：
             # 注意，需要判断后面3种情况都成立，才输出信号：存在该股票的缓存，股票的缓存信息不为空， 并且当前bar发生金叉
             if code in macd_cache.bars.keys() and not macd_cache.bars[code].empty and macd_cache.bars[code].iloc[-1]['gold']:
                tm = macd_cache.bars[code].iloc[-1].name
                signal = MacdSignal(code=code, period=macd_cache.period, tm=tm, name='GOLD')
                g.signals.append(signal)

        - 在策略中加入on_strategy_end函数【聚宽内置的函数，在策略结束后运行】, 然后在该函数中调用信号统计的方法。
          回测结束后，在投资研究页面，可以找到信号记录以及统计结果文件：signals.csv, signal_success_ratio.csv
          注意：每次回测都会重写这两个文件，请注意下载保存每次回测的结果。
          
		  调用信号统计的例子：
          def on_strategy_end(context):

              # 第二个参数backtest_end_tm：回测结束日期
              # 第三个参数：list类型，分别统计多少个bar以后的成功率。
              SignalStatistics.success_ratio(g.signals, backtest_end_tm, [4,8,16,20,24])


    (2) 绘制信号的收益分布直方图
        - 本地下载安装python环境。
            1. python2.7
              下载地址：https://www.python.org/downloads/release/python-2715/
              下载版本：Windows x86-64 executable installer

            2. pyecharts
               以管理员身份打开命令行窗口： 运行 pip install pyecharts --user

            3. pandas
               以管理员身份打开命令行窗口： 运行 pip install pandas --user

        - 从一创聚宽的投资研究页面，下载信号记录文件signals.csv

        - 将signals.csv复制到resources/目录下

        - 以管理员身份打开命令行窗口:
            1. cd ../macd_divergence                  # 切换到chart.py所在的目录下,根据保存的位置自行修改路径
            2. python chart.py

        - 在macd_divergence目录下已经自动生成render.html。使用浏览器打开，即可显示收益分布直方图。



"""
普量学院量化投资课程系列案例源码包
普量学院版权所有
仅用于教学目的，严禁转发和用于盈利目的，违者必究
Plouto-Quants All Rights Reserved

普量学院助教微信：niuxiaomi3
"""