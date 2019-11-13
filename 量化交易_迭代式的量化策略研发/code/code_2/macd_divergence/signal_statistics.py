# -*- encoding:utf-8 -*-
from kuanke.user_space_api import *
import pandas as pd
import numpy as np

"""
普量学院量化投资课程系列案例源码包
普量学院版权所有
仅用于教学目的，严禁转发和用于盈利目的，违者必究
Plouto-Quants All Rights Reserved

普量学院助教微信：niuxiaomi3
"""

"""
信号统计
"""


class MacdSignal:
    """
    触发的信号
    """

    def __init__(self, code, name, period, tm):
        """
        :param code: 股票代码
        :param name: 信号名称
        :param period: 信号周期
        :param tm: 触发信号的时间
        """
        self.code = code
        self.name = name
        self.period = period
        self.tm = tm


class SignalStatistics:
    def __init__(self):
        pass

    @classmethod
    def success_ratio(cls, signals, backtest_end_tm, bar_idx_list):
        """
        :param bar_idx_list: list类型。例如，[4,8,16]， 分别表示触发信号后第4根bar、第8根bar、第16根bar
        :param backtest_end_tm: str类型， 回测结束日期。'2018-09-30 15:00:00'
        :param signals: Signal类型，至少包含属性：code[股票代码], name[信号名称], tm[信号触发时间], period[信号周期]
        :return: 在投资研究页面，生成一个信号统计文件。统计项：触发信号后, M个bar内的胜率和赔率。最大支持100个bar
        """
        df = cls.calc_siganl_profit(signals, backtest_end_tm, bar_idx_list)
        write_file('signals.csv', df.to_csv(index=False), append=False)

        # 统计每种信号的成功率
        signal_names = list(set(list(df['signal_name'])))
        signal_names.sort()

        columns = [u"信号", u"触发次数", u"上涨次数", u"下跌次数",
                   u"上涨概率", u"下跌概率", u"平均涨跌幅",
                   u"上涨股票平均涨幅", u"下跌股票平均跌幅"]
        temp = []
        for idx in bar_idx_list:
            temp.append(['M=' + str(idx)])
            temp.append(columns)
            for name in signal_names:
                row = cls.success_ratio_of_single(name, df[df['signal_name'] == name], idx)
                temp.append(row)
            temp.append([])
            temp.append([])  # 追加两行空行
        write_file('signal_success_ratio.csv', pd.DataFrame(temp).to_csv(index=False, header=False), append=False)

    @classmethod
    def calc_siganl_profit(cls, signals, end_tm, bar_idx_list):
        """
        计算所有信号m个bar内的涨跌幅
        :param signals: list类型，所有的信号
        :param end_tm: str类型， 统计截止时间
        :param bar_idx_list:  list类型， 例如，[4,8,16]， 分别表示触发信号后第4根bar、第8根bar、第16根bar
        :return: DataFrame类型。包含：code/signal_name/period/chg_pct_1...chg_pct_m[从第1根bar到第n根bar的收益]
        """
        columns = ['code', 'tm', 'signal_name', 'period']
        for bar_idx in bar_idx_list:
            columns.append('chg_pct_' + str(bar_idx))
        signal_prifit_df = pd.DataFrame(columns=columns)

        count = 0
        for signal in signals:
            tm = signal.tm
            code = signal.code
            df = get_price(code, start_date=tm, end_date=end_tm, frequency=signal.period, fields=['close'],
                           skip_paused=True, fq='pre')
            if df.empty:
                continue
            dfsize = len(df)
            temp = [code, tm, signal.name, signal.period]
            for bar_idx in bar_idx_list:
                idx = dfsize - 1 if bar_idx >= dfsize else bar_idx
                profit = (df.iloc[idx]['close'] - df.iloc[0]['close']) / df.iloc[0]['close']
                temp.append(profit)
            signal_prifit_df.loc[str(count)] = temp
            count += 1
        return signal_prifit_df

    @classmethod
    def success_ratio_of_single(cls, name, df, bar_idx):
        """
        信号触发后第N个bar的胜率和赔率
        :param name: str类型， 信号名称
        :param df: Dataframe类型 所有名称相同的信号
        :param bar_idx: int类型， 触发信号后的第几根bar
        :return: list类型：信号名称、信号触发次数、上涨次数、下跌次数、
                          上涨概率、下跌概率、平均涨跌幅、上涨平均涨幅、下跌平均跌幅
        """
        pcol = 'chg_pct_' + str(bar_idx)
        rise = df[df[pcol] > 0]
        fall = df[df[pcol] < 0]
        rise_num = len(rise)
        fail_num = len(fall)
        rise_ratio = None
        fall_ratio = None
        trigger_num = len(df)
        if trigger_num > 0:
            rise_ratio = cls.to_per(float(rise_num) / trigger_num)
            fall_ratio = cls.to_per(float(fail_num) / trigger_num)

        return [name, trigger_num, rise_num, fail_num, rise_ratio, fall_ratio, cls.to_per(df[pcol].mean()),
                cls.to_per(rise[pcol].mean()), cls.to_per(fall[pcol].mean())]

    @staticmethod
    def to_per(digits):
        if np.isnan(digits) or digits is None:
            return np.nan
        return '%.2f%%' % (digits * 100)
