from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime
import pandas as pd
from loguru import logger

@dataclass
class Order:
    order_id: str
    symbol: str
    side: str  # "BUY" or "SELL"
    order_type: str  # "LIMIT" or "MARKET"
    price: float  # Limit price (0 for MARKET)
    quantity: int
    status: str = "PENDING"  # PENDING, FILLED, CANCELLED, REJECTED
    filled_qty: int = 0
    avg_price: float = 0.0
    created_at: datetime = datetime.now()

@dataclass
class Trade:
    trade_id: str
    order_id: str
    symbol: str
    price: float
    quantity: int
    timestamp: datetime

class MatchingEngine:
    """
    撮合引擎
    模拟交易所的撮合逻辑
    """
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.trades: List[Trade] = []
        self.market_prices: Dict[str, float] = {} # 缓存最新价格
        
    def submit_order(self, order: Order):
        self.orders[order.order_id] = order
        
    def update_market_price(self, symbol: str, price: float):
        self.market_prices[symbol] = price
        
    def match(self, bar: Dict[str, Any]):
        """
        根据最新的 Bar 数据撮合订单
        简单逻辑：
        - 买单：如果 Limit Price >= Low，成交
        - 卖单：如果 Limit Price <= High，成交
        - 市价单：以 Close (或 Open) 成交
        """
        
    def match_on_tick(self, order_id: str, tick_data: dict) -> bool:
        """
        基于 Tick 数据尝试撮合订单
        tick_data: {
            "current_price": float,
            "high": float, 
            "low": float,
            "volume": int,
            "timestamp": datetime,
            "ask1_price": float,
            "bid1_price": float
        }
        """
        order = self.orders.get(order_id)
        if not order or order.status in ["FILLED", "CANCELLED"]:
            return False
            
        # 简单撮合逻辑
        filled = False
        
        if order.order_type == "MARKET":
            # 市价单：以对手价成交 (简化：Ask1 for Buy, Bid1 for Sell)
            # 考虑冲击成本：这里暂不模拟，直接用 current_price 或 ask1/bid1
            exec_price = tick_data.get("ask1_price") if order.side == "BUY" else tick_data.get("bid1_price")
            if not exec_price:
                 exec_price = tick_data["current_price"]
                 
            self._execute_trade(order, exec_price, order.quantity, tick_data["timestamp"])
            filled = True
            
        elif order.order_type == "LIMIT":
            # 限价单逻辑
            if order.side == "BUY":
                # 买单：如果最低价 <= 限价，则成交
                # 更精细：如果 current_price <= limit_price 或者是 low <= limit_price
                if tick_data["low"] <= order.price:
                    # 假设以限价成交，或者更优价格？
                    # 保守起见，回测通常假设以限价成交 (如果穿过)
                    self._execute_trade(order, order.price, order.quantity, tick_data["timestamp"])
                    filled = True
            elif order.side == "SELL":
                # 卖单：如果最高价 >= 限价
                if tick_data["high"] >= order.price:
                    self._execute_trade(order, order.price, order.quantity, tick_data["timestamp"])
                    filled = True
                    
        return filled

    def match_on_bar(self, order_id: str, bar_data: dict) -> bool:
        """
        基于 K线(Bar) 数据尝试撮合订单
        bar_data: {
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "volume": int,
            "date": datetime
        }
        """
        order = self.orders.get(order_id)
        if not order or order.status in ["FILLED", "CANCELLED"]:
            return False

        filled = False
        timestamp = bar_data["date"]

        if order.order_type == "MARKET":
            # 市价单：通常假设以开盘价成交 (如果订单在Bar开始前提交)
            # 或者以收盘价成交 (如果订单在Bar结束时提交)
            # 这里简化：假设以Open成交 (Next Bar Open)
            exec_price = bar_data["open"]
            self._execute_trade(order, exec_price, order.quantity, timestamp)
            filled = True
            
        elif order.order_type == "LIMIT":
            if order.side == "BUY":
                # 买单：如果 Low <= Limit Price
                if bar_data["low"] <= order.price:
                    # 如果 Open < Limit，可能以 Open 成交 (更优)
                    # 否则以 Limit 成交
                    exec_price = order.price
                    if bar_data["open"] < order.price:
                         exec_price = bar_data["open"] # 获得更优价格
                    
                    self._execute_trade(order, exec_price, order.quantity, timestamp)
                    filled = True
            elif order.side == "SELL":
                # 卖单：如果 High >= Limit Price
                if bar_data["high"] >= order.price:
                    exec_price = order.price
                    if bar_data["open"] > order.price:
                        exec_price = bar_data["open"]
                        
                    self._execute_trade(order, exec_price, order.quantity, timestamp)
                    filled = True
                    
        return filled

    def _execute_trade(self, order: Order, price: float, qty: int, time: datetime):
        order.status = "FILLED"
        order.filled_qty = qty
        order.avg_price = price
        
        trade = Trade(
            trade_id=f"T_{len(self.trades)+1}",
            order_id=order.order_id,
            symbol=order.symbol,
            price=price,
            quantity=qty,
            timestamp=time
        )
        self.trades.append(trade)
        logger.success(f"订单成交: {order.symbol} {order.side} {qty} @ {price}")

    def get_trades_df(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame([vars(t) for t in self.trades])
