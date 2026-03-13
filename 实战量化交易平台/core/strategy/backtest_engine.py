import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
import uuid

from core.data.financial_fetcher import FinancialDataFetcher
from core.strategy.matching_engine import MatchingEngine, Order, Trade
from core.strategy.base_strategy import BaseStrategy

class BacktestEngine:
    """
    回测引擎
    负责驱动策略运行、管理资金和持仓、调用撮合引擎
    """
    def __init__(self, start_date: str, end_date: str, initial_capital: float = 100000.0):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, int] = {} # symbol -> quantity
        
        self.data_fetcher = FinancialDataFetcher()
        self.matching_engine = MatchingEngine()
        self.strategy: Optional[BaseStrategy] = None
        
        self.processed_trades = set() # keep track of processed trade IDs
        self.trade_history: List[Dict] = []
        self.daily_value: List[Dict] = [] # date, total_value
        
    def load_strategy(self, strategy: BaseStrategy):
        self.strategy = strategy
        self.strategy.set_engine(self)
        
    def submit_order(self, symbol: str, side: str, price: float, quantity: int, order_type: str = "LIMIT") -> str:
        """
        策略调用的下单接口
        """
        # 简单的资金检查 (仅买入时)
        if side == "BUY":
            estimated_cost = price * quantity if price > 0 else 0 # 市价单暂不检查准确资金，或者预估
            if self.cash < estimated_cost:
                logger.warning(f"资金不足，无法下单: 需要 {estimated_cost}, 可用 {self.cash}")
                return ""
                
        # 简单的持仓检查 (仅卖出时)
        if side == "SELL":
            current_qty = self.positions.get(symbol, 0)
            if current_qty < quantity:
                logger.warning(f"持仓不足，无法下单: 需要 {quantity}, 可用 {current_qty}")
                return ""

        order_id = str(uuid.uuid4())
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            price=price,
            quantity=quantity,
            created_at=datetime.now() # 应该是回测时间，但这里简化用当前时间，或者传入当前回测时间
        )
        self.matching_engine.submit_order(order)
        return order_id

    def run(self, strategy: BaseStrategy, df: Optional[pd.DataFrame] = None, symbol: str = ""):
        """
        运行回测
        
        支持两种模式:
        1. 单标的回测 (Single Asset): 传入 df 和 symbol
        2. 多标的/全市场回测 (Multi Asset): df=None, symbol="", 需要 engine 能够动态获取全市场数据
        """
        self.load_strategy(strategy)
        
        if not self.strategy:
            logger.error("未加载策略")
            return

        # 模式判断
        is_multi_asset = (df is None and not symbol)
        
        if not is_multi_asset:
            # === 单标的模式 ===
            logger.info(f"开始单标的回测 {symbol} 从 {self.start_date} 到 {self.end_date}")
            
            # 1. 获取数据
            if df is None or df.empty:
                df = self.data_fetcher.get_stock_history(symbol, self.start_date, self.end_date)
                
            if df is None or df.empty:
                logger.error(f"未获取到 {symbol} 的历史数据")
                return

            # 2. 初始化策略
            self.strategy.initialize()
            
            # 3. 按日循环
            for index, row in df.iterrows():
                current_date = row['date']
                
                # 构造 Bar 数据
                bar = {
                    "symbol": symbol,
                    "date": current_date,
                    "open": row['open'],
                    "high": row['high'],
                    "low": row['low'],
                    "close": row['close'],
                    "volume": row['volume']
                }
                
                # 更新当前价格缓存 (用于持仓市值计算等)
                self.matching_engine.update_market_price(symbol, row['close'])
                
                # 触发策略
                self.strategy.on_bar(bar)
                
                # 处理撮合
                self.matching_engine.match(bar)
                self._process_trades()
                
                # 每日结算
                self._record_daily_value(current_date)
                
        else:
            # === 多标的模式 (Market Replay) ===
            logger.info(f"开始多标的全市场回测 从 {self.start_date} 到 {self.end_date}")
            
            # 1. 初始化策略
            self.strategy.initialize()
            
            # 2. 获取交易日历
            dates = self.data_fetcher.get_trade_dates(self.start_date, self.end_date)
            
            # 3. 按日循环
            for current_date_str in dates:
                current_date = pd.to_datetime(current_date_str)
                
                # 3.1 获取当日全市场数据 (Snapshot)
                # 这是一个昂贵的操作，实际应该按需获取或预加载
                # 这里假设 strategy 会告诉我们需要哪些股票的数据，或者 strategy 自己处理选股
                
                # 对于 RotationStrategy，它主要是在 on_day_close 里根据 score 选股
                # 然后下单。下单时需要知道当前价格。
                
                # 触发策略的每日收盘事件 (Strategy 需要实现 on_day_close)
                if hasattr(self.strategy, 'on_day_close'):
                    self.strategy.on_day_close(current_date)
                
                # 3.2 撮合与结算
                # 对于多标的回测，我们需要当日所有持仓股票的行情来撮合
                # 以及策略打算买入的股票的行情
                
                # 获取涉及到的股票池 (持仓 + 挂单)
                active_symbols = set(self.positions.keys()) | set(self.matching_engine.orders.keys())
                
                # 如果是 RotationStrategy，刚下完单，orders 里会有新单
                
                for sym in list(active_symbols): # list copy needed
                    # 获取该股当日行情
                    daily_bar = self.data_fetcher.get_daily_bar(sym, current_date_str)
                    if daily_bar:
                        self.matching_engine.update_market_price(sym, daily_bar['close'])
                        self.matching_engine.match(daily_bar)
                
                self._process_trades()
                self._record_daily_value(current_date)
        
        return self.get_results()

    def get_current_price(self, symbol: str) -> float:
        """获取最新市场价格"""
        return self.matching_engine.market_prices.get(symbol, 0.0)

    def get_total_assets(self) -> float:
        """获取当前总资产 (现金 + 持仓市值)"""
        market_value = 0.0
        for sym, qty in self.positions.items():
            price = self.matching_engine.market_prices.get(sym, 0.0)
            market_value += price * qty
        return self.cash + market_value

    def get_results(self) -> Dict:
        """
        获取回测结果数据，用于前端展示
        """
        if not self.daily_value:
            return {}
            
        df_daily = pd.DataFrame(self.daily_value)
        df_trades = pd.DataFrame(self.trade_history)
        
        initial = self.initial_capital
        final = self.daily_value[-1]["total_value"]
        ret = (final - initial) / initial * 100
        
        # 计算最大回撤
        df_daily['max_value'] = df_daily['total_value'].cummax()
        df_daily['drawdown'] = (df_daily['total_value'] - df_daily['max_value']) / df_daily['max_value']
        max_drawdown = df_daily['drawdown'].min() * 100
        
        # 计算年化收益率和夏普比率
        days = (pd.to_datetime(self.end_date) - pd.to_datetime(self.start_date)).days
        if days > 0:
            annualized_return = ((final / initial) ** (365 / days) - 1) * 100
        else:
            annualized_return = 0.0
            
        # 简单夏普比率 (假设无风险利率 3%)
        rf = 0.03
        daily_ret = df_daily['total_value'].pct_change().dropna()
        if not daily_ret.empty and daily_ret.std() > 0:
            sharpe_ratio = (annualized_return / 100 - rf) / (daily_ret.std() * (252 ** 0.5))
        else:
            sharpe_ratio = 0.0

        # 计算交易统计指标 (胜率、盈亏比)
        trade_stats = self._analyze_trades()

        return {
            "metrics": {
                "initial_capital": initial,
                "final_value": final,
                "total_return": ret,
                "annualized_return": annualized_return,
                "max_drawdown": max_drawdown,
                "sharpe_ratio": sharpe_ratio,
                "trade_count": len(trade_stats.get('round_trips', [])), # 使用完整交易对数量
                "win_rate": trade_stats.get('win_rate', 0.0),
                "profit_factor": trade_stats.get('profit_factor', 0.0),
                "avg_win": trade_stats.get('avg_win', 0.0),
                "avg_loss": trade_stats.get('avg_loss', 0.0)
            },
            "daily_value": df_daily,
            "trade_history": df_trades,
            "portfolio_value": df_daily['total_value'].tolist(),
            "round_trips": trade_stats.get('round_trips', [])
        }

    def _analyze_trades(self) -> Dict:
        """
        分析交易记录，计算胜率、盈亏比等
        使用 FIFO 匹配买卖单来构建 Round-Trip Trades
        """
        trades = sorted(self.trade_history, key=lambda x: x['date'])
        
        buy_queue = [] # list of {price, qty, commission}
        round_trips = []
        
        for t in trades:
            if t['side'] == 'BUY':
                buy_queue.append({
                    'price': t['price'],
                    'qty': t['quantity'],
                    'commission': t['commission'],
                    'date': t['date']
                })
            elif t['side'] == 'SELL':
                sell_qty = t['quantity']
                sell_price = t['price']
                sell_comm_total = t['commission']
                
                # FIFO Matching
                while sell_qty > 0 and buy_queue:
                    buy_order = buy_queue[0]
                    matched_qty = min(sell_qty, buy_order['qty'])
                    
                    # Calculate PnL for this chunk
                    # Cost basis: (Buy Price * Qty) + Buy Comm (pro-rated)
                    # Proceeds: (Sell Price * Qty) - Sell Comm (pro-rated)
                    
                    buy_comm_share = buy_order['commission'] * (matched_qty / buy_order['qty'])
                    sell_comm_share = sell_comm_total * (matched_qty / t['quantity']) # Approximation if multiple matches
                    
                    cost = (buy_order['price'] * matched_qty) + buy_comm_share
                    proceeds = (sell_price * matched_qty) - sell_comm_share
                    pnl = proceeds - cost
                    pnl_pct = (pnl / cost) * 100 if cost > 0 else 0
                    
                    round_trips.append({
                        'entry_date': buy_order['date'],
                        'exit_date': t['date'],
                        'qty': matched_qty,
                        'entry_price': buy_order['price'],
                        'exit_price': sell_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct
                    })
                    
                    # Update queues
                    sell_qty -= matched_qty
                    buy_order['qty'] -= matched_qty
                    buy_order['commission'] -= buy_comm_share
                    
                    if buy_order['qty'] <= 0:
                        buy_queue.pop(0)
                        
        # Calculate Stats
        if not round_trips:
            return {}
            
        wins = [t for t in round_trips if t['pnl'] > 0]
        losses = [t for t in round_trips if t['pnl'] <= 0]
        
        win_rate = (len(wins) / len(round_trips)) * 100
        
        gross_profit = sum(t['pnl'] for t in wins)
        gross_loss = abs(sum(t['pnl'] for t in losses))
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        avg_win = (gross_profit / len(wins)) if wins else 0
        avg_loss = (gross_loss / len(losses)) if losses else 0
        
        return {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'round_trips': round_trips
        }

    def _process_trades(self):
        """处理撮合引擎产生的新成交"""
        for trade in self.matching_engine.trades:
            if trade.trade_id in self.processed_trades:
                continue
            
            order = self.matching_engine.orders.get(trade.order_id)
            if not order:
                continue
                
            # 应用滑点 (Slippage)
            executed_price = trade.price
            if order.side == "BUY":
                executed_price = executed_price * (1 + self.slippage_rate)
            elif order.side == "SELL":
                executed_price = executed_price * (1 - self.slippage_rate)
            
            # 更新资金和持仓
            amount = executed_price * trade.quantity
            commission = amount * self.commission_rate
            if commission < self.min_commission: commission = self.min_commission
            
            if order.side == "BUY":
                self.cash -= (amount + commission)
                self.positions[trade.symbol] = self.positions.get(trade.symbol, 0) + trade.quantity
            elif order.side == "SELL":
                self.cash += (amount - commission)
                self.positions[trade.symbol] = self.positions.get(trade.symbol, 0) - trade.quantity
                
            self.processed_trades.add(trade.trade_id)
            self.trade_history.append({
                "trade_id": trade.trade_id,
                "date": trade.timestamp,
                "symbol": trade.symbol,
                "side": order.side,
                "price": round(executed_price, 2),
                "quantity": trade.quantity,
                "commission": round(commission, 2),
                "cost": round(amount + commission if order.side == "BUY" else amount - commission, 2),
                "cash_balance": self.cash
            })
            
    def _record_daily_value(self, date, current_price):
        position_value = 0
        for sym, qty in self.positions.items():
            # 简化：假设单标的回测，直接用 current_price
            # 如果是多标的，需要获取每个标的当日价格
            position_value += qty * current_price
            
        total_value = self.cash + position_value
        self.daily_value.append({
            "date": date,
            "total_value": total_value,
            "cash": self.cash,
            "position_value": position_value
        })

    def _generate_report(self):
        if not self.daily_value:
            logger.warning("没有回测数据")
            return

        initial = self.initial_capital
        final = self.daily_value[-1]["total_value"]
        ret = (final - initial) / initial * 100
        
        print("-" * 50)
        print(f"回测报告: {self.strategy.name if self.strategy else 'Unknown'}")
        print(f"回测区间: {self.start_date} - {self.end_date}")
        print(f"初始资金: {initial:.2f}")
        print(f"最终权益: {final:.2f}")
        print(f"收益率: {ret:.2f}%")
        print(f"交易次数: {len(self.trade_history)}")
        print("-" * 50)

    def log(self, msg: str):
        logger.info(msg)
