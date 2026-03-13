import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger
from core.strategy.base_strategy import BaseStrategy

class RotationStrategy(BaseStrategy):
    """
    轮动策略 (Rotation Strategy)
    基于外部传入的因子得分或预测结果，定期进行持仓轮动
    
    逻辑：
    1. 在每个调仓日 (Rebalance Date)，读取最新的 Alpha Scores
    2. 买入得分最高的 Top N 只股票
    3. 卖出不在 Top N 中的持仓股票
    4. 资金等权重分配 (或根据分数加权)
    """
    
    def __init__(self, 
                 score_data: pd.DataFrame, 
                 top_n: int = 5, 
                 rebalance_period: int = 20,
                 score_col: str = 'predicted_score'):
        """
        :param score_data: 包含 'date', 'stock_code', 'score' 的 DataFrame
        :param top_n: 持仓股票数量
        :param rebalance_period: 调仓周期 (天)
        :param score_col: 分数列名
        """
        super().__init__()
        self.top_n = top_n
        self.rebalance_period = rebalance_period
        self.score_col = score_col
        
        # 预处理分数数据：按日期索引，方便快速查找
        # score_data 应该包含: date, stock_code, score
        self.score_data = score_data.copy()
        if 'date' in self.score_data.columns:
            self.score_data['date'] = pd.to_datetime(self.score_data['date'])
        
        self.last_rebalance_date = None
        self.days_since_rebalance = 0
        
    def initialize(self):
        self.log(f"轮动策略初始化完成: Top {self.top_n}, 调仓周期 {self.rebalance_period}天")

    def on_bar(self, bar: Dict[str, Any]):
        # 注意：on_bar 是针对单只股票的，但在回测引擎中，我们通常是按天循环
        # 如果是单股回测，这个策略没意义
        # 这个策略需要在 BacktestEngine 层面支持多股回测，或者我们在这里 hack 一下
        # 假设 Engine 会按时间顺序推送 bar，我们只需要在每天结束时检查是否需要调仓
        
        # 目前 BacktestEngine 的逻辑是：
        # run() -> for index, row in df.iterrows(): -> on_bar(bar)
        # 这通常是针对单只股票的。
        # 为了支持多股轮动，BacktestEngine 需要修改，或者我们在这里做一些假设。
        
        # 现有的 BacktestEngine.run 接受 df 和 symbol，是单股回测。
        # 我们需要一个新的 BacktestEngine 模式：Multi-Stock Backtest
        pass
        
    def on_day_close(self, current_date: datetime):
        """
        每日收盘后触发 (需要回测引擎支持)
        在这里执行调仓逻辑
        """
        self.days_since_rebalance += 1
        
        # 检查是否是调仓日
        if self.days_since_rebalance < self.rebalance_period and self.last_rebalance_date is not None:
            return

        self.rebalance(current_date)
        self.last_rebalance_date = current_date
        self.days_since_rebalance = 0
        
    def rebalance(self, current_date: datetime):
        self.log(f"=== 开始调仓: {current_date.strftime('%Y-%m-%d')} ===")
        
        # 1. 获取当日（或最近）的因子得分
        # 注意：实际交易中只能用 T-1 日或更早的数据，这里假设 score_data 已经对齐好了
        # 我们查找 date <= current_date 的最新数据
        
        daily_scores = self.score_data[self.score_data['date'] <= current_date]
        if daily_scores.empty:
            self.log("无可用评分数据，跳过调仓")
            return
            
        # 取最近一天的 scores
        latest_date = daily_scores['date'].max()
        target_scores = daily_scores[daily_scores['date'] == latest_date]
        
        # 2. 选出 Top N
        if target_scores.empty:
            return
            
        top_stocks = target_scores.sort_values(self.score_col, ascending=False).head(self.top_n)
        target_symbols = set(top_stocks['stock_code'].tolist())
        
        self.log(f"目标持仓: {target_symbols}")
        
        # 3. 获取当前持仓
        current_positions = self.engine.positions.copy() # {'600519': 100, ...}
        current_symbols = set([s for s, qty in current_positions.items() if qty > 0])
        
        # 4. 生成卖出指令 (不在目标池的)
        sell_list = current_symbols - target_symbols
        for symbol in sell_list:
            qty = self.engine.positions.get(symbol, 0)
            if qty > 0:
                # 获取该股票当前价格 (需要引擎提供获取多股价格的能力)
                current_price = self.engine.get_current_price(symbol)
                if current_price:
                    self.sell(symbol, current_price, qty)
                    self.log(f"卖出 {symbol}, 数量 {qty}")
        
        # 5. 生成买入指令 (在目标池且未持有的，或需要调整权重的)
        # 简单起见：等权重分配
        # 计算可用资金：当前现金 + 预计卖出回款 (简化处理，仅使用当前现金 + 卖出估值)
        # 在回测中，sell 是即时成交的(如果满足条件)，所以 cash 会立即更新
        
        # 这里的逻辑有点依赖引擎的执行顺序。
        # 如果是 Limit 单，可能不会立即成交。如果是 Market 单，会立即更新 Cash。
        # 假设我们用 Market 单或者由撮合引擎立即撮合。
        
        # 重新计算每只股票的目标金额
        total_assets = self.engine.get_total_assets()
        target_value_per_stock = total_assets / self.top_n * 0.95 # 留5%缓冲
        
        for index, row in top_stocks.iterrows():
            symbol = row['stock_code']
            current_price = self.engine.get_current_price(symbol)
            
            if not current_price or pd.isna(current_price):
                self.log(f"无法获取 {symbol} 价格，跳过")
                continue
                
            target_qty = int(target_value_per_stock / current_price / 100) * 100
            current_qty = self.engine.positions.get(symbol, 0)
            
            diff_qty = target_qty - current_qty
            
            if diff_qty > 0:
                # 买入
                self.buy(symbol, current_price, diff_qty)
                self.log(f"买入 {symbol}, 数量 {diff_qty}")
            elif diff_qty < 0:
                # 减仓 (如果策略允许减仓以维持权重)
                # self.sell(symbol, current_price, abs(diff_qty))
                pass
