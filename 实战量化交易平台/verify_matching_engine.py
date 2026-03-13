from core.strategy.matching_engine import MatchingEngine, Order
from datetime import datetime
from loguru import logger

def test_matching_engine():
    logger.info(">>> 开始测试: MatchingEngine")
    
    engine = MatchingEngine()
    
    # 1. 提交买单 (限价单)
    # 假设当前价格 100，我们挂单 99 买入
    order1 = Order(
        order_id="ORD_001",
        symbol="600519",
        side="BUY",
        order_type="LIMIT",
        price=99.0,
        quantity=100
    )
    engine.submit_order(order1)
    
    # 2. 模拟 Tick 数据 (未成交)
    tick1 = {
        "current_price": 100.0,
        "high": 101.0,
        "low": 99.5, # 最低价 99.5 > 99.0，未成交
        "volume": 1000,
        "timestamp": datetime.now(),
        "ask1_price": 100.1,
        "bid1_price": 99.9
    }
    matched = engine.match_on_tick("ORD_001", tick1)
    if not matched:
        logger.info("✅ Tick 1: 价格未触及，未成交 (预期符合)")
    else:
        logger.error("❌ Tick 1: 意外成交")
        
    # 3. 模拟 Tick 数据 (成交)
    tick2 = {
        "current_price": 98.0,
        "high": 100.0,
        "low": 98.0, # 最低价 98.0 <= 99.0，应成交
        "volume": 2000,
        "timestamp": datetime.now(),
        "ask1_price": 98.1,
        "bid1_price": 97.9
    }
    matched = engine.match_on_tick("ORD_001", tick2)
    if matched:
        logger.success("✅ Tick 2: 价格触及，订单成交")
        logger.info(f"成交记录:\n{engine.get_trades_df()}")
    else:
        logger.error("❌ Tick 2: 未成交")

if __name__ == "__main__":
    test_matching_engine()
