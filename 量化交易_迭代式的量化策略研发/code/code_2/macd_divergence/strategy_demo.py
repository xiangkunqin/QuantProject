from jqdata import *
from jukuan_macd_signal import *  # 导入自定义的，用于信号检测的库
from signal_statistics import *  # 导入用于统计信号胜率和赔率的库

"""
普量学院量化投资课程系列案例源码包
普量学院版权所有
仅用于教学目的，严禁转发和用于盈利目的，违者必究
Plouto-Quants All Rights Reserved

普量学院助教微信：niuxiaomi3
"""

"""
macd信号检测demo。
"""

PERIOD = '60m'  # 检测信号的k线周期
SIGNAL_PERIOD_UNIT = 60  # 检测信号的时间间隔。与信号检测的周期保持一致。
STOCK_POOL = [str(normalize_code(code)) for code in
              ['002466', '601398', '600085', '0000063', '002236', '000651', '002415', '600703', '300187',
               '002028']]  # 股票池


def initialize(context):
    """
    初始化函数，设定要操作的股票、基准等等
    """
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    log.set_level('order', 'error')
    run_daily(every_bar_start, time='every_bar', reference_security='000300.XSHG')

    # 设置策略的日级输出级别。可选：debug、info、warning、error
    log.set_level('strategy', 'info')
    g.macd_signals = []


def process_initialize(context):
    """
    策略每次启动后运行的函数。策略重启后，initialize函数只能恢复可序列化的对象。
    不可序列化的对象必须要在这里定义。
    """
    g.period = PERIOD
    g.macd_cache = None
    g.stocks = STOCK_POOL
    g.counter = 0

    ## 初始化macd缓存
    if g.macd_cache is None:
        # 使用回测时间，初始化MacdCache
        current_tm = context.current_dt
        g.macd_cache = MacdCache(g.period, current_tm, count=250, stocks=g.stocks)


def every_bar_start(context):
    """
    每隔SIGNAL_PERIOD_UNIT分钟检测一次信号。每根bar开盘前检测，以上一根bar的收盘价产生的信号。
    """
    if g.counter % SIGNAL_PERIOD_UNIT != 0:
        g.counter += 1
        return
    elif g.counter == 0:
        g.counter += 1
    elif g.counter != 0:
        g.counter = 1

    # 以当前回测时间，更新缓存
    current_tm = context.current_dt
    g.macd_cache.update_cache(current_tm)

    for stock_code in g.macd_cache.bars.keys():
        # 获取最新一根bar检测到的背离、金叉、死叉
        divergences = g.macd_cache.divergences[stock_code] if stock_code in g.macd_cache.divergences.keys() else []
        last_bar = g.macd_cache.bars[stock_code].iloc[-1] if not g.macd_cache.bars[stock_code].empty else {}
        tm = last_bar.name
        if len(divergences) > 0:
            for divergence in divergences:
                # DivergenceType.Bottom - 底背离，DivergenceType.Top - 顶背离
                if divergence.divergence_type == DivergenceType.Bottom:
                    g.macd_signals.append(
                        MacdSignal(code=stock_code, period=g.macd_cache.period, tm=tm, name='BottomDivergence'))
                    log.info(
                        '【%s, %s】all divergences=%s' % (stock_code, current_tm, Divergence.to_json_list(divergences)))
                    break

        if 'gold' in last_bar.keys() and last_bar['gold']:
            g.macd_signals.append(MacdSignal(code=stock_code, period=g.macd_cache.period, tm=tm, name='Gold'))
            log.info('【%s, %s】Gold, last_bar=%s, ' % (stock_code, current_tm, last_bar.to_dict()))

        if 'death' in last_bar.keys() and last_bar['death']:
            g.macd_signals.append(MacdSignal(code=stock_code, period=g.macd_cache.period, tm=tm, name='Death'))
            log.info('【%s, %s】Death, last_bar=%s, ' % (stock_code, current_tm, last_bar.to_dict()))


def on_strategy_end(context):
    log.info('开始统计')
    backtest_end_tm = context.run_params.end_date
    SignalStatistics.success_ratio(g.macd_signals, backtest_end_tm, [4, 8, 16, 20, 24])
