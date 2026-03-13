from core.strategy.base_strategy import BaseStrategy
import pandas as pd

class DualMAStrategy(BaseStrategy):
    """
    双均线策略
    策略逻辑：
    1. 短周期均线(Short MA)上穿长周期均线(Long MA) -> 买入 (金叉)
    2. 短周期均线(Short MA)下穿长周期均线(Long MA) -> 卖出 (死叉)
    """
    def __init__(self, short_window=5, long_window=20):
        super().__init__()
        self.short_window = short_window
        self.long_window = long_window
        self.history = [] # 存储收盘价历史

    def initialize(self):
        self.log(f"初始化双均线策略: Short={self.short_window}, Long={self.long_window}")

    def on_bar(self, bar):
        symbol = bar['symbol']
        close_price = bar['close']
        date = bar['date']
        
        self.history.append(close_price)
        
        # 确保数据足够计算均线
        if len(self.history) <= self.long_window:
            return
            
        # 计算均线
        # 注意：这里为了演示方便，每次都重新计算 rolling mean
        # 在实盘高频场景下应优化为增量计算
        data = pd.Series(self.history)
        
        ma_short = data.rolling(window=self.short_window).mean().iloc[-1]
        ma_long = data.rolling(window=self.long_window).mean().iloc[-1]
        
        prev_ma_short = data.rolling(window=self.short_window).mean().iloc[-2]
        prev_ma_long = data.rolling(window=self.long_window).mean().iloc[-2]
        
        curr_pos = self.get_position(symbol)
        
        # 金叉：短期上穿长期 (前一时刻短<=长，当前短>长)
        if prev_ma_short <= prev_ma_long and ma_short > ma_long:
            if curr_pos == 0:
                self.log(f"金叉出现 ({date.strftime('%Y-%m-%d')}): Short={ma_short:.2f}, Long={ma_long:.2f} -> 买入")
                # 假设买入 1000 股 (10手)
                self.buy(symbol, 0, 1000, "MARKET") 
                
        # 死叉：短期下穿长期 (前一时刻短>=长，当前短<长)
        elif prev_ma_short >= prev_ma_long and ma_short < ma_long:
            if curr_pos > 0:
                self.log(f"死叉出现 ({date.strftime('%Y-%m-%d')}): Short={ma_short:.2f}, Long={ma_long:.2f} -> 卖出")
                self.sell(symbol, 0, curr_pos, "MARKET") # 清仓
