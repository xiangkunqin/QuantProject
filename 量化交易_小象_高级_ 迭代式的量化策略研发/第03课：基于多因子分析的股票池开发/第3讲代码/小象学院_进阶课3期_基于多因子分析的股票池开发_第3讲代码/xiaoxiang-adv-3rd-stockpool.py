# coding=utf8
"""
普量学院量化投资课程系列案例源码包
普量学院版权所有
仅用于教学目的，严禁转发和用于盈利目的，违者必究
©Plouto-Quants All Rights Reserved

普量学院助教微信：niuxiaomi3
"""
# 导入函数库
import jqdata
import pandas as pd
import numpy as np
import math
import talib as tl

# 股票池计算涨跌幅的窗口大小
CHANGE_PCT_DAY_NUMBER = 25
# 更新股票池的间隔天数
CHANGE_STOCK_POOL_DAY_NUMBER = 25


# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 过滤掉order系列API产生的比error级别低的log
    log.set_level('order', 'error')

    ### 股票相关设定 ###
    # 设定滑点为0
    set_slippage(FixedSlippage(0))
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

    init_global(context)

    # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    # 交易
    run_daily(trade, time='every_bar',reference_security='000300.XSHG')
    # 收盘后运行
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')


'''
初始化全局变量
'''
def init_global(context):
    # 距上一次股票池更新的天数
    g.stock_pool_update_day = 0
    # 股票池，股票代码
    g.stock_pool = []
    # 需要买入的股票池
    g.need_buy_stock = []
    # 是否更新股票池
    g.updated_stock_pool = False
    # 每只标的需要买入的头寸
    g.position = 0


'''
开盘前运行函数
'''
def before_market_open(context):
    pass


'''
交易函数
'''
def trade(context):
    if not g.updated_stock_pool:
        return
    # 调用卖出函数
    sell(context)

    # 计算头寸
    if len(g.need_buy_stock) > 0:
        g.position = context.portfolio.available_cash / len(g.need_buy_stock)
        log.info("股票池变动后需要买入的数量",len(g.need_buy_stock),"可用现金",context.portfolio.available_cash,"每只股票的头寸",g.position,"需要新买入的标的",g.need_buy_stock)
    g.updated_stock_pool = False

    buy(context)   # 建仓
    pass


'''
收盘后处理

1. 更新股票池
2. 更新股票池后，获取需要新买入的标的列表
'''
def after_market_close(context):
    if g.stock_pool_update_day % CHANGE_STOCK_POOL_DAY_NUMBER == 0:
        old_stock_pool = g.stock_pool
        # 更新股票池
        stock_pool(context)
        # 获取需要新买入的标的列表
        g.need_buy_stock = []
        for code in g.stock_pool:
            if code not in old_stock_pool:
                g.need_buy_stock.append(code)
        g.updated_stock_pool = True
    g.stock_pool_update_day = (g.stock_pool_update_day + 1) % CHANGE_STOCK_POOL_DAY_NUMBER

    record(pos=(context.portfolio.positions_value / context.portfolio.total_value * 100))
    pass


'''
卖出逻辑。
当标的不在股票池中时，卖出该标的的持仓。
'''
def sell(context):
    for code in context.portfolio.positions.keys():
        if code not in g.stock_pool:
            if is_low_limit(code):
                continue
            # 标的已经不在股票池中尝试卖出该标的的股票
            order_ = order_target(security=code, amount=0)
            if order_ is not None and order_.filled:
                log.info("交易 卖出",code,order_.filled)
    pass

'''
买入逻辑。
'''
def buy(context):
    for code in g.stock_pool:
        if code in context.portfolio.positions.keys():
            continue
        current_data = get_current_data()[code]
        if current_data == None:
            return
        if is_high_limit(code):
            continue
        order_ = order_value(security=code, value=g.position)
        if order_ is not None and order_.filled > 0:
            log.info("交易 买入",code,"买入仓位",g.position,"买入的股数",order_.filled)
    pass


'''
加载股票的财务数据，包括总市值和PE
'''
def load_fundamentals_data(context):
    df = get_fundamentals(query(valuation,indicator), context.current_dt.strftime("%Y-%m-%d"))
    raw_data = []
    for index in range(len(df['code'])):
        raw_data_item = {
            'code'      :df['code'][index],
            'market_cap':df['market_cap'][index],
            'pe_ratio'  :df['pe_ratio'][index]
            }
        raw_data.append(raw_data_item)
    return raw_data


