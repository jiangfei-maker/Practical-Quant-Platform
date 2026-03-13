from core.strategy.base_strategy import BaseStrategy
from core.strategy.indicator_calculator import IndicatorCalculator
import pandas as pd

class RSIBollingerStrategy(BaseStrategy):
    """
    RSI + Bollinger Bands 均值回归策略
    
    策略逻辑:
    1. 买入信号 (Buy Signal):
       - RSI < rsi_lower (超卖)
       - Close < Bollinger Lower Band (跌破下轨)
       - 认为价格被低估，即将回调
       
    2. 卖出信号 (Sell Signal):
       - RSI > rsi_upper (超买)
       - Close > Bollinger Upper Band (突破上轨)
       - 认为价格被高估，即将回调
    """
    def __init__(self, rsi_period=14, boll_window=20, rsi_lower=30, rsi_upper=70):
        super().__init__()
        self.rsi_period = rsi_period
        self.boll_window = boll_window
        self.rsi_lower = rsi_lower
        self.rsi_upper = rsi_upper
        
        self.history_close = []
        self.history_high = []
        self.history_low = []
        self.history_dates = []

    def initialize(self):
        self.log(f"初始化 RSI+Bollinger 策略: RSI_Period={self.rsi_period}, Boll_Window={self.boll_window}")

    def on_bar(self, bar):
        symbol = bar['symbol']
        close_price = bar['close']
        date = bar['date']
        
        # 记录历史数据
        self.history_close.append(close_price)
        self.history_high.append(bar['high'])
        self.history_low.append(bar['low'])
        self.history_dates.append(date)
        
        # 确保数据足够
        min_len = max(self.rsi_period, self.boll_window) + 2
        if len(self.history_close) < min_len:
            return
            
        # 构造 DataFrame 用于计算
        # 注意: 实盘中应优化为增量计算或只取最近N条
        df = pd.DataFrame({
            'close': self.history_close,
            'high': self.history_high, # RSI/Boll 其实只用 Close，但为了兼容性保留
            'low': self.history_low
        })
        
        # 计算指标
        rsi_series = IndicatorCalculator.calculate_rsi(df, period=self.rsi_period)
        upper, mid, lower = IndicatorCalculator.calculate_boll(df, window=self.boll_window)
        
        current_rsi = rsi_series.iloc[-1]
        current_upper = upper.iloc[-1]
        current_lower = lower.iloc[-1]
        
        curr_pos = self.get_position(symbol)
        
        # 交易逻辑
        # 买入: RSI超卖 且 价格跌破下轨
        if current_rsi < self.rsi_lower and close_price < current_lower:
            if curr_pos == 0:
                self.log(f"买入信号 ({date.strftime('%Y-%m-%d')}): RSI={current_rsi:.2f}, Close={close_price:.2f} < Lower={current_lower:.2f}")
                self.buy(symbol, 0, 1000, "MARKET")
        
        # 卖出: RSI超买 且 价格突破上轨
        elif current_rsi > self.rsi_upper and close_price > current_upper:
            if curr_pos > 0:
                self.log(f"卖出信号 ({date.strftime('%Y-%m-%d')}): RSI={current_rsi:.2f}, Close={close_price:.2f} > Upper={current_upper:.2f}")
                self.sell(symbol, 0, curr_pos, "MARKET")
