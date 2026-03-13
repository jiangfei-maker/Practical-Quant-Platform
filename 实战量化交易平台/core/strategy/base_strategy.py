from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseStrategy(ABC):
    """
    策略基类
    所有的具体策略都应该继承此类并实现 initialize 和 on_bar 方法
    """
    def __init__(self):
        self.engine = None
        self.name = self.__class__.__name__

    def set_engine(self, engine):
        """设置回测/实盘引擎引用"""
        self.engine = engine

    @abstractmethod
    def initialize(self):
        """
        初始化策略
        在这里设置参数、加载历史数据等
        """
        pass

    @abstractmethod
    def on_bar(self, bar: Dict[str, Any]):
        """
        收到新的K线数据
        bar: {
            "symbol": str,
            "date": datetime,
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "volume": int
        }
        """
        pass
    
    def buy(self, symbol: str, price: float, quantity: int, order_type: str = "LIMIT") -> Optional[str]:
        """
        买入下单
        :param symbol: 标的代码
        :param price: 价格 (市价单时传 0)
        :param quantity: 数量
        :param order_type: "LIMIT" or "MARKET"
        :return: order_id
        """
        if self.engine:
            return self.engine.submit_order(symbol, "BUY", price, quantity, order_type)
        return None

    def sell(self, symbol: str, price: float, quantity: int, order_type: str = "LIMIT") -> Optional[str]:
        """
        卖出下单
        :param symbol: 标的代码
        :param price: 价格 (市价单时传 0)
        :param quantity: 数量
        :param order_type: "LIMIT" or "MARKET"
        :return: order_id
        """
        if self.engine:
            return self.engine.submit_order(symbol, "SELL", price, quantity, order_type)
        return None
    
    def get_position(self, symbol: str) -> int:
        """获取当前持仓数量"""
        if self.engine:
            return self.engine.positions.get(symbol, 0)
        return 0

    def log(self, message: str):
        """记录日志"""
        if self.engine:
            self.engine.log(f"[{self.name}] {message}")
        else:
            print(f"[{self.name}] {message}")