'''
计算标的的25日涨跌幅。

Args:
    context 上下文
    codes   标的的代码列表
Returns:
    标的的涨跌幅列表。列表中的每一项数据时一个字典：
        code:标的代码
        change_pct: 标的的涨跌幅
'''
def load_change_pct_data(context,codes):
    change_pct_dict_list = []
    # 计算涨跌幅需要用到前一日收盘价，所以需要多加载一天的数据，
    # 而这里在第二日的开盘前运行，计算前一个交易日收盘后的数据，所以需要再多加载一天
    # 使用固定的25个交易日，而非25个bar计算涨跌幅
    count = CHANGE_PCT_DAY_NUMBER + 1
    # 获取25个交易日的日期
    pre_25_dates = jqdata.get_trade_days(start_date=None, end_date=context.current_dt, count=count)
    pre_25_date = pre_25_dates[0]
    pre_1_date = pre_25_dates[-1]
    for code in codes:
        pre_25_data =  get_price(code, start_date=None, end_date=pre_25_date, frequency='daily', fields=['close'], skip_paused=True, fq='post', count=1)
        pre_1_data =  get_price(code, start_date=None, end_date=pre_1_date, frequency='daily', fields=['close'], skip_paused=True, fq='post', count=1)
        pre_25_close = None
        pre_1_close = None
        if str(pre_25_date) == str(pre_25_data.index[0])[:10]:
            pre_25_close = pre_25_data['close'][0]
        if str(pre_1_date) == str(pre_1_data.index[0])[:10]:
            pre_1_close = pre_1_data['close'][0]

        if pre_25_close != None and pre_1_close != None and not math.isnan(pre_25_close) and not math.isnan(pre_1_close):
            change_pct = (pre_1_close - pre_25_close) / pre_25_close
            item = {'code':code, 'change_pct': change_pct}
            change_pct_dict_list.append(item)
    return change_pct_dict_list



'''
更新股票池。该方法在收盘后调用。

1. 全市场的股票作为基础股票池
2. 在基础股票池的基础上剔除ST的股票作为股票池1
3. 在股票池1的基础上剔除总市值最小的10%的股票作为股票池2
4. 在股票池2的基础上剔除PE < 0 或 PE > 100的股票作为股票池3
5. 在股票池3的基础上 取25日跌幅前10%的股票作为最终的股票池
'''
def stock_pool(context):
    current_date = context.current_dt.strftime("%Y-%m-%d")
    # 获取股票财务数据
    raw_data = load_fundamentals_data(context)

    # 剔除ST的股票
    raw_data_array = []
    current_datas = get_current_data()
    for item in raw_data:
        code = item['code']
        current_data = current_datas[code]
        if current_data.is_st:
            continue
        name = current_data.name
        if 'ST' in name or '*' in name or '退' in name:
            continue
        raw_data_array.append(item)

    raw_data = raw_data_array
    # 按照财务信息中的总市值降序排序
    raw_data = sorted(raw_data,key = lambda item:item['market_cap'],reverse=True)
    # 剔除总市值排名最小的10%的股票
    fitered_market_cap = raw_data[:int(len(raw_data) * 0.9)]
    # 剔除PE TTM 小于0或大于100
    filtered_pe = []
    for stock in fitered_market_cap:
        if stock['pe_ratio'] == None or math.isnan(stock['pe_ratio']) or float(stock['pe_ratio']) < 0 or float(stock['pe_ratio']) > 100:
            continue
        filtered_pe.append(stock['code'])

    # 加载标的的涨跌幅信息
    change_pct_dict_list = load_change_pct_data(context,filtered_pe)
    # 按照涨跌幅升序排序
    change_pct_dict_list = sorted(change_pct_dict_list,key = lambda item:item['change_pct'],reverse=False)
    # 取跌幅前10%的股票
    change_pct_dict_list = change_pct_dict_list[0:(int(len(change_pct_dict_list)*0.1))]

    # 获取最终的股票池
    g.stock_pool = []
    for stock in change_pct_dict_list:
        g.stock_pool.append(stock['code'])
    log.info('调整股票池,筛选出的股票池：',g.stock_pool)
    pass


'''
判断标的是否涨停或停牌。

Args:
    code 标的的代码

Returns:
    True 标的涨停或停牌，该情况下无法买入
'''
def is_high_limit(code):
    current_data = get_current_data()[code]
    if current_data.last_price >= current_data.high_limit:
        return True
    if current_data.paused:
        return True
    return False


'''
判断标的是否跌停或停牌。

Args:
    code 标的的代码

Returns:
    True 标的跌停或停牌，该情况下无法卖出
'''
def is_low_limit(code):
    current_data = get_current_data()[code]
    if current_data.last_price <= current_data.low_limit:
        return True
    if current_data.paused:
        return True
    return False
